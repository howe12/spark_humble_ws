#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""4.3 人脸识别 — LBPH 训练器 (ROS2 迁移)

ROS1 trainer.py → ROS2 face_trainer.py
读取训练用的人脸图片，训练 LBPH 模型并保存为 .yml 文件

Bug 修复:
  - 文件过滤: 只处理 .jpg/.png/.jpeg 图片，跳过非图片文件
  - 文件名解析: 使用 os.path.splitext 获取不带扩展名的文件名作为 ID
  - CvBridge 在 __init__ 中实例化一次
  - 级联器使用 cv2.data.haarcascades
"""

import os
import rclpy
from rclpy.node import Node
from cv_bridge import CvBridge
import cv2
import numpy as np
from PIL import Image as PILImage


class FaceTrainerNode(Node):
    def __init__(self):
        super().__init__('face_trainer_node')

        self.bridge = CvBridge()

        # ── 参数: 训练图片目录和模型输出路径 ──
        self.declare_parameter('image_dir', '')
        self.declare_parameter('output_model', '')

        image_dir_param = self.get_parameter('image_dir').get_parameter_value().string_value
        output_model_param = self.get_parameter('output_model').get_parameter_value().string_value

        if image_dir_param:
            self.image_dir = image_dir_param
        else:
            self.image_dir = os.path.join(os.path.expanduser('~'), 'face_images')

        if output_model_param:
            self.output_model = output_model_param
        else:
            self.output_model = os.path.join(self.image_dir, 'trainer.yml')

        self.get_logger().info(f'训练图片目录: {self.image_dir}')
        self.get_logger().info(f'模型输出路径: {self.output_model}')

        # ── 执行训练 ──
        faces, ids = self.get_images_and_labels(self.image_dir)
        if len(faces) == 0:
            self.get_logger().error('未找到任何有效人脸图片，训练终止')
            return

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.train(faces, np.array(ids))
        recognizer.write(self.output_model)

        self.get_logger().info(f'训练完成 | 图像ID列表: {ids}')
        self.get_logger().info(f'模型已保存至: {self.output_model}')

    def get_images_and_labels(self, path: str):
        faces_samples = []
        ids = []

        # ── 人脸检测级联器 ──
        face_xml = os.path.join(cv2.data.haarcascades,
                                'haarcascade_frontalface_alt2.xml')
        face_detector = cv2.CascadeClassifier(face_xml)

        if not os.path.isdir(path):
            self.get_logger().error(f'图片目录不存在: {path}')
            return faces_samples, ids

        # ── 只处理图片文件 ──
        valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.pgm'}
        for filename in sorted(os.listdir(path)):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in valid_extensions:
                continue

            image_path = os.path.join(path, filename)

            try:
                # 提取 ID (文件名去掉扩展名的部分，应为数字)
                name_without_ext = os.path.splitext(filename)[0]
                person_id = int(name_without_ext)
            except ValueError:
                self.get_logger().warn(
                    f'文件名 "{filename}" 不是纯数字，跳过 (文件名应为数字ID)')
                continue

            try:
                pil_img = PILImage.open(image_path).convert('L')
                img_numpy = np.array(pil_img, 'uint8')
            except Exception as e:
                self.get_logger().warn(f'无法读取图片 {image_path}: {e}')
                continue

            # 检测人脸
            faces = face_detector.detectMultiScale(img_numpy)
            for (x, y, w, h) in faces:
                ids.append(person_id)
                faces_samples.append(img_numpy[y:y + h, x:x + w])

        self.get_logger().info(f'共找到 {len(faces_samples)} 个人脸样本')
        return faces_samples, ids


def main(args=None):
    rclpy.init(args=args)
    node = FaceTrainerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
