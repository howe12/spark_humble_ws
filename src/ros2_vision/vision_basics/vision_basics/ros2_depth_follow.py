#!/usr/bin/env python3
"""03-2 深度跟随: ROS2 点云质心跟踪 + cmd_vel 控制

订阅 D435 点云 → 3D ROI 质心计算 → cmd_vel 发布

Python 翻译自 spark_follower.cpp 的核心算法:
  1. 点云中划定 3D ROI
  2. 计算质心 → 控制律: linear = (cz - goal) × Kp, angular = asin(cx/d) × Kp
  3. 补充死区 + 激光雷达避障 (可选)

运行:
  ros2 launch realsense2_camera rs_launch.py pointcloud.enable:=true
  ros2 run vision_basics ros2_depth_follow
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from geometry_msgs.msg import Twist
import sensor_msgs_py.point_cloud2 as pc2
import numpy as np
import math


class DepthFollowNode(Node):
    def __init__(self):
        super().__init__('depth_follow_node')

        # ====== 参数声明 ======
        self.declare_parameter('goal_depth', 0.7)
        self.declare_parameter('z_scale', 1.2)
        self.declare_parameter('x_scale', 5.0)
        self.declare_parameter('min_points', 2000)
        self.declare_parameter('roi_x_min', -0.2)
        self.declare_parameter('roi_x_max', 0.2)
        self.declare_parameter('roi_y_min', 0.1)
        self.declare_parameter('roi_y_max', 0.5)
        self.declare_parameter('roi_z_max', 1.5)

        # ====== 读取参数 ======
        self.goal_depth = self.get_parameter('goal_depth').value
        self.z_scale = self.get_parameter('z_scale').value
        self.x_scale = self.get_parameter('x_scale').value
        self.min_points = self.get_parameter('min_points').value
        self.roi_x = (self.get_parameter('roi_x_min').value,
                      self.get_parameter('roi_x_max').value)
        self.roi_y = (self.get_parameter('roi_y_min').value,
                      self.get_parameter('roi_y_max').value)
        self.roi_z_max = self.get_parameter('roi_z_max').value

        # ====== 发布者 + 订阅者 ======
        self.cmd_pub = self.create_publisher(Twist, 'cmd_vel', 10)
        self.cloud_sub = self.create_subscription(
            PointCloud2, 'camera/camera/depth/color/points',
            self.cloud_cb, 10)

        self.get_logger().info(
            f'深度跟随启动: goal={self.goal_depth}m, '
            f'ROI X={self.roi_x} Y={self.roi_y} Z<{self.roi_z_max}')

    def cloud_cb(self, msg):
        """点云回调：提取 ROI 内点 → 质心 → cmd_vel"""
        # 解析点云 (x, y, z)
        points = []
        for pt in pc2.read_points(msg, field_names=('x', 'y', 'z'),
                                  skip_nans=True):
            points.append((pt[0], pt[1], pt[2]))

        if len(points) < self.min_points:
            self.publish_stop()
            return

        # 3D ROI 过滤 + 质心累加
        x_sum, z_sum, n = 0.0, 0.0, 0
        for px, py, pz in points:
            forward = -py  # 相机 Y↓ → 机器人前方
            if (self.roi_x[0] < px < self.roi_x[1] and
                self.roi_y[0] < forward < self.roi_y[1] and
                pz < self.roi_z_max):
                x_sum += px
                z_sum += pz
                n += 1

        if n < self.min_points:
            self.publish_stop()
            return

        # 质心
        cx = x_sum / n
        cz = z_sum / n

        # 控制律
        linear_x = (cz - self.goal_depth) * self.z_scale
        dist = math.sqrt(cx * cx + cz * cz)
        angular_z = (math.asin(cx / dist) * self.x_scale
                     if dist > 0 else 0.0)

        # 死区
        if abs(cz - self.goal_depth) < 0.05:
            linear_x = 0.0
        if abs(cx) < 0.087:
            angular_z = 0.0

        self.publish_cmd(linear_x, angular_z)
        self.get_logger().info(
            f'质心=({cx:.2f},{cz:.2f})m n={n} '
            f'cmd=(lx={linear_x:.2f}, az={angular_z:.2f})',
            throttle_duration_sec=1.0)

    def publish_cmd(self, lx, az):
        cmd = Twist()
        cmd.linear.x = float(lx)
        cmd.angular.z = float(az)
        self.cmd_pub.publish(cmd)

    def publish_stop(self):
        self.publish_cmd(0.0, 0.0)
        self.get_logger().info('停止 — 目标丢失或点数不足',
                               throttle_duration_sec=2.0)


def main():
    rclpy.init()
    node = DepthFollowNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
