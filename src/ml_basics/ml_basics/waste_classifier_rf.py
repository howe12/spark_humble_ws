#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
垃圾分类推理节点 — Random Forest (ROS2)
订阅图像话题，加载 Random Forest 模型进行实时分类。

与 waste_classifier.py (决策树) 的区别仅在于模型加载方式。
为避免干扰，发布专属话题 /waste_classification_rf。

用法:
  ros2 run ml_basics waste_classifier_rf
  ros2 run ml_basics waste_classifier_rf --ros-args -p image_topic:=/camera/rgb/image_raw
"""

import os
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String, Float32
import cv2
import numpy as np
import joblib
from cv_bridge import CvBridge


# =============================================================================
# 向量化 GLCM 计算
# =============================================================================

def _compute_glcm_vectorized(gray_img, mask=None, levels=16, distances=None, angles=None):
    if distances is None:
        distances = [1, 2]
    if angles is None:
        angles = [0, np.pi / 4, np.pi / 2, 3 * np.pi / 4]
    if mask is not None:
        gray_img = gray_img.copy()
        gray_img[mask == 0] = 0
    bins = np.linspace(0, 256, levels + 1)
    quantized = np.digitize(gray_img, bins) - 1
    quantized = np.clip(quantized, 0, levels - 1)
    rows, cols = quantized.shape
    props = {'contrast': 0.0, 'energy': 0.0}
    pair_count = 0
    for d in distances:
        for angle in angles:
            dr = int(round(d * np.sin(angle)))
            dc = int(round(d * np.cos(angle)))
            r_from = max(0, -dr)
            r_to = min(rows, rows - dr)
            c_from = max(0, -dc)
            c_to = min(cols, cols - dc)
            if r_to <= r_from or c_to <= c_from:
                continue
            rr, cc = np.meshgrid(np.arange(r_from, r_to),
                                 np.arange(c_from, c_to), indexing='ij')
            src_vals = quantized[rr.ravel(), cc.ravel()]
            dst_vals = quantized[rr.ravel() + dr, cc.ravel() + dc]
            pair_idx = src_vals * levels + dst_vals
            glcm_flat = np.bincount(pair_idx, minlength=levels * levels)
            glcm = glcm_flat.reshape(levels, levels).astype(np.float64)
            total = glcm.sum()
            if total == 0:
                continue
            glcm /= total
            i = np.arange(levels, dtype=np.float64)
            ii, jj = np.meshgrid(i, i, indexing='ij')
            diff = np.abs(ii - jj)
            props['contrast'] += np.sum(glcm * diff ** 2)
            props['energy'] += np.sum(glcm ** 2)
            pair_count += 1
    if pair_count > 0:
        for k in props:
            props[k] /= pair_count
    return props


# =============================================================================
# WasteClassifierRFNode
# =============================================================================

class WasteClassifierRFNode(Node):
    """Random Forest 垃圾分类 ROS2 节点"""

    def __init__(self):
        super().__init__('waste_classifier_rf')

        self.declare_parameter('image_topic', '/camera/color/image_raw')
        self.declare_parameter('model_file', 'waste_random_forest.pkl')

        image_topic = self.get_parameter('image_topic').get_parameter_value().string_value
        model_file = self.get_parameter('model_file').get_parameter_value().string_value

        # --- 加载 Random Forest 模型 (joblib, 同 sklearn) ---
        if not os.path.isabs(model_file):
            pkg_dir = os.path.dirname(os.path.abspath(__file__))
            model_file = os.path.join(pkg_dir, '..', 'models', model_file)
        self.model = joblib.load(model_file)
        self.get_logger().info(f'Random Forest 模型已加载: {model_file}')

        self.class_names = ['plastic_bottle', 'can', 'battery', 'seed', 'tissue']
        self.bridge = CvBridge()
        self.target_size = (200, 200)

        # --- 专属话题 (避免与决策树节点干扰) ---
        self.result_pub = self.create_publisher(String, '/waste_classification_rf', 1)
        self.confidence_pub = self.create_publisher(Float32, '/waste_classification_rf/confidence', 1)

        self.image_sub = self.create_subscription(
            Image, image_topic, self.image_callback, 1)

        self.get_logger().info('Random Forest 垃圾分类节点已启动')
        self.get_logger().info(f'订阅话题: {image_topic}')
        self.get_logger().info('发布话题: /waste_classification_rf')

    def extract_features(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV, 11, 2)
        kernel = np.ones((3, 3), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(contour)
        if area < 100:
            return None

        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = float(max(w, h)) / min(w, h) if min(w, h) > 0 else 0.0
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        extent = float(area) / hull_area if hull_area > 0 else 0.0
        perimeter = cv2.arcLength(contour, True)
        circularity = (4.0 * np.pi * area) / (perimeter * perimeter) if perimeter > 0 else 0.0
        rectangularity = area / float(w * h) if (w * h) > 0 else 0.0
        contour_complexity = float(len(contour)) / perimeter if perimeter > 0 else 0.0
        geometric_features = [aspect_ratio, extent, circularity,
                              rectangularity, contour_complexity]

        mask = np.zeros(gray.shape, dtype=np.uint8)
        cv2.drawContours(mask, [contour], 0, 255, -1)
        mask_pixels = np.sum(mask > 0)
        mean_val = cv2.mean(hsv, mask=mask)
        mean_hue = mean_val[0] / 180.0
        mean_saturation = mean_val[1] / 255.0
        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 30, 255])
        white_mask = cv2.inRange(hsv, lower_white, upper_white)
        white_ratio = (np.sum(white_mask > 0) / mask_pixels) if mask_pixels > 0 else 0.0
        highlight_mask = cv2.inRange(image, (200, 200, 200), (255, 255, 255))
        highlight_ratio = (np.sum(highlight_mask > 0) / mask_pixels) if mask_pixels > 0 else 0.0
        hsv_roi = hsv[mask > 0]
        if len(hsv_roi) > 0:
            color_std = np.std(hsv_roi, axis=0)
            color_consistency = 1.0 / (1.0 + np.mean(color_std) / 255.0)
        else:
            color_consistency = 0.0
        color_features = [mean_hue, mean_saturation, white_ratio,
                          highlight_ratio, color_consistency]

        glcm_props = _compute_glcm_vectorized(gray, mask=mask, levels=16,
                                               distances=[1, 2],
                                               angles=[0, np.pi/4, np.pi/2, 3*np.pi/4])
        texture_entropy = np.clip(glcm_props['energy'] * 10.0, 0.0, 1.0)
        texture_contrast = np.clip(glcm_props['contrast'] / 50.0, 0.0, 1.0)
        texture_features = [texture_entropy, texture_contrast]

        return np.array(geometric_features + color_features + texture_features, dtype=np.float64)

    def image_callback(self, msg):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            img = cv2.resize(cv_image, self.target_size)
            features = self.extract_features(img)
            if features is None:
                return
            prediction = self.model.predict([features])[0]
            confidence = self.model.predict_proba([features])[0].max()
            result_msg = String()
            result_msg.data = self.class_names[int(prediction)]
            self.result_pub.publish(result_msg)
            confidence_msg = Float32()
            confidence_msg.data = float(confidence)
            self.confidence_pub.publish(confidence_msg)
            self.get_logger().info(
                f'[RF] 分类: {self.class_names[int(prediction)]} (置信度: {confidence:.2f})')
        except Exception as e:
            self.get_logger().warn(f'[RF] 分类失败: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = WasteClassifierRFNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
