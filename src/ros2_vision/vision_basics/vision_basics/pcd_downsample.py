#!/usr/bin/env python3
"""03-1 点云与深度相机: 体素下采样（纯 numpy）

将 3D 空间划分为 voxel_size × voxel_size × voxel_size 的立方体，
每个体素只保留一个点（质心），从而大幅减少点云密度。
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
import numpy as np


class PCDDownsample(Node):
    def __init__(self):
        super().__init__('pcd_downsample')
        self.voxel_size = 0.05  # 5cm

        self.sub = self.create_subscription(
            PointCloud2, '/camera/camera/depth/color/points',
            self.callback, 10)
        self.get_logger().info(f'体素下采样: voxel={self.voxel_size}m')

    def voxel_downsample(self, points):
        """纯 numpy 体素下采样 — 每个体素只保留一个点"""
        if len(points) == 0:
            return points

        # 1. 计算每个点落在哪个体素（整数索引）
        voxel_indices = np.floor(points[:, :3] / self.voxel_size).astype(np.int32)

        # 2. 按体素索引分组
        _, unique_idx, counts = np.unique(
            voxel_indices, axis=0, return_index=True, return_counts=True)

        # 3. 返回每个体素的第一个点
        return points[unique_idx]

    def callback(self, msg):
        all_pts = np.array(list(point_cloud2.read_points(
            msg, field_names=('x', 'y', 'z'), skip_nans=True)))

        if len(all_pts) == 0:
            return

        downsampled = self.voxel_downsample(all_pts)

        self.get_logger().info(
            f'下采样前: {len(all_pts):>6} 点 | '
            f'下采样后: {len(downsampled):>6} 点 | '
            f'压缩比: {len(all_pts)/max(len(downsampled),1):.1f}x')


def main():
    rclpy.init()
    node = PCDDownsample()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
