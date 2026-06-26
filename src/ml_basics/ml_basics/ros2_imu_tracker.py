#!/usr/bin/env python3
"""1.2 数据分析 — ROS2 IMU 实时轨迹跟踪

订阅 /imu_data → 欧拉法航迹推算 → 发布轨迹 (Path) + 可视化

ROS1 → ROS2 适配要点:
  - rospy.Subscriber → rclpy Node.create_subscription
  - rospy.Time.now() → node.get_clock().now()
  - nav_msgs/Path 发布实时轨迹
  - 增加轨迹重置服务 (方便多次实验)

用法:
  ros2 run ml_basics ros2_imu_tracker
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped
import numpy as np
import math


class IMUTrackerNode(Node):
    def __init__(self):
        super().__init__('imu_tracker_node')

        # ── IMU 参数 ──
        self.declare_parameter('gyro_bias', [2.424e-5, 2.424e-5, 2.424e-5])
        self.declare_parameter('accel_bias', [9.81e-5, 9.81e-5, 3.4335e-4])

        self.gyro_bias = np.array(
            self.get_parameter('gyro_bias').get_parameter_value().double_array_value)
        self.accel_bias = np.array(
            self.get_parameter('accel_bias').get_parameter_value().double_array_value)
        self.gravity = np.array([0.0, 0.0, -9.81])

        # ── 状态变量 ──
        self.R = np.eye(3)        # 旋转矩阵
        self.v = np.zeros(3)      # 速度 (世界系)
        self.p = np.zeros(3)      # 位置
        self.last_time = None     # 上一帧时间
        self.trajectory = []      # 轨迹记录

        # ── ROS2 话题 ──
        self.imu_sub = self.create_subscription(
            Imu, '/imu_data', self.imu_callback, 10)
        self.path_pub = self.create_publisher(Path, '/imu_trajectory', 10)

        self.get_logger().info('IMU 轨迹跟踪已启动 | 等待 /imu_data ...')

    def skew(self, v):
        return np.array([[0, -v[2], v[1]],
                         [v[2], 0, -v[0]],
                         [-v[1], v[0], 0]])

    def exp_so3(self, omega, dt):
        theta = np.linalg.norm(omega) * dt
        if theta < 1e-10:
            return np.eye(3)
        axis = omega / (np.linalg.norm(omega) + 1e-12)
        K = self.skew(axis)
        return np.eye(3) + math.sin(theta) * K + (1 - math.cos(theta)) * (K @ K)

    def imu_callback(self, msg: Imu):
        now = self.get_clock().now().nanoseconds / 1e9

        if self.last_time is None:
            self.last_time = now
            return

        dt = now - self.last_time
        self.last_time = now

        if dt <= 0 or dt > 0.1:
            return  # 跳过异常 dt

        # 提取角速度 & 加速度 (去偏置)
        omega = np.array([
            msg.angular_velocity.x,
            msg.angular_velocity.y,
            msg.angular_velocity.z,
        ]) - self.gyro_bias

        accel = np.array([
            msg.linear_acceleration.x,
            msg.linear_acceleration.y,
            msg.linear_acceleration.z,
        ]) - self.accel_bias

        # 欧拉积分
        self.R = self.R @ self.exp_so3(omega, dt)
        self.v = self.v + (self.R @ accel + self.gravity) * dt
        self.p = self.p + self.v * dt

        self.trajectory.append(self.p.copy())

        # 发布 Path
        path_msg = Path()
        path_msg.header.stamp = msg.header.stamp
        path_msg.header.frame_id = 'odom'

        for pt in self.trajectory[-100:]:  # 最近 100 个点
            pose = PoseStamped()
            pose.header = path_msg.header
            pose.pose.position.x = float(pt[0])
            pose.pose.position.y = float(pt[1])
            pose.pose.position.z = float(pt[2])
            path_msg.poses.append(pose)

        self.path_pub.publish(path_msg)

        # 每 100 帧打印一次
        if len(self.trajectory) % 100 == 0:
            self.get_logger().info(
                f'位置: ({self.p[0]:.2f}, {self.p[1]:.2f}) | '
                f'轨迹点数: {len(self.trajectory)}')


def main():
    rclpy.init()
    node = IMUTrackerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
