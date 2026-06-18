#!/usr/bin/env python3
"""02-10 特征匹配: ROS2 相机实时物体检测

从 test_pattern.png 裁取模板 → 实时相机帧中匹配 → 画单应性框。
参考版无此程序——实践版新增，让学生体验特征匹配在真实场景中的应用。
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np
import os


class MatchObjectNode(Node):
    def __init__(self):
        super().__init__('match_object_node')

        # --- 1. 加载模板 ---
        base = os.path.dirname(__file__)
        scene = cv2.imread(os.path.join(base, '..', 'pictures', 'test_pattern.png'))
        self.template = scene[50:250, 350:550]
        self.tmpl_h, self.tmpl_w = self.template.shape[:2]

        self.orb = cv2.ORB_create(500)
        self.kp_t, self.des_t = self.orb.detectAndCompute(self.template, None)
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING)
        self.bridge = CvBridge()

        self.sub = self.create_subscription(
            Image, '/camera/color/image_raw', self.callback, 10)
        self.get_logger().info(
            f'模板加载完成: {self.tmpl_w}x{self.tmpl_h}, '
            f'{len(self.kp_t)} keypoints — 等待相机帧')

    def callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

        # --- 2. ORB 检测 ---
        kp_f, des_f = self.orb.detectAndCompute(frame, None)
        if des_f is None or len(kp_f) < 10:
            cv2.imshow('Object Detection (camera)', frame)
            cv2.waitKey(1)
            return

        # --- 3. KNN 匹配 + 比率测试 ---
        raw = self.bf.knnMatch(self.des_t, des_f, k=2)
        good = [m for m, n in raw if m.distance < 0.75 * n.distance]

        # --- 4. 单应性 + 画框 ---
        if len(good) >= 8:
            src = np.float32(
                [self.kp_t[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst = np.float32(
                [kp_f[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
            H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)

            if H is not None and np.sum(mask) > 4:
                corners = np.float32(
                    [[0, 0], [self.tmpl_w, 0],
                     [self.tmpl_w, self.tmpl_h], [0, self.tmpl_h]]
                ).reshape(-1, 1, 2)
                proj = cv2.perspectiveTransform(corners, H)
                cv2.polylines(frame, [np.int32(proj)], True, (0, 255, 0), 3)
                cv2.putText(frame, f'Match: {np.sum(mask)} inliers',
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                            0.8, (0, 255, 0), 2)

        cv2.imshow('Object Detection (camera)', frame)
        cv2.waitKey(1)


def main():
    rclpy.init()
    node = MatchObjectNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
