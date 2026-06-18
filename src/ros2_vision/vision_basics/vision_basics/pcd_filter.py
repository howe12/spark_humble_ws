#!/usr/bin/env python3
"""03-1 点云与深度相机: 直通滤波 — z 轴范围过滤

订阅点云 → 保留 z ∈ [z_min, z_max] 的点 → 打印过滤前后统计。
不发布新点云，仅做统计输出，让学生理解"直通滤波"的效果。
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
import numpy as np


class PCDFilter(Node):
    def __init__(self):
        super().__init__('pcd_filter')
        self.z_min = 0.3   # 最近距离 (米)
        self.z_max = 3.0   # 最远距离 (米)

        self.sub = self.create_subscription(
            PointCloud2, '/camera/camera/depth/color/points',
            self.callback, 10)
        self.get_logger().info(
            f'直通滤波: z ∈ [{self.z_min}, {self.z_max}]m')

    def callback(self, msg):
        # 1. 解析全部点
        all_pts = np.array(list(point_cloud2.read_points(
            msg, field_names=('x', 'y', 'z'), skip_nans=True)))

        if len(all_pts) == 0:
            return

        # 2. z 轴直通滤波
        z = all_pts[:, 2]
        mask = (z >= self.z_min) & (z <= self.z_max)
        filtered = all_pts[mask]

        # 3. 统计
        self.get_logger().info(
            f'过滤前: {len(all_pts):>6} 点 | '
            f'z∈[{z.min():.2f}, {z.max():.2f}]m')
        self.get_logger().info(
            f'过滤后: {len(filtered):>6} 点 | '
            f'保留率: {len(filtered)/len(all_pts)*100:.1f}% | '
            f'z∈[{filtered[:,2].min():.2f}, {filtered[:,2].max():.2f}]m')


def main():
    rclpy.init()
    node = PCDFilter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
