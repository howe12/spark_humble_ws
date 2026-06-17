#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.logging import get_logger

from std_msgs.msg import Header
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

import cv2


class ImgShow(Node):
    """订阅相机图像话题并显示的 ROS2 节点"""

    def __init__(self):
        # 1. 调用父类的初始化函数，设置节点名称为 'ImgShow'
        super().__init__('ImgShow')
        # 2. 创建日志记录器
        self.logger = get_logger("ImgShow")
        # 3. 创建订阅者，订阅相机彩色图像话题
        #    参数：消息类型 / 话题名 / 回调函数 / 队列长度
        self.image_sub = self.create_subscription(
            Image,
            '/camera/color/image_raw',
            self.show,
            10
        )
        # 4. 创建 CvBridge 对象，用于 ROS 图像消息与 OpenCV 图像之间的转换
        self.bridge = CvBridge()

    def show(self, img):
        """回调函数：处理接收到的图像消息"""
        # 1. 将 ROS 图像消息转换为 OpenCV 图像
        color_image = self.bridge.imgmsg_to_cv2(img, desired_encoding='bgr8')
        # 2. 显示图像
        cv2.imshow('color_image', color_image)
        # 3. 等待 1ms 刷新窗口
        cv2.waitKey(1)


def main(args=None):
    # 1. 初始化 rclpy 库
    rclpy.init(args=args)
    # 2. 创建 ImgShow 节点对象
    node = ImgShow()
    try:
        # 3. 保持节点运行，直到收到中断信号
        rclpy.spin(node)
    except KeyboardInterrupt:
        # 4. 捕获键盘中断异常
        print("Shutting down")
    finally:
        # 5. 销毁节点
        node.destroy_node()
        # 6. 关闭 rclpy
        rclpy.shutdown()
        # 7. 销毁所有 OpenCV 创建的窗口
        cv2.destroyAllWindows()


# 如果此脚本作为主程序执行，则调用 main 函数
if __name__ == '__main__':
    main()
