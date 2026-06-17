#!/usr/bin/env python3
# ROS2 相机图像实时 BGR→HSV 转换

import rclpy
from rclpy.node import Node
from rclpy.logging import get_logger

from std_msgs.msg import Header
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

import cv2


class ImgShow(Node):
    """订阅相机图像话题并实时转换为 HSV 的 ROS2 节点"""

    def __init__(self):
        super().__init__('ImgShow')
        self.logger = get_logger("ImgShow")
        self.image_sub = self.create_subscription(
            Image, '/camera/color/image_raw', self.show, 10)
        self.bridge = CvBridge()

    def show(self, img):
        # 处理接收到的图像信息
        self.color_image = self.bridge.imgmsg_to_cv2(img, desired_encoding='bgr8')
        cv2.imshow('color_image', self.color_image)

        # 将 BGR 图像转换为 HSV 图像
        self.hsv_image = cv2.cvtColor(self.color_image, cv2.COLOR_BGR2HSV)
        cv2.imshow('HSV Image', self.hsv_image)

        cv2.waitKey(1)


def main():
    rclpy.init()
    node = ImgShow()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        print("Shutting down")
    node.destroy_node()
    rclpy.shutdown()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
