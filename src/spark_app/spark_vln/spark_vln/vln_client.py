#!/usr/bin/env python3
"""
VLN Client Node for Spark-I Robot
Subscribes to camera, queries L40 cloud inference via SSH tunnel, publishes cmd_vel.
"""
import base64
import io
import os
import threading
import time
import traceback
import atexit

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rcl_interfaces.msg import SetParametersResult
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
from std_msgs.msg import String
from std_srvs.srv import Trigger

import cv2
import numpy as np
import requests
from cv_bridge import CvBridge

# ── Custom service type (inline to avoid extra package) ──
# Instruction passed via ROS2 param: ros2 param set /vln_client instruction '...' 

# ── SSH tunnel ──
import paramiko
from paramiko import SSHClient, AutoAddPolicy


# ── Global tunnel reference for cleanup ──
_tunnel_process = None


def _cleanup_tunnel():
    global _tunnel_process
    if _tunnel_process:
        _tunnel_process.terminate()
        _tunnel_process = None


atexit.register(_cleanup_tunnel)


class VLNClient(Node):
    def __init__(self):
        super().__init__('vln_client')

        # ── Parameters ──
        self.declare_parameter('l40_url', 'http://localhost:18001')
        self.declare_parameter('linear_speed', 0.2)
        self.declare_parameter('angular_speed', 0.5)
        self.declare_parameter('step_interval', 1.5)
        self.declare_parameter('image_quality', 85)
        self.declare_parameter('http_timeout', 15.0)
        # Tunnel params
        self.declare_parameter('l40_host', '120.209.70.195')
        self.declare_parameter('l40_ssh_port', 30456)
        self.declare_parameter('l40_remote_port', 8443)
        self.declare_parameter('l40_local_port', 18001)
        self.declare_parameter('l40_ssh_key', os.path.expanduser('~/.ssh/l40_key'))

        self.l40_host = self.get_parameter('l40_host').value
        self.l40_ssh_port = self.get_parameter('l40_ssh_port').value
        self.l40_remote_port = self.get_parameter('l40_remote_port').value
        self.l40_local_port = self.get_parameter('l40_local_port').value
        self.l40_ssh_key = self.get_parameter('l40_ssh_key').value

        l40_url = self.get_parameter('l40_url').value.rstrip('/')
        self.reset_url = f'{l40_url}/reset'
        self.step_url = f'{l40_url}/step'
        self.health_url = f'{l40_url}/health'
        self.linear_speed = self.get_parameter('linear_speed').value
        self.angular_speed = self.get_parameter('angular_speed').value
        self.step_interval = self.get_parameter('step_interval').value
        self.step_interval_step = 0.05
        self.image_quality = self.get_parameter('image_quality').value
        self.http_timeout = self.get_parameter('http_timeout').value

        self.cv_bridge = CvBridge()

        # ── Display state ──
        self.declare_parameter('display_enabled', True)
        self.display_enabled = self.get_parameter('display_enabled').value


        # ── State ──
        self.state = 'IDLE'
        self.instruction = ''
        self.latest_image = None
        self.step_id = 0
        self.session_id = f'spark_{int(time.time())}'

        # ── Anti-spin: track consecutive turns ──
        self._turn_count = 0
        self._last_turn_dir = None

        # ── Lock ──
        self._lock = threading.Lock()

        # ── Start SSH tunnel ──
        self._start_tunnel()

        # ── Publishers ──
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.status_pub = self.create_publisher(String, '/vln/status', 10)

        # ── Subscribers ──
        self.cam_sub = self.create_subscription(
            Image, '/camera/color/image_raw', self._on_image, 10)

        # ── Services ──
        self.start_srv = self.create_service(
            Trigger, '/vln/start', self._on_start)
        self.stop_srv = self.create_service(
            Trigger, '/vln/stop', self._on_stop)
        self.declare_parameter('instruction', '')
        self.instruction = self.get_parameter('instruction').value

        # ── Parameter callback for instruction ──
        self.add_on_set_parameters_callback(self._on_param_update)

        # ── Timer ──
        self.loop_timer = None
        self.idle_timer = self.create_timer(0.5, self._idle_tick)

        # ── Display window init ──
        if self.display_enabled:
            os.environ.setdefault('DISPLAY', ':0')
            try:
                cv2.namedWindow('Spark VLN', cv2.WINDOW_NORMAL)
                cv2.resizeWindow('Spark VLN', 640, 560)
            except Exception as e:
                self.get_logger().warn(f'Display init failed: {e}')
                self.display_enabled = False

        self._stop_cmd_vel()
        self._publish_status('IDLE')
        self.get_logger().info(f'VLN Client ready. Tunnel: localhost:{self.l40_local_port} → {self.l40_host}:{self.l40_remote_port}')

    # ── SSH Tunnel ──
    def _start_tunnel(self):
        global _tunnel_process

        if not os.path.exists(self.l40_ssh_key):
            self.get_logger().error(f'SSH key not found: {self.l40_ssh_key}')
            return False

        try:
            import subprocess
            cmd = [
                'ssh',
                '-o', 'StrictHostKeyChecking=no',
                '-i', self.l40_ssh_key,
                '-f', '-N',
                '-L', f'{self.l40_local_port}:localhost:{self.l40_remote_port}',
                f'root@{self.l40_host}',
                '-p', str(self.l40_ssh_port),
            ]
            _tunnel_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1)

            # Verify tunnel
            r = requests.get(self.health_url, timeout=5)
            if r.status_code == 200:
                self.get_logger().info('SSH tunnel established successfully')
                return True
            else:
                self.get_logger().warn(f'Tunnel up but L40 returned {r.status_code}')
                return False
        except Exception as e:
            self.get_logger().error(f'SSH tunnel failed: {e}')
            return False



    # ── Display ──
    def _update_display(self, img, action, step_id, instruction):
        """Build display frame + show immediately."""
        if not self.display_enabled or img is None:
            return
        h, w = img.shape[:2]
        canvas_h = h + 80
        canvas = np.zeros((canvas_h, w, 3), dtype=np.uint8)
        canvas[:h, :w] = img

        colors = {'MOVE_FORWARD': (0, 255, 0), 'TURN_LEFT': (0, 255, 255),
                  'TURN_RIGHT': (0, 255, 255), 'STOP': (0, 0, 255)}
        color = colors.get(action, (255, 255, 255))

        cv2.rectangle(canvas, (0, h), (w, canvas_h), (30, 30, 30), -1)
        instr_short = instruction[:30] + ('...' if len(instruction) > 30 else '')
        cv2.putText(canvas, f"🎯 {instr_short}", (10, h + 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
        cv2.putText(canvas, f"Step {step_id}  |  {action}", (10, h + 58),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        cv2.imshow('Spark VLN', canvas)
        cv2.waitKey(1)

    # ── Image callback ──
    def _on_image(self, msg: Image):
        try:
            self.latest_image = self.cv_bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            if self.display_enabled and self.state == 'IDLE' and self.latest_image is not None:
                self._update_display(self.latest_image, 'WAITING', 0, self.instruction or '等待指令...')
        except Exception:
            pass

    # ── Parameter update callback ──
    def _on_param_update(self, params):
        for p in params:
            if p.name == 'instruction':
                self.instruction = p.value.strip()
                self.get_logger().info(f'Instruction updated: {self.instruction}')
        return SetParametersResult(successful=True)

    # ── Idle keepalive ──
    def _idle_tick(self):
        if self.state in ('IDLE', 'STOPPED'):
            self._stop_cmd_vel()

    # ── Services ──
    def _on_set_instruction_legacy(self):
        import warnings
        warnings.warn('Use ros2 param set /vln_client instruction instead', DeprecationWarning)


    def _on_start(self, req, resp):
        if not self.instruction:
            resp.success = False
            resp.message = 'No instruction set. Call /vln/set_instruction first.'
            return resp

        try:
            r = requests.get(self.health_url, timeout=5)
            if r.status_code != 200 or not r.json().get('model_loaded'):
                resp.success = False
                resp.message = f'L40 not ready: {r.text}'
                return resp
        except Exception as e:
            resp.success = False
            resp.message = f'Cannot reach L40: {e}'
            return resp

        try:
            r = requests.post(self.reset_url, json={
                'session_id': self.session_id,
                'instruction': self.instruction,
            }, timeout=self.http_timeout)
            if r.status_code != 200:
                resp.success = False
                resp.message = f'L40 reset failed: {r.status_code}'
                return resp
        except Exception as e:
            resp.success = False
            resp.message = f'L40 reset error: {e}'
            return resp

        self.state = 'RUNNING'
        self.step_id = 0
        with self._lock:
            self.latest_image = None

        self.loop_timer = self.create_timer(self.step_interval, self._control_tick)
        self._publish_status('RUNNING')
        resp.success = True
        resp.message = f'Navigation started. Instruction: {self.instruction}'
        self.get_logger().info(resp.message)
        return resp

    def _on_stop(self, req, resp):
        self._shutdown_loop()
        self.state = 'STOPPED'
        self._publish_status('STOPPED')
        resp.success = True
        resp.message = 'Navigation stopped'
        return resp

    def _shutdown_loop(self):
        if self.loop_timer:
            self.destroy_timer(self.loop_timer)
            self.loop_timer = None
        if self.display_enabled:
            cv2.destroyWindow('Spark VLN')
        self._stop_cmd_vel()

    # ── Control tick ──
    def _control_tick(self):
        if self.state != 'RUNNING':
            return

        with self._lock:
            img = self.latest_image
        if img is None:
            self.get_logger().warn('No image received yet, waiting...', throttle_duration_sec=3)
            return

        try:
            # Resize to reduce L40 memory pressure (模型43GB, 只剩1GB做推理)
            h, w = img.shape[:2]
            max_size = 384
            if max(h, w) > max_size:
                scale = max_size / max(h, w)
                new_w, new_h = int(w * scale), int(h * scale)
                img = cv2.resize(img, (new_w, new_h))
            ok, jpg = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, self.image_quality])
            if not ok:
                self.get_logger().error('JPEG encode failed')
                return
            b64 = base64.b64encode(jpg.tobytes()).decode()

            r = requests.post(self.step_url, json={
                'session_id': self.session_id,
                'image_base64': b64,
                'step_id': self.step_id,
            }, timeout=self.http_timeout)

            if r.status_code != 200:
                self._on_error(f'L40 returned {r.status_code}')
                return

            data = r.json()
            action = data.get('action', 'STOP')
            raw = data.get('raw_output', '?')
            self.get_logger().info(f'Step {self.step_id}: {action} ({raw})', throttle_duration_sec=1)

        except requests.exceptions.Timeout:
            self._on_error('L40 timeout')
            return
        except Exception as e:
            self._on_error(f'HTTP error: {e}')
            return

        # Anti-spin: if 3+ same turns, force MOVE_FORWARD
        if action in ("TURN_LEFT", "TURN_RIGHT"):
            if action == self._last_turn_dir:
                self._turn_count += 1
            else:
                self._turn_count = 1
            self._last_turn_dir = action
            if self._turn_count >= 3:
                self.get_logger().warn(f"Anti-spin: {self._turn_count} consecutive {action}, forcing MOVE_FORWARD")
                action = "MOVE_FORWARD"
                self._turn_count = 0
                self._last_turn_dir = None
        elif action == "MOVE_FORWARD":
            self._turn_count = 0
            self._last_turn_dir = None

        self._execute_action(action)


        self.step_id += 1

        if action == 'STOP':
            self._shutdown_loop()
            self.state = 'STOPPED'
            self._publish_status('STOPPED')
            self.get_logger().info('Goal reached (STOP)')

    def _execute_action(self, action: str):
        twist = Twist()
        if action == 'MOVE_FORWARD':
            twist.linear.x = self.linear_speed
        elif action == 'TURN_LEFT':
            twist.angular.z = self.angular_speed
        elif action == 'TURN_RIGHT':
            twist.angular.z = -self.angular_speed
        self.cmd_pub.publish(twist)
        # Keep moving until next action — don't stop between steps

    def _stop_cmd_vel(self):
        self.cmd_pub.publish(Twist())

    def _on_error(self, msg: str):
        self._shutdown_loop()
        self.state = 'ERROR'
        self._publish_status('ERROR')
        self.get_logger().error(msg)

    def _publish_status(self, status: str):
        s = String()
        s.data = status
        self.status_pub.publish(s)


def main(args=None):
    rclpy.init(args=args)
    node = VLNClient()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node._shutdown_loop()
    finally:
        _cleanup_tunnel()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
