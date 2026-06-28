#!/usr/bin/env python3
"""04-3 YOLO姿态识别: ROS2 实时动作分析节点

订阅 /camera/color/image_raw → YOLOv8n-pose 推理 → 举手检测 + 手臂角度。
发布 /pose_action (String) — 人体动作语义分析结果。

ROS2 参数:
  - image_topic: 相机话题 (默认 /camera/color/image_raw)
  - conf_threshold: 检测置信度 (默认 0.3)
  - display: 是否显示画面 (默认 True, headless 时设 False)
"""

import os
import math
import numpy as np
import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
from ament_index_python.packages import get_package_share_directory
from ultralytics import YOLO

# ── COCO 关键点索引 ──
LEFT_SHOULDER  = 5
RIGHT_SHOULDER = 6
LEFT_ELBOW     = 7
RIGHT_ELBOW    = 8
LEFT_WRIST     = 9
RIGHT_WRIST    = 10


def calc_angle(a, b, c):
    """计算三点夹角 ∠ABC (a=肩, b=肘, c=腕)"""
    v1 = a - b
    v2 = c - b
    cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
    return math.degrees(math.acos(np.clip(cos_angle, -1, 1)))


def analyze_pose(keypoints, person_idx=0):
    """分析单个人体姿态: 举手方向 + 手臂角度

    Returns:
        (text_report, actions) — text_report 是终端可读文本，actions 是结构化 dict
    """
    if keypoints is None or keypoints.xy.shape[0] == 0:
        return None, {}

    kp = keypoints.xy[person_idx]
    conf = keypoints.conf[person_idx]
    lines = []
    actions = {}

    # ── 左臂 ──
    if all(conf[i] > 0.3 for i in [LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST]):
        l_angle = calc_angle(kp[LEFT_SHOULDER], kp[LEFT_ELBOW], kp[LEFT_WRIST])
        l_wrist_y = kp[LEFT_WRIST][1]
        l_shoulder_y = kp[LEFT_SHOULDER][1]
        lines.append(f'L-Arm: {l_angle:.0f} deg')
        actions['left_arm_angle'] = round(l_angle, 1)
        if l_wrist_y < l_shoulder_y and l_angle > 120:
            lines.append('  ^ Left hand raised!')
            actions['left_hand_raised'] = True

    # ── 右臂 ──
    if all(conf[i] > 0.3 for i in [RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST]):
        r_angle = calc_angle(kp[RIGHT_SHOULDER], kp[RIGHT_ELBOW], kp[RIGHT_WRIST])
        r_wrist_y = kp[RIGHT_WRIST][1]
        r_shoulder_y = kp[RIGHT_SHOULDER][1]
        lines.append(f'R-Arm: {r_angle:.0f} deg')
        actions['right_arm_angle'] = round(r_angle, 1)
        if r_wrist_y < r_shoulder_y and r_angle > 120:
            lines.append('  ^ Right hand raised!')
            actions['right_hand_raised'] = True

    return '\n'.join(lines) if lines else 'No complete arm detected', actions


class PoseActionNode(Node):
    """ROS2 姿态动作分析节点"""

    def __init__(self):
        super().__init__('pose_action_node')

        # ── 参数 ──
        self.declare_parameter('image_topic', '/camera/color/image_raw')
        self.declare_parameter('conf_threshold', 0.3)
        self.declare_parameter('display', True)

        image_topic = self.get_parameter('image_topic').value
        self.conf_threshold = self.get_parameter('conf_threshold').value
        self.display = self.get_parameter('display').value

        # ── 模型 ──
        model_path = os.path.join(
            get_package_share_directory('vision_basics'), 'model', 'yolov8n-pose.pt')
        self.model = YOLO(model_path)
        self.get_logger().info(f'模型: {model_path}')

        # ── CvBridge ──
        self.bridge = CvBridge()

        # ── 订阅 + 发布 ──
        self.image_sub = self.create_subscription(
            Image, image_topic, self.image_callback, 10)
        self.action_pub = self.create_publisher(String, '/pose_action', 10)

        # ── 显示窗口 ──
        if self.display:
            cv2.namedWindow('Pose Action Analysis', cv2.WINDOW_NORMAL)
            cv2.resizeWindow('Pose Action Analysis', 800, 600)

        self.get_logger().info(f'订阅: {image_topic} | 发布: /pose_action | display={self.display}')

    def image_callback(self, msg):
        """相机回调: 推理 + 分析 + 发布"""
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        except Exception as e:
            self.get_logger().error(f'CvBridge 转换失败: {e}')
            return

        # ── 推理 ──
        results = self.model(frame, conf=self.conf_threshold, verbose=False)
        annotated = results[0].plot()

        # ── 分析姿态 ──
        text_report, actions = analyze_pose(results[0].keypoints, 0)

        if text_report:
            # 发布分析结果
            msg_out = String()
            msg_out.data = text_report.replace('\n', ' | ')
            self.action_pub.publish(msg_out)

            # 画面叠加文字
            if self.display:
                y_offset = 60
                for line in text_report.split('\n'):
                    cv2.putText(annotated, line, (10, y_offset),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                    y_offset += 25

        if self.display:
            cv2.imshow('Pose Action Analysis', annotated)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                rclpy.shutdown()

    def destroy_node(self):
        if self.display:
            cv2.destroyAllWindows()
        super().destroy_node()


def main():
    rclpy.init()
    node = PoseActionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
