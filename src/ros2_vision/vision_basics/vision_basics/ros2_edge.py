#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np


class ImgEdge(Node):
    """订阅相机图像，实时显示原图 + Sobel 边缘图"""

    def __init__(self):
        super().__init__('ImgEdge')
        self.image_sub = self.create_subscription(
            Image,
            '/camera/color/image_raw',
            self.show,
            10
        )
        self.bridge = CvBridge()

    def show(self, img):
        # ROS 消息 → OpenCV 图像
        color_image = self.bridge.imgmsg_to_cv2(img, desired_encoding='bgr8')
        # 转灰度
        gray = cv2.cvtColor(color_image, cv2.COLOR_BGR2GRAY)
        # Sobel 边缘检测
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        sobel_magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
        # 归一化
        sobel_magnitude = np.uint8(sobel_magnitude / sobel_magnitude.max() * 255)
        # 显示
        cv2.imshow('original', color_image)
        cv2.imshow('edges', sobel_magnitude)
        cv2.waitKey(1)


def main(args=None):
    rclpy.init(args=args)
    node = ImgEdge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        print("Shutting down")
    finally:
        node.destroy_node()
        rclpy.shutdown()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
