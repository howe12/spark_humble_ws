#!/usr/bin/env python3
"""03-5 多相机融合: ROS2 立体匹配 vs D435 深度对比

订阅 D435 RGB + 对齐深度图 → 合成立体对(水平偏移) → SGBM 视差
→ 视差转深度 → 对比 D435 深度（当作真值）→ 并排显示差异

目的: 让学生直观看到立体匹配的效果和局限，
理解为什么 D435 内部用硬件做立体匹配。
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge
import cv2
import numpy as np


class StereoCompareNode(Node):
    def __init__(self):
        super().__init__('stereo_compare_node')
        self.bridge = CvBridge()
        self.rgb = None
        self.depth_gt = None

        self.fx, self.fy = 613.4, 612.2
        self.cx, self.cy = 330.2, 240.6

        # 合成立体参数
        self.shift = 12          # 水平偏移 (模拟基线)
        self.baseline = 0.05     # 合成基线 (m)

        # SGBM
        self.stereo = cv2.StereoSGBM_create(
            minDisparity=0, numDisparities=64, blockSize=5,
            P1=8*3*5**2, P2=32*3*5**2, disp12MaxDiff=1,
            uniquenessRatio=10, speckleWindowSize=100, speckleRange=32)

        self.rgb_sub = self.create_subscription(
            Image, '/camera/camera/color/image_raw', self.rgb_cb, 10)
        self.depth_sub = self.create_subscription(
            Image, '/camera/camera/aligned_depth_to_color/image_raw',
            self.depth_cb, 10)
        self.ci_sub = self.create_subscription(
            CameraInfo, '/camera/camera/color/camera_info',
            self.camera_info_cb, 10)
        self.get_logger().info('立体对比节点启动 — 等待 RGB + Depth')

    def camera_info_cb(self, msg):
        self.fx = msg.k[0]; self.fy = msg.k[4]
        self.cx = msg.k[2]; self.cy = msg.k[5]
        self.destroy_subscription(self.ci_sub)

    def rgb_cb(self, msg):
        self.rgb = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

    def depth_cb(self, msg):
        self.depth_gt = self.bridge.imgmsg_to_cv2(msg, '32FC1')

    def spin_once(self):
        rclpy.spin_once(self, timeout_sec=0.05)
        if self.rgb is None or self.depth_gt is None:
            return

        gray = cv2.cvtColor(self.rgb, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        # --- 1. 合成右视图 ---
        right = np.zeros_like(gray)
        right[:, self.shift:] = gray[:, :w-self.shift]

        # --- 2. SGBM 匹配 → 视差 ---
        disp = self.stereo.compute(gray, right).astype(np.float32) / 16.0
        disp[disp < 0] = 0

        # --- 3. 视差 → 深度 (SGBM 估计) ---
        depth_sgbm = np.zeros_like(disp)
        valid = disp > 0
        depth_sgbm[valid] = self.fx * self.baseline / disp[valid]

        # --- 4. D435 深度 (真值) ---
        depth_gt_valid = self.depth_gt.copy()
        depth_gt_valid[depth_gt_valid > 8] = 0

        # --- 5. 可视化: 3 列并排 ---
        # 列1: RGB原图
        col1 = cv2.resize(self.rgb, (w//3, h//2))

        # 列2: SGBM 视差伪彩色
        disp_viz = cv2.applyColorMap(
            cv2.normalize(disp, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U),
            cv2.COLORMAP_JET)
        col2 = cv2.resize(disp_viz, (w//3, h//2))
        cv2.putText(col2, 'SGBM Disparity', (5, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # 列3: D435 深度伪彩色
        depth_viz = cv2.applyColorMap(
            cv2.normalize(depth_gt_valid, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U),
            cv2.COLORMAP_JET)
        col3 = cv2.resize(depth_viz, (w//3, h//2))
        cv2.putText(col3, 'D435 Depth (GT)', (5, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # 第二行: SGBM深度 vs D435深度对比
        sgbm_viz = cv2.applyColorMap(
            cv2.normalize(depth_sgbm, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U),
            cv2.COLORMAP_JET)
        col4 = cv2.resize(sgbm_viz, (w//3, h//2))
        cv2.putText(col4, 'SGBM Depth', (5, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # 深度差热力图
        diff = np.abs(depth_sgbm - depth_gt_valid)
        diff[diff > 2] = 2  # 截断
        diff_viz = cv2.applyColorMap(
            (diff / 2 * 255).astype(np.uint8), cv2.COLORMAP_HOT)
        col5 = cv2.resize(diff_viz, (w//3, h//2))
        cv2.putText(col5, '|SGBM - D435| diff', (5, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # 统计
        depth_diff = np.abs(depth_sgbm[valid & (depth_gt_valid > 0)] -
                            depth_gt_valid[valid & (depth_gt_valid > 0)])
        if len(depth_diff) > 0:
            cv2.putText(col4, f'MAE: {depth_diff.mean():.3f}m', (5, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        # 合并
        row1 = np.hstack([col1, col2, col3])
        row2 = np.hstack([col4, col5,
                          np.zeros((h//2, w//3, 3), dtype=np.uint8)])
        display = np.vstack([row1, row2])

        cv2.imshow('Stereo SGBM vs D435 Depth', display)
        if cv2.waitKey(1) & 0xFF == 27:
            raise KeyboardInterrupt


def main():
    rclpy.init()
    node = StereoCompareNode()
    try:
        while rclpy.ok():
            node.spin_once()
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
