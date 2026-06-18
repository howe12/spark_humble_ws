#!/usr/bin/env python3
"""ROS2 相机实时角点检测 — Shi-Tomasi 提取 + 亚像素精化"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np


class CornerNode(Node):
    def __init__(self):
        super().__init__('CornerNode')
        self.sub = self.create_subscription(
            Image, '/camera/color/image_raw', self.callback, 10)
        self.bridge = CvBridge()
        self.criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    def callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Shi-Tomasi 角点检测
        corners = cv2.goodFeaturesToTrack(
            gray, maxCorners=200, qualityLevel=0.01, minDistance=15)

        result = frame.copy()
        if corners is not None:
            # 亚像素精化
            corners_sub = cv2.cornerSubPix(
                gray, corners, winSize=(5, 5),
                zeroZone=(-1, -1), criteria=self.criteria)
            for x, y in corners_sub.reshape(-1, 2):
                cv2.circle(result, (int(x), int(y)), 4, (0, 0, 255), -1)
                cv2.circle(result, (int(x), int(y)), 6, (0, 255, 0), 1)

        cv2.putText(result, f"Corners: {len(corners) if corners is not None else 0}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.imshow('Camera Corners (Shi-Tomasi + SubPix)', result)
        cv2.waitKey(1)


def main():
    rclpy.init()
    node = CornerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
