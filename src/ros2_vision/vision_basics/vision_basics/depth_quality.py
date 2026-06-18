#!/usr/bin/env python3
"""03-6 深度方案对比: D435 深度质量评估

订阅 D435 深度图 → 计算质量指标:
  - 填充率 (有效像素占比)
  - 深度分布 (min/max/mean/median)
  - 噪声估计 (平坦区域的 std dev)

对着不同材质/光照/距离 → 看到指标变化 → 理解不同深度方案的优劣。
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import numpy as np


class DepthQualityNode(Node):
    def __init__(self):
        super().__init__('depth_quality')
        self.bridge = CvBridge()
        self.frame_count = 0

        self.sub = self.create_subscription(
            Image, '/camera/camera/aligned_depth_to_color/image_raw',
            self.callback, 10)
        self.get_logger().info('深度质量评估 — 对着不同场景观察指标变化')

    def callback(self, msg):
        self.frame_count += 1
        depth = self.bridge.imgmsg_to_cv2(msg, '32FC1')
        h, w = depth.shape

        # --- 1. 填充率 ---
        valid = depth[depth > 0]
        fill_rate = len(valid) / (h * w) * 100

        # --- 2. 深度分布 ---
        if len(valid) == 0:
            self.get_logger().warn(f'[{self.frame_count}] 深度图全空！')
            return

        z_min, z_max = valid.min(), valid.max()
        z_mean, z_median = valid.mean(), np.median(valid)

        # --- 3. 噪声估计 (中心 100×100 平坦区域) ---
        cy, cx = h // 2, w // 2
        patch = depth[cy-50:cy+50, cx-50:cx+50]
        patch_valid = patch[patch > 0]
        noise_std = np.std(patch_valid) if len(patch_valid) > 100 else 0

        # --- 4. 距离分布 ---
        near = np.sum(valid < 1.0) / len(valid) * 100   # <1m
        mid = np.sum((valid >= 1.0) & (valid < 3.0)) / len(valid) * 100
        far = np.sum(valid >= 3.0) / len(valid) * 100

        self.get_logger().info(
            f'[{self.frame_count}] '
            f'填充率={fill_rate:.0f}% | '
            f'z∈[{z_min:.2f},{z_max:.2f}]m '
            f'mean={z_mean:.2f} median={z_median:.2f} | '
            f'噪声σ={noise_std:.3f}m | '
            f'<1m:{near:.0f}% 1-3m:{mid:.0f}% >3m:{far:.0f}%')


def main():
    rclpy.init()
    node = DepthQualityNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
