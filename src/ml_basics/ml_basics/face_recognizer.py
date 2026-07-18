#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""4.3 人脸识别 — LBPH 识别器 (ROS2 迁移)

ROS1 detect.py → ROS2 face_recognizer.py
订阅 /camera/color/image_raw，使用 LBPH 模型实时识别摄像头中出现的人脸

Bug 修复:
  - bare except → 捕获具体异常 (IndexError, ValueError)
  - CascadeClassifier 在 __init__ 中加载一次，不在每帧回调中重复加载
  - names.sort() → sorted(names, key=int) (按数字排序, 而非字典序)
  - CvBridge 在 __init__ 中实例化一次
  - 级联器使用 cv2.data.haarcascades
"""

import os
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np


class FaceRecognizerNode(Node):
    def __init__(self):
        super().__init__('face_recognizer_node')

        self.bridge = CvBridge()

        # ── 参数 ──
        self.declare_parameter('image_dir', '')
        self.declare_parameter('model_file', '')
        self.declare_parameter('confidence_threshold', 80.0)

        image_dir_param = self.get_parameter('image_dir').get_parameter_value().string_value
        model_file_param = self.get_parameter('model_file').get_parameter_value().string_value
        self.confidence_threshold = self.get_parameter(
            'confidence_threshold').get_parameter_value().double_value

        if image_dir_param:
            self.image_dir = image_dir_param
        else:
            self.image_dir = os.path.join(os.path.expanduser('~'), 'face_images')

        if model_file_param:
            self.model_file = model_file_param
        else:
            self.model_file = os.path.join(self.image_dir, 'trainer.yml')

        # ── 加载名称列表 (按数字排序) ──
        self.names = self._load_names(self.image_dir)
        self.get_logger().info(f'已加载名称: {self.names}')

        # ── 级联分类器 (只加载一次) ──
        face_xml = os.path.join(cv2.data.haarcascades,
                                'haarcascade_frontalface_alt2.xml')
        self.face_detector = cv2.CascadeClassifier(face_xml)
        if self.face_detector.empty():
            self.get_logger().error(f'无法加载级联模型: {face_xml}')

        # ── LBPH 识别器 ──
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        if os.path.exists(self.model_file):
            self.recognizer.read(self.model_file)
            self.get_logger().info(f'已加载识别模型: {self.model_file}')
        else:
            self.get_logger().warn(f'模型文件不存在: {self.model_file}')

        # ── 订阅 ──
        self.sub_image = self.create_subscription(
            Image, '/camera/color/image_raw', self.image_cb, 10)

        self.get_logger().info('人脸识别节点已启动')

    def _load_names(self, image_dir: str):
        """从图片目录加载名称列表 (按数字ID排序)"""
        names = []
        if not os.path.isdir(image_dir):
            return names

        valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.pgm'}
        for filename in os.listdir(image_dir):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in valid_extensions:
                continue
            # 提取文件名 (不含扩展名)
            name_id = os.path.splitext(filename)[0]
            names.append(name_id)

        # 按数字排序 (而非字典序: 1,2,3,...,10 而不是 1,10,2,...) 
        try:
            names = sorted(names, key=int)
        except ValueError:
            # 如果包含非数字文件名，回退到字符串排序
            names.sort()
        return names

    def image_cb(self, msg: Image):
        try:
            img = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        except Exception as e:
            self.get_logger().error(f'图像转换失败: {e}')
            return

        img0 = img.copy()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # ── 人脸检测 ──
        faces = self.face_detector.detectMultiScale(
            gray, 1.1, 5,
            cv2.CASCADE_SCALE_IMAGE,
            (100, 100), (300, 300)
        )

        for (x, y, w, h) in faces:
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.circle(img, (x + w // 2, y + h // 2),
                       w // 2, (0, 255, 0), 1)

            # ── LBPH 识别 ──
            try:
                person_id, confidence = self.recognizer.predict(
                    gray[y:y + h, x:x + w])
            except Exception as e:
                self.get_logger().error(f'人脸识别失败: {e}')
                continue

            if confidence > self.confidence_threshold:
                label = 'unknown'
            else:
                try:
                    label = str(self.names[person_id - 1])
                except (IndexError, ValueError):
                    label = f'ID:{person_id}'

            cv2.putText(img, label, (x + 10, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 1)

            # ── 指定人物抓拍 ──
            try:
                if int(label) == 3:
                    save_path = os.path.join(self.image_dir, 'photo.jpg')
                    cv2.imwrite(save_path, img0)
                    self.get_logger().info(f'识别到目标人物 {label}，已抓拍')
            except (ValueError, TypeError):
                pass  # label 不是数字时不抓拍

        cv2.imshow('Face Recognition', img)
        cv2.waitKey(10)


def main(args=None):
    rclpy.init(args=args)
    node = FaceRecognizerNode()
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
