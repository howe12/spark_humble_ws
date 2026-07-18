#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
垃圾分类推理节点 — ROS2 迁移版
订阅图像话题，加载 joblib 决策树模型进行实时分类。

ROS1 → ROS2 关键 API 变更:
  - rospy → rclpy (导入, init, spin, shutdown)
  - rospy.init_node() → rclpy.init() + 显式创建 Node 对象
  - rospy.get_param('~name') → self.declare_parameter() + self.get_parameter()
  - rospy.Publisher / rospy.Subscriber → self.create_publisher() / self.create_subscription()
  - rospy.spin() → rclpy.spin(node)
  - rospy.loginfo() → self.get_logger().info()
  - 不再需要 anonymous=True

特征提取 (12维):
  几何(5): aspect_ratio, extent, circularity, rectangularity, contour_complexity
  颜色(5): mean_hue, mean_saturation, white_ratio, highlight_ratio, color_consistency
  纹理(2): texture_entropy, texture_contrast  ← 使用向量化 numpy GLCM, 避免逐像素 Python 循环
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
# 向量化 GLCM 计算 — 替代原始的双重 for 循环
# =============================================================================

def _compute_glcm_vectorized(gray_img, mask=None, levels=16, distances=None, angles=None):
    """
    使用向量化 numpy 操作计算灰度共生矩阵 (GLCM) 的对比度和熵。
    无 Python 逐像素循环, 性能远优于原始实现。

    Args:
        gray_img: 2D uint8 灰度图像。
        mask:     可选的 2D 掩膜 (非零区域参与计算)。
        levels:   量化灰度级数 (默认 16)。
        distances: 像素距离列表 (默认 [1, 2])。
        angles:    角度列表 (默认 0°, 45°, 90°, 135°)。

    Returns:
        dict: {'contrast': float, 'energy': float}  取多方向平均
    """
    if distances is None:
        distances = [1, 2]
    if angles is None:
        angles = [0, np.pi / 4, np.pi / 2, 3 * np.pi / 4]

    # 应用掩膜
    if mask is not None:
        gray_img = gray_img.copy()
        gray_img[mask == 0] = 0

    # 量化到 levels 个灰度级
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

            # 有效源区域范围
            r_from = max(0, -dr)
            r_to = min(rows, rows - dr)
            c_from = max(0, -dc)
            c_to = min(cols, cols - dc)

            if r_to <= r_from or c_to <= c_from:
                continue

            rr, cc = np.meshgrid(np.arange(r_from, r_to),
                                 np.arange(c_from, c_to),
                                 indexing='ij')
            rr_flat = rr.ravel()
            cc_flat = cc.ravel()

            src_vals = quantized[rr_flat, cc_flat]
            dst_vals = quantized[rr_flat + dr, cc_flat + dc]

            # 向量化: 将 (src, dst) 对映射到一维索引, 用 bincount 统计
            pair_idx = src_vals * levels + dst_vals
            glcm_flat = np.bincount(pair_idx, minlength=levels * levels)
            glcm = glcm_flat.reshape(levels, levels).astype(np.float64)

            total = glcm.sum()
            if total == 0:
                continue
            glcm /= total

            # 计算对比度和能量
            i = np.arange(levels, dtype=np.float64)
            j = np.arange(levels, dtype=np.float64)
            ii, jj = np.meshgrid(i, j, indexing='ij')
            diff = np.abs(ii - jj)

            props['contrast'] += np.sum(glcm * diff ** 2)
            props['energy'] += np.sum(glcm ** 2)
            pair_count += 1

    if pair_count > 0:
        for k in props:
            props[k] /= pair_count

    return props


# =============================================================================
# WasteClassifierNode — ROS2 Node
# =============================================================================

