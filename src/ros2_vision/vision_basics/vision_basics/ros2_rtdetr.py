#!/usr/bin/env python3
"""
ROS2 RT-DETR 实时检测节点

与 ros2_yolo.py 结构完全一致，唯一区别：模型用 rtdetr-l.pt。
证明 ultralytics 统一 API：YOLO 和 RT-DETR 节点代码可互换。
"""

import time
import os
import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from ament_index_python.packages import get_package_share_directory
from ultralytics import YOLO

MODEL = os.path.join(
    get_package_share_directory('vision_basics'), 'model', 'rtdetr-l.pt')


class RTDETRNode(Node):
    def __init__(self):
        super().__init__('rtdetr_node')
        self.get_logger().info('启动 RT-DETR 检测节点...')

        self.bridge = CvBridge()
        self.model = YOLO(MODEL)  # 可用 RTDETR() 或 YOLO()

        self.image_sub = self.create_subscription(
            Image, '/camera/camera/color/image_raw', self.image_callback, 10)

        self.last_fps_time = time.time()
        self.frame_count = 0
        self.fps_value = 0.0
        self.get_logger().info(f'模型加载完成，等待图像...')

    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        results = self.model(frame, conf=0.25, verbose=False)
        annotated = results[0].plot()

        self.frame_count += 1
        now = time.time()
        elapsed = now - self.last_fps_time
        if elapsed >= 1.0:
            self.fps_value = self.frame_count / elapsed
            self.frame_count = 0
            self.last_fps_time = now
            self.get_logger().info(f'FPS: {self.fps_value:.1f}')

        cv2.putText(annotated, f'RT-DETR FPS: {self.fps_value:.1f}',
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow('RT-DETR — ROS2 Real-time', annotated)
        cv2.waitKey(1)

    def destroy(self):
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = RTDETRNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('收到中断信号...')
    finally:
        node.destroy()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
