#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""4.3 人脸识别 — 图像采集器 (ROS2 迁移)

ROS1 get_img.py → ROS2 face_capture.py
订阅 /camera/color/image_raw，按 's' 键保存当前帧图片

Bug 修复:
  - CvBridge 在 __init__ 中实例化一次
  - 输出到功能包下的 config/image/ 目录 (通过参数配置)
"""

import os
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2


class FaceCaptureNode(Node):
    def __init__(self):
        super().__init__('face_capture_node')

        # ── CvBridge 只创建一次 ──
        self.bridge = CvBridge()

        # ── 参数: 图像保存路径 ──
        self.declare_parameter('save_dir', '')
        save_dir_param = self.get_parameter('save_dir').get_parameter_value().string_value
        if save_dir_param:
            self.save_dir = save_dir_param
        else:
            # 默认: ~/face_images/
            self.save_dir = os.path.join(os.path.expanduser('~'), 'face_images')
        os.makedirs(self.save_dir, exist_ok=True)

        self.num = 1

        # ── 订阅 RGB ──
        self.sub_image = self.create_subscription(
            Image, '/camera/color/image_raw', self.image_cb, 10)

        self.get_logger().info(f'人脸采集节点已启动 | 按下 [s] 保存图片至 {self.save_dir}')

    def image_cb(self, msg: Image):
        try:
            img = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        except Exception as e:
            self.get_logger().error(f'图像转换失败: {e}')
            return

        cv2.imshow('Face Capture', img)

        key = cv2.waitKey(30)
        if key == ord('s') or key == ord('S'):
            filename = os.path.join(self.save_dir, f'{self.num}.jpg')
            cv2.imwrite(filename, img)
            self.get_logger().info(f'已保存: {filename}')
            self.num += 1


def main(args=None):
    rclpy.init(args=args)
    node = FaceCaptureNode()
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