class WasteClassifierNode(Node):
    """垃圾分类 ROS2 节点"""

    def __init__(self):
        super().__init__('waste_classifier')

        # --- 声明参数 ---
        self.declare_parameter('image_topic', '/camera/color/image_raw')
        self.declare_parameter('model_file', 'waste_classifier.pkl')

        # --- 获取参数值 ---
        image_topic = self.get_parameter('image_topic').get_parameter_value().string_value
        model_file = self.get_parameter('model_file').get_parameter_value().string_value

        # --- 加载模型 ---
        # 如果 model_file 是相对路径, 相对于包目录解析
        if not os.path.isabs(model_file):
            pkg_dir = os.path.dirname(os.path.abspath(__file__))
            model_file = os.path.join(pkg_dir, '..', 'models', model_file)
        self.model = joblib.load(model_file)
        self.get_logger().info(f'模型已加载: {model_file}')

        # --- 类别名称 (须与训练时一致) ---
        self.class_names = ['plastic_bottle', 'can', 'battery', 'seed', 'tissue']

        # --- cv_bridge ---
        self.bridge = CvBridge()

        # --- 目标图像尺寸 ---
        self.target_size = (200, 200)

        # --- 发布者 ---
        self.result_pub = self.create_publisher(String, '/waste_classification', 1)
        self.confidence_pub = self.create_publisher(Float32, '/waste_classification/confidence', 1)

        # --- 订阅者 ---
        self.image_sub = self.create_subscription(
            Image, image_topic, self.image_callback, 1)

        self.get_logger().info('垃圾分类节点已启动')
        self.get_logger().info(f'订阅话题: {image_topic}')
        self.get_logger().info('发布话题: /waste_classification')

    # -------------------------------------------------------------------------
    # 特征提取
    # -------------------------------------------------------------------------

    def extract_features(self, image):
        """
        提取图像特征 (12维)。

        Returns:
            np.ndarray (12,) 或 None (无法提取时)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # --- 自适应阈值 + 形态学 + 轮廓 ---
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
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

        # --- 几何特征 (5维) ---
        x, y, w, h = cv2.boundingRect(contour)

        # 1. 长宽比
        aspect_ratio = float(max(w, h)) / min(w, h) if min(w, h) > 0 else 0.0

        # 2. 致密度 (convex hull 面积比)
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        extent = float(area) / hull_area if hull_area > 0 else 0.0

        # 3. 圆形度
        perimeter = cv2.arcLength(contour, True)
        circularity = (4.0 * np.pi * area) / (perimeter * perimeter) if perimeter > 0 else 0.0

        # 4. 矩形度
        rect_area = float(w * h)
        rectangularity = area / rect_area if rect_area > 0 else 0.0

        # 5. 轮廓复杂度
        contour_complexity = float(len(contour)) / perimeter if perimeter > 0 else 0.0

        geometric_features = [aspect_ratio, extent, circularity,
                              rectangularity, contour_complexity]

        # --- 颜色特征 (5维) ---
        mask = np.zeros(gray.shape, dtype=np.uint8)
        cv2.drawContours(mask, [contour], 0, 255, -1)
        mask_pixels = np.sum(mask > 0)
        mean_val = cv2.mean(hsv, mask=mask)

        # 6. 平均色调
        mean_hue = mean_val[0] / 180.0

        # 7. 平均饱和度
        mean_saturation = mean_val[1] / 255.0

        # 8. 白色区域比例 (HSV 白区)
        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 30, 255])
        white_mask = cv2.inRange(hsv, lower_white, upper_white)
        white_ratio = (np.sum(white_mask > 0) / mask_pixels) if mask_pixels > 0 else 0.0

        # 9. 高光比例 (RGB > 200)
        highlight_mask = cv2.inRange(image, (200, 200, 200), (255, 255, 255))
        highlight_ratio = (np.sum(highlight_mask > 0) / mask_pixels) if mask_pixels > 0 else 0.0

        # 10. 颜色一致性
        hsv_roi = hsv[mask > 0]
        if len(hsv_roi) > 0:
            color_std = np.std(hsv_roi, axis=0)
            color_consistency = 1.0 / (1.0 + np.mean(color_std) / 255.0)
        else:
            color_consistency = 0.0

        color_features = [mean_hue, mean_saturation, white_ratio,
                          highlight_ratio, color_consistency]

        # --- 纹理特征 (2维) — 向量化 GLCM ---
        glcm_props = _compute_glcm_vectorized(
            gray, mask=mask, levels=16,
            distances=[1, 2],
            angles=[0, np.pi / 4, np.pi / 2, 3 * np.pi / 4])

        # 11. 纹理熵 (对应训练中的 energy, 命名遵循任务约定)
        texture_entropy = np.clip(glcm_props['energy'] * 10.0, 0.0, 1.0)

        # 12. 纹理对比度
        texture_contrast = np.clip(glcm_props['contrast'] / 50.0, 0.0, 1.0)

        texture_features = [texture_entropy, texture_contrast]

        # --- 合并 ---
        features = geometric_features + color_features + texture_features
        return np.array(features, dtype=np.float64)

    # -------------------------------------------------------------------------
    # 回调
    # -------------------------------------------------------------------------

    def image_callback(self, msg):
        """图像回调: 转换 → 预处理 → 特征提取 → 推理 → 发布"""
        try:
            # ROS Image → OpenCV BGR
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

            # 缩放到目标尺寸
            img = cv2.resize(cv_image, self.target_size)

            # 特征提取
            features = self.extract_features(img)
            if features is None:
                return

            # 模型推理
            prediction = self.model.predict([features])[0]
            confidence = self.model.predict_proba([features])[0].max()

            # 发布分类结果
            result_msg = String()
            result_msg.data = self.class_names[int(prediction)]
            self.result_pub.publish(result_msg)

            # 发布置信度
            confidence_msg = Float32()
            confidence_msg.data = float(confidence)
            self.confidence_pub.publish(confidence_msg)

            self.get_logger().info(
                f'分类结果: {self.class_names[int(prediction)]} '
                f'(置信度: {confidence:.2f})')

        except Exception as e:
            self.get_logger().warn(f'分类失败: {e}')


# =============================================================================
# main
# =============================================================================

def main(args=None):
    rclpy.init(args=args)
    node = WasteClassifierNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
