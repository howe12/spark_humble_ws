#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2


class ImgBlur(Node):
    """订阅相机图像，实时显示原图和高斯滤波图"""

    def __init__(self):
        super().__init__('ImgBlur')
        self.image_sub = self.create_subscription(
            Image,
            '/camera/color/image_raw',
            self.show,
            10
        )
        self.bridge = CvBridge()

    def show(self, img):
        # ROS 消息 → OpenCV 图像（bgr8）
        color_image = self.bridge.imgmsg_to_cv2(img, desired_encoding='bgr8')
        # 显示原图
        cv2.imshow('original', color_image)
        # 高斯滤波（5x5，sigma 自动）
        blurred = cv2.GaussianBlur(color_image, (11, 11), 0)
        # 显示滤波图
        cv2.imshow('blurred', blurred)
        cv2.waitKey(1)


def main(args=None):
    rclpy.init(args=args)
    node = ImgBlur()
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
