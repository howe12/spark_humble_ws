#!/usr/bin/env python3
"""03-3 物体识别抓取: ROS2 实时颜色检测 + 深度 + 3D 坐标 + TF

订阅 RGB + 对齐深度图 → HSV 检测颜色方块 → ROI 深度采样
→ 像素→相机 3D 坐标 → 发布 TF → cv2 可视化

这是抓取管线的视觉核心——后续课程接机械臂即可完成抓取。
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge
import cv2
import numpy as np
import math

# TF2
from geometry_msgs.msg import TransformStamped
import tf2_ros

# D435 默认内参 (640×480，运行时从 CameraInfo 更新)
DEFAULT_FX, DEFAULT_FY = 613.4, 612.2
DEFAULT_CX, DEFAULT_CY = 330.2, 240.6


class GraspDetectNode(Node):
    def __init__(self):
        super().__init__('grasp_detect_node')

        self.bridge = CvBridge()
        self.rgb_image = None
        self.depth_image = None

        # 相机内参（从 CameraInfo 获取，这里用默认值）
        self.fx, self.fy = DEFAULT_FX, DEFAULT_FY
        self.cx, self.cy = DEFAULT_CX, DEFAULT_CY

        # 颜色 HSV 阈值
        self.color_targets = {
            'red':    ([0, 120, 80],   [10, 255, 255]),
            'red2':   ([160, 120, 80], [180, 255, 255]),
            'blue':   ([100, 120, 80], [130, 255, 255]),
            'yellow': ([20, 120, 80],  [35, 255, 255]),
        }

        self.kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

        # 订阅
        self.rgb_sub = self.create_subscription(
            Image, '/camera/camera/color/image_raw', self.rgb_cb, 10)
        self.depth_sub = self.create_subscription(
            Image, '/camera/camera/aligned_depth_to_color/image_raw',
            self.depth_cb, 10)
        self.camera_info_sub = self.create_subscription(
            CameraInfo, '/camera/camera/color/camera_info',
            self.camera_info_cb, 10)

        # TF 广播
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)

        self.get_logger().info('抓取检测节点启动 — 等待 RGB + Depth + CameraInfo')

    def camera_info_cb(self, msg):
        """从 CameraInfo 更新内参"""
        self.fx = msg.k[0]
        self.fy = msg.k[4]
        self.cx = msg.k[2]
        self.cy = msg.k[5]
        self.get_logger().info(
            f'内参: fx={self.fx:.1f} fy={self.fy:.1f} '
            f'cx={self.cx:.1f} cy={self.cy:.1f}')
        self.destroy_subscription(self.camera_info_sub)  # 只读一次

    def rgb_cb(self, msg):
        self.rgb_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

    def depth_cb(self, msg):
        self.depth_image = self.bridge.imgmsg_to_cv2(msg, '32FC1')

    def get_depth(self, x, y, radius=10):
        """ROI 中值深度采样"""
        if self.depth_image is None:
            return 0.0
        h, w = self.depth_image.shape
        x1, x2 = max(0, x-radius), min(w, x+radius+1)
        y1, y2 = max(0, y-radius), min(h, y+radius+1)
        roi = self.depth_image[y1:y2, x1:x2]
        valid = roi[roi > 0]
        return float(np.median(valid)) if len(valid) > 20 else 0.0

    def detect_objects(self):
        """HSV 颜色检测 → 返回 [(name, center_x, center_y, angle), ...]"""
        if self.rgb_image is None:
            return []

        hsv = cv2.cvtColor(self.rgb_image, cv2.COLOR_BGR2HSV)
        objects = []

        # 红色（合并两段 H）
        mask_red1 = cv2.inRange(hsv, np.array([0, 120, 80]), np.array([10, 255, 255]))
        mask_red2 = cv2.inRange(hsv, np.array([160, 120, 80]), np.array([180, 255, 255]))
        mask_red = cv2.bitwise_or(mask_red1, mask_red2)

        for name, (lower, upper) in [
            ('red', mask_red),
            ('blue', None),
            ('yellow', None),
        ]:
            if name == 'red':
                mask = mask_red
            else:
                low = np.array(self.color_targets[name][0])
                high = np.array(self.color_targets[name][1])
                mask = cv2.inRange(hsv, low, high)

            mask = cv2.erode(mask, self.kernel, iterations=1)
            mask = cv2.dilate(mask, self.kernel, iterations=1)

            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                if cv2.contourArea(cnt) < 500:
                    continue
                min_rect = cv2.minAreaRect(cnt)
                cx, cy = min_rect[0]
                angle = min_rect[2]
                objects.append((name, int(cx), int(cy), angle))

        return objects

    def pixel_to_camera(self, u, v, Z):
        """像素 → 相机 3D 坐标"""
        X = (u - self.cx) * Z / self.fx
        Y = (v - self.cy) * Z / self.fy
        return X, Y, Z

    def publish_tf(self, name, X, Y, Z, theta):
        """发布物体 TF (相机坐标系 → object_N)"""
        tf_msg = TransformStamped()
        tf_msg.header.stamp = self.get_clock().now().to_msg()
        tf_msg.header.frame_id = 'camera_color_optical_frame'
        tf_msg.child_frame_id = f'object_{name}'

        tf_msg.transform.translation.x = float(X)
        tf_msg.transform.translation.y = float(Y)
        tf_msg.transform.translation.z = float(Z)

        # 物体绕 Z 轴旋转 theta（绕 Y 轴转 180° 补偿相机朝向）
        # 简化: 只传位置，姿态用默认
        tf_msg.transform.rotation.w = 1.0

        self.tf_broadcaster.sendTransform(tf_msg)

    def spin_once(self):
        """手动驱动处理循环（替代 spin）"""
        rclpy.spin_once(self, timeout_sec=0.05)

        if self.rgb_image is None or self.depth_image is None:
            return

        display = self.rgb_image.copy()
        objects = self.detect_objects()

        for name, cx, cy, angle in objects:
            # 深度采样
            Z = self.get_depth(cx, cy, radius=10)
            if Z <= 0 or Z > 5.0:
                continue

            # 3D 坐标
            X, Y, _ = self.pixel_to_camera(cx, cy, Z)

            # 发布 TF
            self.publish_tf(name, X, Y, Z, angle)

            # 可视化
            cv2.circle(display, (cx, cy), 6, (0, 255, 0), -1)
            cv2.putText(display,
                        f'{name} ({X:.2f},{Y:.2f},{Z:.2f})',
                        (cx+10, cy-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv2.imshow('Grasp Detection', display)
        if cv2.waitKey(1) & 0xFF == 27:
            raise KeyboardInterrupt


def main():
    rclpy.init()
    node = GraspDetectNode()
    try:
        while rclpy.ok():
            node.spin_once()
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
