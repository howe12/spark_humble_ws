#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""4.1 颜色识别跟随 — ROS2 迁移

ROS1 follow.py → ROS2 color_follow.py
订阅: /camera/color/image_raw + /camera/aligned_depth_to_color/image_raw
发布: /cmd_vel (Twist)

Bug 修复:
  - HSV 通道选择错误: 不再对 H 通道做阈值90（90=青色，蓝≈100-130），
    改用 inRange 直接生成掩膜后做形态学处理
  - CvBridge 在 __init__ 中实例化一次，不在回调中反复创建
  - 随机偏移边界检查: np.random.uniform 可能越界，增加 clamp
"""

import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np


class ColorFollowNode(Node):
    def __init__(self):
        super().__init__('color_follow_node')

        # ── CvBridge 只创建一次 ──
        self.bridge = CvBridge()

        # ── 发布 /cmd_vel ──
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # ── 订阅 RGB & 深度图像 ──
        self.sub_image = self.create_subscription(
            Image, '/camera/color/image_raw', self.image_cb, 10)
        self.sub_depth = self.create_subscription(
            Image, '/camera/aligned_depth_to_color/image_raw', self.depth_cb, 10)

        # ── 全局变量 ──
        self.obj_x = 0.0
        self.obj_y = 0.0
        self.obj_dis = 0.0
        self.forward_speed = 0.1
        self.image_width = 640   # 默认图像宽度
        self.image_height = 480  # 默认图像高度

        self.get_logger().info('颜色跟随节点已启动')

    # ── RGB 回调 ──
    def image_cb(self, msg: Image):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        except Exception as e:
            self.get_logger().error(f'图像转换失败: {e}')
            return

        self.image_height, self.image_width = cv_image.shape[:2]

        # ── HSV 色彩空间转换 + 蓝色掩膜 ──
        # 蓝色在 OpenCV HSV 中 H ≈ 100-130 (映射后)
        hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
        lower_blue = np.array([100, 90, 80])
        upper_blue = np.array([140, 255, 255])
        mask = cv2.inRange(hsv, lower_blue, upper_blue)

        # ── 形态学处理: 去噪 + 填充 ──
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.erode(mask, None, iterations=4)
        mask = cv2.dilate(mask, None, iterations=4)

        # ── 轮廓检测 ──
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        if len(contours) > 0:
            # 找到最近的目标方块
            dis_min = float(self.image_width)
            best_contour = None
            for c in contours:
                rect = cv2.minAreaRect(c)
                box = cv2.boxPoints(rect)
                box = np.int0(box)
                x_mid = float(box[:, 0].mean())
                y_mid = float(box[:, 1].mean())
                distance = math.sqrt((x_mid - self.image_width / 2) ** 2 +
                                     (self.image_height - y_mid) ** 2)
                if distance < dis_min:
                    dis_min = distance
                    best_contour = c
                    self.obj_x = x_mid
                    self.obj_y = y_mid

            if best_contour is not None:
                cv2.drawContours(cv_image, [best_contour], 0, (0, 255, 0), 2)
                cv2.circle(cv_image, (int(self.obj_x), int(self.obj_y)),
                           5, (0, 0, 255), -1)
        else:
            self.obj_x = 0.0
            self.obj_y = 0.0

        cv2.imshow('contours', cv_image)
        cv2.waitKey(1)

    # ── 深度回调 ──
    def depth_cb(self, msg: Image):
        try:
            depth_data = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
        except Exception as e:
            self.get_logger().error(f'深度图像转换失败: {e}')
            return

        if depth_data is None or self.obj_x == 0.0:
            self.cmd_vel_pub.publish(Twist())
            return

        height, width = depth_data.shape
        x = int(self.obj_x)
        y = int(self.obj_y)

        # ── 边界检查 + 随机偏移 (clamp 防止越界) ──
        distance = 0.0
        if 0 <= y < height and 0 <= x < width:
            distance = float(depth_data[y, x]) / 1000.0

        if distance <= 0.1:
            try:
                m = np.random.uniform(low=-5, high=5)
                new_y = int(np.clip(y + m, 0, height - 1))
                new_x = int(np.clip(x + m, 0, width - 1))
                distance = float(depth_data[new_y, new_x]) / 1000.0
            except (IndexError, ValueError):
                pass  # clamp 已处理边界

        self.obj_dis = distance

        # ── 方向判断 ──
        half_w = width / 2.0
        if self.obj_x >= half_w - 20 and self.obj_x <= half_w + 20:
            self.move(self.forward_speed, 0.0, distance)
        elif self.obj_x > half_w + 20:
            self.move(self.forward_speed, -0.2, distance)
        elif self.obj_x < half_w - 20 and self.obj_x != 0.0:
            self.move(self.forward_speed, 0.2, distance)
        else:
            self.cmd_vel_pub.publish(Twist())

    # ── 移动控制 ──
    def move(self, x: float, z: float, dis: float):
        if 0.39 < dis < 0.7:
            x1 = 1.0
        elif 0.35 <= dis <= 0.37:
            x1 = 0.0
        elif dis < 0.33:
            x1 = -1.0
        else:
            x1 = 0.0

        twist = Twist()
        twist.linear.x = x * x1
        twist.angular.z = z
        self.cmd_vel_pub.publish(twist)


def main(args=None):
    rclpy.init(args=args)
    node = ColorFollowNode()
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
