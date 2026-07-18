#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
指令控制节点 - ROS2 移植版
功能：将解析后的命令参数映射为 /cmd_vel (Twist) 并发布
订阅 /cmd_params，发布 /cmd_vel + /robot_status
特性：持续发布定时器 + 自动停止定时器
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist


class CmdControlNode(Node):
    """指令控制器（ROS2）"""

    def __init__(self):
        super().__init__('cmd_control_node')

        # ROS2 params
        self.declare_parameter('linear_speed', 0.2)
        self.declare_parameter('min_turn_speed', 0.25)
        self.declare_parameter('angular_speed', 0.35)
        self.declare_parameter('publish_rate', 20)

        self.linear_speed = self.get_parameter('linear_speed').value
        self.min_turn_speed = self.get_parameter('min_turn_speed').value
        self.angular_speed = self.get_parameter('angular_speed').value
        self.publish_rate = self.get_parameter('publish_rate').value

        # 意图到速度的映射表
        self.intent_velocity_map = {
            'forward':     (self.linear_speed, 0.0),
            'backward':    (-self.linear_speed, 0.0),
            'left':        (0.0, self.angular_speed),
            'right':       (0.0, -self.angular_speed),
            'stop':        (0.0, 0.0),
            'speed_up':    (self.linear_speed * 1.5, 0.0),
            'slow_down':   (self.linear_speed * 0.5, 0.0),
            'turn_around': (self.linear_speed * 0.5, self.angular_speed * 2)
        }

        # 当前状态
        self.current_twist = Twist()
        self.publish_timer = None
        self.stop_timer = None

        # 创建订阅者和发布者
        self.subscription = self.create_subscription(
            String, '/cmd_params', self.cmd_callback, 10)
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.status_pub = self.create_publisher(String, '/robot_status', 10)

        self.get_logger().info(
            f"指令控制器已启动 (linear={self.linear_speed}, angular={self.angular_speed})")

    def cmd_callback(self, msg):
        """接收指令回调"""
        cmd_str = str(msg.data)
        self.get_logger().info(f"接收到指令: {cmd_str}")

        intent, params = self._parse_command(cmd_str)
        linear, angular = self._calculate_twist(intent, params)

        twist = Twist()
        twist.linear.x = linear
        twist.angular.z = angular
        self.current_twist = twist

        # 关闭旧定时器
        self._cancel_timers()

        # 立即发布一次
        self.cmd_vel_pub.publish(twist)
        status_msg = String()
        status_msg.data = f"Executing: {intent}"
        self.status_pub.publish(status_msg)

        # 启动持续发布定时器
        period = 1.0 / self.publish_rate
        self.publish_timer = self.create_timer(period, self._publish_callback)

        # 如果有持续时间，启动自动停止定时器
        duration = self._calculate_duration(intent, params)
        if duration > 0:
            self.stop_timer = self.create_timer(duration, self._stop_callback, oneshot=True)
            self.get_logger().info(f"将在 {duration:.1f} 秒后自动停止")

    def _cancel_timers(self):
        """取消所有定时器"""
        if self.publish_timer is not None:
            self.destroy_timer(self.publish_timer)
            self.publish_timer = None
        if self.stop_timer is not None:
            self.destroy_timer(self.stop_timer)
            self.stop_timer = None

    def _publish_callback(self):
        """持续发布回调"""
        self.cmd_vel_pub.publish(self.current_twist)

    def _stop_callback(self):
        """自动停止回调"""
        # 取消持续发布
        if self.publish_timer is not None:
            self.destroy_timer(self.publish_timer)
            self.publish_timer = None

        # 发布停止指令
        stop_twist = Twist()
        self.cmd_vel_pub.publish(stop_twist)
        self.current_twist = stop_twist

        status_msg = String()
        status_msg.data = "Stopped: timer triggered"
        self.status_pub.publish(status_msg)

        self.get_logger().info("自动停止定时器触发，机器人已停止")

    def _calculate_twist(self, intent, params):
        """根据意图和参数计算 Twist"""
        if intent in self.intent_velocity_map:
            linear, angular = self.intent_velocity_map[intent]
        else:
            linear, angular = 0.0, 0.0

        # 转向时保持最低线速度
        if intent in ['left', 'right'] and linear == 0:
            linear = self.min_turn_speed

        # 速度参数缩放
        if 'speed' in params:
            scale = params['speed'] / self.linear_speed
            linear *= scale
            angular *= scale

        return linear, angular

    def _calculate_duration(self, intent, params):
        """根据意图和参数计算持续时间"""
        duration = 0.0

        if 'distance' in params and intent in ['forward', 'backward']:
            duration = abs(params['distance']) / self.linear_speed
        elif 'angle' in params and intent in ['left', 'right', 'turn_around']:
            duration = abs(params['angle']) / self.angular_speed
        elif 'time' in params:
            duration = params['time']

        return duration

    def _parse_command(self, cmd_str):
        """解析命令字符串"""
        parts = cmd_str.split(',')
        intent = parts[0].strip()

        params = {}
        for part in parts[1:]:
            if '=' in part:
                key, value = part.split('=')
                try:
                    params[key.strip()] = float(value.strip())
                except ValueError:
                    pass

        return intent, params


def main(args=None):
    rclpy.init(args=args)
    node = CmdControlNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
