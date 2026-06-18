#!/usr/bin/env python3
"""ROS2 相机实时直方图 + CLAHE — 订阅相机，CLAHE 增强暗区，显示直方图"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np


class HistNode(Node):
    def __init__(self):
        super().__init__('HistNode')
        self.sub = self.create_subscription(
            Image, '/camera/color/image_raw', self.callback, 10)
        self.bridge = CvBridge()
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    def callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # CLAHE 增强
        enhanced = self.clahe.apply(gray)

        # 直方图
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist_enh = cv2.calcHist([enhanced], [0], None, [256], [0, 256])
        hist_img = np.zeros((200, 256, 3), dtype=np.uint8)
        hn1 = hist / hist.max() * 180
        hn2 = hist_enh / hist_enh.max() * 180
        for i in range(256):
            cv2.line(hist_img, (i, 199), (i, 199 - int(hn1[i])), (200, 200, 200), 1)
            cv2.line(hist_img, (i, 199), (i, 199 - int(hn2[i])), (0, 255, 0), 1)

        cv2.imshow('Original (Gray)', gray)
        cv2.imshow('CLAHE Enhanced', enhanced)
        cv2.imshow('Histogram (gray=orig, green=enhanced)', hist_img)
        cv2.waitKey(1)


def main():
    rclpy.init()
    node = HistNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
