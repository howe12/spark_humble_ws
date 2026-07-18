#!/usr/bin/env python3
"""
03-2 参考版核心程序: ROS2 目标跟随控制节点
==========================================
对应参考版 (X3qRdYfoco4XwcxI6Hkc4pXuneb) "following_control_node"

架构 (YOLO检测链路):
  /camera/aligned_depth/image_raw ─┐
  /tracking/detections ────────────┤
                                   ▼
  FollowingControlNode ──→ /cmd_vel (geometry_msgs/Twist)

⚠️ 底盘安全警告
===============
本节点会向 /cmd_vel 发布速度指令控制机器人移动。
运行前必须确保：
  1. 机器人悬空/有人监护
  2. 紧急停止按钮可用
  3. 通过 ros2 param set /following_control_node enable_following false 可禁用

运行:
  ros2 launch realsense2_camera rs_launch.py align_depth.enable:=true
  ros2 run vision_basics following_control_node
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import Twist
from std_msgs.msg import Int32MultiArray
import numpy as np
import math
from cv_bridge import CvBridge

# 使用本地工具模块
from vision_basics.following_utils import DepthObjectDetector, FollowingController


class FollowingControlNode(Node):
    """
    ROS2 目标跟随控制节点

    订阅:
      /camera/aligned_depth/image_raw  — 对齐深度图
      /tracking/detections             — 检测结果 [track_id, x1, y1, x2, y2, class_id]
      /camera/depth/camera_info        — 相机内参

    发布:
      /cmd_vel  — 机器人速度指令
    """

    def __init__(self):
        super().__init__('following_control_node')

        # ===== 参数 =====
        self.declare_parameter('desired_distance', 1.5)
        self.declare_parameter('max_linear_speed', 0.5)
        self.declare_parameter('max_angular_speed', 1.5)
        self.declare_parameter('target_class', 0)        # 0=person (COCO)
        self.declare_parameter('enable_following', False) # ⚠️ 默认关闭！
        self.declare_parameter('depth_filter_alpha', 0.3)

        self.desired_distance = self.get_parameter('desired_distance').value
        self.max_linear_speed = self.get_parameter('max_linear_speed').value
        self.max_angular_speed = self.get_parameter('max_angular_speed').value
        self.target_class = self.get_parameter('target_class').value
        self.depth_filter_alpha = self.get_parameter('depth_filter_alpha').value

        # ===== 相机内参 (默认 D435 720p) =====
        self.camera_intrinsics = {'fx': 639.0, 'fy': 639.0, 'cx': 639.5, 'cy': 359.5}
        self.camera_info_received = False

        # ===== 深度图 =====
        self.latest_depth = None
        self.bridge = CvBridge()

        # ===== 当前跟踪目标 =====
        self.tracked_target = None

        # ===== 深度定位器 + PID控制器 =====
        self.detector = DepthObjectDetector(
            self.camera_intrinsics,
            target_class='person',  # 用 class_name 匹配
            depth_filter_alpha=self.depth_filter_alpha
        )
        self.controller = FollowingController(
            desired_distance=self.desired_distance,
            max_linear_speed=self.max_linear_speed,
            max_angular_speed=self.max_angular_speed
        )

        # ===== 50Hz 控制循环 =====
        self.control_timer = self.create_timer(0.02, self.control_callback)

        # ===== 订阅 =====
        self.depth_sub = self.create_subscription(
            Image, '/camera/aligned_depth_to_color/image_raw',
            self.depth_callback, 10)
        self.info_sub = self.create_subscription(
            CameraInfo, '/camera/color/camera_info',
            self.camera_info_callback, 10)
        self.detection_sub = self.create_subscription(
            Int32MultiArray, '/tracking/detections',
            self.detection_callback, 10)

        # ===== 发布 =====
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        self.get_logger().info('=' * 50)
        self.get_logger().info('目标跟随控制节点已启动')
        self.get_logger().info(f'  期望距离: {self.desired_distance}m')
        self.get_logger().info(f'  最大速度: v={self.max_linear_speed} ω={self.max_angular_speed}')
        self.get_logger().info('  ⚠️ enable_following=False (默认关闭)')
        self.get_logger().info('  启用: ros2 param set /following_control_node enable_following true')
        self.get_logger().info('=' * 50)

    # ---------- 回调 ----------

    def camera_info_callback(self, msg):
        if self.camera_info_received:
            return
        self.camera_intrinsics['fx'] = msg.k[0]
        self.camera_intrinsics['fy'] = msg.k[4]
        self.camera_intrinsics['cx'] = msg.k[2]
        self.camera_intrinsics['cy'] = msg.k[5]
        self.camera_info_received = True
        self.detector.camera_intrinsics = self.camera_intrinsics
        self.get_logger().info(f'相机内参已更新: fx={msg.k[0]:.1f} fy={msg.k[4]:.1f}')

    def depth_callback(self, msg):
        try:
            depth = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
            self.latest_depth = depth.astype(np.float32) / 1000.0  # mm → m
        except Exception as e:
            self.get_logger().error(f'深度图转换失败: {e}')

    def detection_callback(self, msg):
        """接收检测结果: [track_id, x1, y1, x2, y2, class_id]"""
        data = list(msg.data)
        detections = []
        for i in range(0, len(data), 6):
            if i + 5 < len(data):
                track_id, x1, y1, x2, y2, class_id = data[i:i+6]
                detections.append({
                    'track_id': track_id,
                    'bbox': [x1, y1, x2, y2],
                    'class_id': class_id,
                    'class_name': 'person' if class_id == 0 else 'unknown',
                    'confidence': 1.0,
                })

        if detections:
            self.process_detections(detections)

    def process_detections(self, detections):
        """深度融合 + 目标选择"""
        if self.latest_depth is None:
            return

        # 筛选目标类别
        class_dets = [d for d in detections if d['class_id'] == self.target_class]
        if not class_dets:
            self.tracked_target = None
            return

        # 深度融合 → 3D位置
        localized = self.detector.detect_and_localize(
            None, self.latest_depth, class_dets)

        if not localized:
            return

        # 目标选择: 优先保持当前跟踪ID，否则选最近
        if self.tracked_target is not None:
            matched = [d for d in localized
                       if d['track_id'] == self.tracked_target.get('track_id')]
            self.tracked_target = matched[0] if matched else min(localized, key=lambda d: d['distance'])
        else:
            self.tracked_target = min(localized, key=lambda d: d['distance'])

    # ---------- 控制循环 ----------

    def control_callback(self):
        """50Hz: 根据目标位置计算并发布 cmd_vel"""
        enable = self.get_parameter('enable_following').value

        if not enable:
            # 跟随禁用 → 停止
            self.publish_stop()
            return

        if self.tracked_target is None or self.tracked_target.get('position_3d') is None:
            # 无目标 → 逐渐减速
            self.controller.v_filtered *= 0.8
            self.controller.omega_filtered *= 0.8
            self.publish_cmd(self.controller.v_filtered, self.controller.omega_filtered)
            return

        # PID 控制
        pos_3d = self.tracked_target['position_3d']
        v, omega = self.controller.compute(pos_3d, dt=0.02)

        cmd = Twist()
        cmd.linear.x = float(v)
        cmd.angular.z = float(omega)
        self.cmd_vel_pub.publish(cmd)

        self.get_logger().info(
            f'目标: d={self.tracked_target.get("distance", 0):.2f}m '
            f'→ cmd: v={v:+.2f} ω={omega:+.2f}',
            throttle_duration_sec=1.0)

    def publish_cmd(self, linear_x, angular_z):
        cmd = Twist()
        cmd.linear.x = float(linear_x)
        cmd.angular.z = float(angular_z)
        self.cmd_vel_pub.publish(cmd)

    def publish_stop(self):
        self.publish_cmd(0.0, 0.0)
        self.get_logger().info('跟随已停止', throttle_duration_sec=3.0)


def main():
    rclpy.init()
    node = FollowingControlNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.publish_stop()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
