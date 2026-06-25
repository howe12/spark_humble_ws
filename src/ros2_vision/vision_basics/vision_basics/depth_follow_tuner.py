#!/usr/bin/env python3
"""03-2 深度跟随: 3D ROI 参数调参工具（带深度图可视化）

供学生理解 ROI 参数含义:
  - roi_x_min/max: 左右范围（m）
  - roi_y_min/max: 前后范围（-py, 机器人前方）
  - roi_z_max: 高度上限（m）
  - goal_depth: 目标跟随距离（m）

左边=RGB, 右边=深度图+ROI 标注+质心显示

运行:
  ros2 launch realsense2_camera rs_launch.py align_depth.enable:=true
  ros2 run vision_basics depth_follow_tuner
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge
import cv2
import numpy as np
import math


class DepthFollowTuner(Node):
    def __init__(self):
        super().__init__('depth_follow_tuner')
        self.bridge = CvBridge()
        self.rgb_image = None
        self.depth_image = None

        # 相机内参
        self.fx, self.fy = 613.4, 612.2
        self.cx, self.cy = 330.2, 240.6

        # ROI 默认参数
        self.roi_x_min = -20   # ×10 (显示用, 单位 cm)
        self.roi_x_max = 20
        self.roi_y_min = 10
        self.roi_y_max = 50
        self.goal_depth = 70   # ×10
        self.min_points = 20   # ×100

        self.init_window = True

        # 订阅
        self.rgb_sub = self.create_subscription(
            Image, '/camera/camera/color/image_raw', self.rgb_cb, 10)
        self.depth_sub = self.create_subscription(
            Image, '/camera/camera/aligned_depth_to_color/image_raw',
            self.depth_cb, 10)
        self.camera_info_sub = self.create_subscription(
            CameraInfo, '/camera/camera/color/camera_info',
            self.camera_info_cb, 10)

        self.init_gui()
        self.get_logger().info('深度跟随调参工具启动 — 拖动滑块调整 ROI')

    def init_gui(self):
        cv2.namedWindow('Depth Follow Tuner', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Depth Follow Tuner', 1300, 600)
        cv2.createTrackbar('X min (cm)', 'Depth Follow Tuner',
                           -20, 100, self.on_trackbar)
        cv2.createTrackbar('X max (cm)', 'Depth Follow Tuner',
                           20, 100, self.on_trackbar)
        cv2.createTrackbar('Y min (cm)', 'Depth Follow Tuner',
                           10, 100, self.on_trackbar)
        cv2.createTrackbar('Y max (cm)', 'Depth Follow Tuner',
                           50, 200, self.on_trackbar)
        cv2.createTrackbar('Z max (cm)', 'Depth Follow Tuner',
                           150, 300, self.on_trackbar)
        cv2.createTrackbar('Goal (cm)', 'Depth Follow Tuner',
                           70, 200, self.on_trackbar)
        cv2.setMouseCallback('Depth Follow Tuner', self.mouse_cb)
        self.init_window = False

    def on_trackbar(self, val):
        if self.init_window:
            return
        self.roi_x_min = cv2.getTrackbarPos('X min (cm)', 'Depth Follow Tuner')
        self.roi_x_max = cv2.getTrackbarPos('X max (cm)', 'Depth Follow Tuner')
        self.roi_y_min = cv2.getTrackbarPos('Y min (cm)', 'Depth Follow Tuner')
        self.roi_y_max = cv2.getTrackbarPos('Y max (cm)', 'Depth Follow Tuner')
        self.goal_depth = cv2.getTrackbarPos('Goal (cm)', 'Depth Follow Tuner')
        self.roi_z_max = cv2.getTrackbarPos('Z max (cm)', 'Depth Follow Tuner')

    def mouse_cb(self, event, x, y, flags, param):
        """点击深度图某点 → 终端输出该点的 3D 坐标"""
        if event == cv2.EVENT_LBUTTONDOWN and self.depth_image is not None:
            h, w = self.depth_image.shape
            if 0 <= x < w and 0 <= y < h:
                z = self.depth_image[y, x]
                if z > 0:
                    # 像素 → 相机 3D
                    px = (x - self.cx) * z / self.fx
                    py = (y - self.cy) * z / self.fy
                    forward = -py  # 机器人前方
                    print(f'点击 ({x},{y}): '
                          f'3D=({px:.2f}, {-py:.2f}, {z:.2f})m  '
                          f'forward={forward:.2f}m')

    def rgb_cb(self, msg):
        self.rgb_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

    def depth_cb(self, msg):
        self.depth_image = self.bridge.imgmsg_to_cv2(msg, '32FC1')

    def camera_info_cb(self, msg):
        self.fx, self.fy = msg.k[0], msg.k[4]
        self.cx, self.cy = msg.k[2], msg.k[5]
        self.destroy_subscription(self.camera_info_sub)

    def spin_once(self):
        rclpy.spin_once(self, timeout_sec=0.05)

        if self.rgb_image is None or self.depth_image is None:
            return

        # 构建显示：左侧 RGB + 右侧深度热力图
        rgb_disp = self.rgb_image.copy()
        depth_disp = self.depth_image.copy()
        depth_disp = np.clip(depth_disp, 0, 3.0)
        depth_heat = cv2.applyColorMap(
            (depth_disp * 85).astype(np.uint8), cv2.COLORMAP_JET)

        # 标注 ROI 在 RGB 上的大概区域
        if self.fx > 0:
            # 画 ROI 近似边界线
            h, w = rgb_disp.shape[:2]
            # Y_min → 图像底部附近 (forward=0.1m 对应 depth≈0.4m, py≈...)
            # 简化：画两条水平线表示前后边界
            y_near = int(h * 0.5)    # 近边界 (Y_max, ~0.5m)
            y_far  = int(h * 0.3)    # 远边界 (Y_min, ~0.1m)
            cv2.line(rgb_disp, (0, y_near), (w, y_near), (0, 255, 255), 1)
            cv2.line(rgb_disp, (0, y_far), (w, y_far), (0, 255, 255), 1)
            cv2.putText(rgb_disp, f'Y:{self.roi_y_min}-{self.roi_y_max}cm',
                        (10, 20), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (0, 255, 255), 1)

        # HUD 信息
        cv2.putText(rgb_disp,
                    f'ROI X:({self.roi_x_min},{self.roi_x_max})cm '
                    f'Z<{self.roi_z_max}cm goal={self.goal_depth}cm',
                    (10, rgb_disp.shape[0]-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

        # 并排显示
        combined = np.hstack([rgb_disp, depth_heat])
        cv2.imshow('Depth Follow Tuner', combined)

        if cv2.waitKey(1) & 0xFF == 27:
            raise KeyboardInterrupt


def main():
    rclpy.init()
    node = DepthFollowTuner()
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
