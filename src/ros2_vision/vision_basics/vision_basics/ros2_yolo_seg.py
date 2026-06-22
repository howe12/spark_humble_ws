#!/usr/bin/env python3
"""04-2 YOLO实例分割: ROS2 相机实时实例分割

订阅 D435 彩色图像 → YOLOv8n-seg 推理 → mask 叠加显示。
与 ros2_yolo.py 的唯一区别: 模型加 -seg, 输出含遮罩。
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import os
from ultralytics import YOLO


MODEL_NAME = 'yolov8n-seg.pt'
local_model = os.path.expanduser(
    f'~/Music/spark_humble/src/spark_app/spark_yolov8/model/{MODEL_NAME}')
MODEL = local_model if os.path.exists(local_model) else MODEL_NAME


class YoloSegNode(Node):
    def __init__(self):
        super().__init__('yolo_seg_node')
        self.bridge = CvBridge()
        self.model = YOLO(MODEL)
        self.conf = 0.3

        self.sub = self.create_subscription(
            Image, '/camera/camera/color/image_raw', self.callback, 10)
        self.get_logger().info(f'YOLOv8n-seg 已加载 | 等待相机帧')

    def callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

        results = self.model(frame, conf=self.conf, verbose=False)
        annotated = results[0].plot()

        speed = results[0].speed
        if speed and 'inference' in speed:
            fps = 1000.0 / speed['inference']
            cv2.putText(annotated, f'FPS: {int(fps)}', (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow('YOLOv8-seg Camera', annotated)
        cv2.waitKey(1)


def main():
    rclpy.init()
    node = YoloSegNode()
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
