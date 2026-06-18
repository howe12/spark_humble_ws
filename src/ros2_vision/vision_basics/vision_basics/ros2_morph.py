#!/usr/bin/env python3
"""ROS2 相机实时形态学 — 订阅 /camera/color/image_raw，二值化后做开闭运算去噪"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np


class MorphNode(Node):
    def __init__(self):
        super().__init__('MorphNode')
        self.sub = self.create_subscription(
            Image, '/camera/color/image_raw', self.callback, 10)
        self.bridge = CvBridge()

    def callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 二值化（Otsu 自动阈值）
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # 形态学：开运算去白点 + 闭运算填黑洞
        kernel = np.ones((5, 5), np.uint8)
        opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)

        cv2.imshow('Original', frame)
        cv2.imshow('Binary (Otsu)', binary)
        cv2.imshow('Morph Cleaned (Open+Close)', closed)
        cv2.waitKey(1)


def main():
    rclpy.init()
    node = MorphNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
