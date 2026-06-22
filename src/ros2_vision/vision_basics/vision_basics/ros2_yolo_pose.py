#!/usr/bin/env python3
"""
ROS2 节点：实时 YOLOv8 肢体识别

订阅 /camera/color/image_raw，用 yolov8n-pose.pt 实时检测人体姿态，
在窗口显示火柴人 + FPS 叠加。
"""

import time
import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from ultralytics import YOLO


# ── 模型路径：优先本地 ──
MODEL_NAME = 'yolov8n-pose.pt'
MODEL = MODEL_NAME


class PoseDetectionNode(Node):
    """YOLOv8 Pose 实时肢体识别节点"""

    def __init__(self):
        super().__init__('pose_detection_node')
        self.get_logger().info('启动 YOLOv8 Pose 检测节点...')

        self.bridge = CvBridge()
        self.model = YOLO(MODEL)

        # 订阅 D435 彩色图像
        self.image_sub = self.create_subscription(
            Image,
            '/camera/color/image_raw',
            self.image_callback,
            10,
        )

        self.last_fps_time = time.time()
        self.frame_count = 0
        self.fps_value = 0.0

        self.get_logger().info(f'模型已加载: {MODEL_NAME}，等待相机图像...')

    def image_callback(self, msg):
        # ROS → OpenCV
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        # YOLO-Pose 推理
        results = self.model(frame, conf=0.4, verbose=False)

        # 自动绘制火柴人
        annotated = results[0].plot()

        # ── FPS 计算 ──
        self.frame_count += 1
        now = time.time()
        elapsed = now - self.last_fps_time
        if elapsed >= 1.0:
            self.fps_value = self.frame_count / elapsed
            self.frame_count = 0
            self.last_fps_time = now
            self.get_logger().info(f'FPS: {self.fps_value:.1f}')

        # 叠加 FPS
        cv2.putText(
            annotated, f'FPS: {self.fps_value:.1f}',
            (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
            1, (0, 255, 0), 2,
        )

        cv2.imshow('YOLOv8 Pose — ROS2 实时', annotated)
        cv2.waitKey(1)

    def destroy(self):
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = PoseDetectionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('收到中断信号...')
    finally:
        node.destroy()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
