#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""4.2 笑脸检测抓拍 — ROS2 迁移

ROS1 smile_detect.py → ROS2 face_smile_detect.py
订阅: /camera/color/image_raw
检测人脸后查找笑脸特征，检测到即保存照片

Bug 修复:
  - Haar 级联文件路径: 从 /usr/share/opencv4/ 改为 cv2.data.haarcascades
  - 缩进错误: 修复 ROI 操作中的多余缩进
  - CvBridge 在 __init__ 中实例化一次
"""

import os
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np


class FaceSmileDetectNode(Node):
    def __init__(self):
        super().__init__('face_smile_detect_node')

        # ── CvBridge 只创建一次 ──
        self.bridge = CvBridge()

        # ── 级联分类器 (使用 cv2 内置路径) ──
        face_xml = os.path.join(cv2.data.haarcascades,
                                'haarcascade_frontalface_default.xml')
        smile_xml = os.path.join(cv2.data.haarcascades,
                                 'haarcascade_smile.xml')
        self.facer = cv2.CascadeClassifier(face_xml)
        self.smile = cv2.CascadeClassifier(smile_xml)

        # ── 输出目录 ──
        self.save_dir = os.path.join(os.path.expanduser('~'), 'smile_photos')
        os.makedirs(self.save_dir, exist_ok=True)
        self.photo_count = 0

        # ── 订阅 RGB ──
        self.sub_image = self.create_subscription(
            Image, '/camera/color/image_raw', self.image_cb, 10)

        self.get_logger().info(f'笑脸检测节点已启动 | 保存路径: {self.save_dir}')

    def image_cb(self, msg: Image):
        try:
            img = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        except Exception as e:
            self.get_logger().error(f'图像转换失败: {e}')
            return

        img0 = img.copy()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # ── 人脸检测 ──
        faces = self.facer.detectMultiScale(gray, 1.2, 5)

        for (x, y, w, h) in faces:
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 2)

            # ── ROI: 仅人脸区域 (缩进已修正) ──
            roi_gray = gray[y:y + h, x:x + w]
            roi_color = img[y:y + h, x:x + w]

            # ── 笑脸检测 ──
            smiler = self.smile.detectMultiScale(roi_gray, 1.5, 15)
            for (ex, ey, ew, eh) in smiler:
                cv2.rectangle(roi_color, (ex, ey),
                              (ex + ew, ey + eh), (0, 255, 0), 2)
                # 保存照片
                filename = os.path.join(self.save_dir,
                                        f'smile_{self.photo_count:04d}.jpg')
                cv2.imwrite(filename, img0)
                self.get_logger().info(f'检测到笑脸，已保存: {filename}')
                self.photo_count += 1

        cv2.imshow('Smile Detect', img)
        cv2.waitKey(1)


def main(args=None):
    rclpy.init(args=args)
    node = FaceSmileDetectNode()
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
