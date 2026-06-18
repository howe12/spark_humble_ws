#!/usr/bin/env python3
"""03-1 点云与深度相机: 深度统计 — min/max/mean/median + 最近物体

解析点云 → 计算 z 轴深度统计 → 找最近物体中心位置。
帮助学生理解"从点云里提取有用信息"。
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
import numpy as np


class PCDStats(Node):
    def __init__(self):
        super().__init__('pcd_stats')
        self.sub = self.create_subscription(
            PointCloud2, '/camera/camera/depth/color/points',
            self.callback, 10)

    def callback(self, msg):
        all_pts = np.array(list(point_cloud2.read_points(
            msg, field_names=('x', 'y', 'z'), skip_nans=True)))

        if len(all_pts) == 0:
            return

        z = all_pts[:, 2]

        # --- 基本统计 ---
        stats_msg = (
            f'点数: {len(all_pts)} | '
            f'z: min={z.min():.3f} max={z.max():.3f} '
            f'mean={z.mean():.3f} median={np.median(z):.3f}m')
        self.get_logger().info(stats_msg)

        # --- 深度分布直方图（文本） ---
        bins = [0.3, 0.5, 0.8, 1.2, 2.0, 3.0, 5.0]
        hist, _ = np.histogram(z, bins=bins)
        total = len(all_pts)
        hist_str = ' | '.join(
            f'{bins[i]:.1f}-{bins[i+1]:.1f}m: {hist[i]:>4} ({hist[i]/total*100:5.1f}%)'
            for i in range(len(hist)))
        self.get_logger().info(f'深度分布: {hist_str}')

        # --- 最近物体 ---
        close_mask = z < 1.0
        if np.any(close_mask):
            close_pts = all_pts[close_mask]
            center = close_pts.mean(axis=0)
            self.get_logger().info(
                f'最近物体 (< 1m): {len(close_pts)} 点 | '
                f'中心: ({center[0]:.3f}, {center[1]:.3f}, {center[2]:.3f})')


def main():
    rclpy.init()
    node = PCDStats()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
