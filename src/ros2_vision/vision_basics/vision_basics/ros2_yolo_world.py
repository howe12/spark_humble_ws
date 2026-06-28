#!/usr/bin/env python3
"""
ROS2 YOLO-World 开放词汇检测节点

运行时可通过参数动态切换检测类别——无需重启节点。

默认检测: person, cup, bottle, laptop, chair
自定义: ros2 run vision_basics ros2_yolo_world --ros-args -p classes:="person,dog,cat"
"""

import time
import os
import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from ament_index_python.packages import get_package_share_directory
from ultralytics import YOLOWorld

MODEL = os.path.join(
    get_package_share_directory('vision_basics'), 'model', 'yolov8s-world.pt')


class YOLOWorldNode(Node):
    def __init__(self):
        super().__init__('yolo_world_node')

        # 声明参数：检测类别（逗号分隔）
        self.declare_parameter('classes', 'person,cup,bottle,laptop,chair')
        self.declare_parameter('conf', 0.3)

        self.bridge = CvBridge()
        self.model = YOLOWorld(MODEL)

        # 从参数初始设置类别
        self._update_classes()

        # 参数变更回调（运行时动态切换！）
        self.add_on_set_parameters_callback(self._on_param_change)

        self.image_sub = self.create_subscription(
            Image, '/camera/camera/color/image_raw', self.image_callback, 10)

        self.last_fps_time = time.time()
        self.frame_count = 0
        self.fps_value = 0.0

        self.get_logger().info('YOLO-World 节点启动，支持动态类别切换')

    def _update_classes(self):
        classes_str = self.get_parameter('classes').value
        classes = [c.strip() for c in classes_str.split(',') if c.strip()]
        self.model.set_classes(classes)
        self.get_logger().info(f'检测类别: {classes}')

    def _on_param_change(self, params):
        for p in params:
            if p.name == 'classes':
                self._update_classes()
        return rclpy.parameter.SetParametersResult(successful=True)

    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        conf = self.get_parameter('conf').value
        results = self.model(frame, conf=conf, verbose=False)
        annotated = results[0].plot()

        # FPS
        self.frame_count += 1
        now = time.time()
        elapsed = now - self.last_fps_time
        if elapsed >= 1.0:
            self.fps_value = self.frame_count / elapsed
            self.frame_count = 0
            self.last_fps_time = now

        cv2.putText(annotated, f'YOLO-World FPS: {self.fps_value:.1f}',
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow('YOLO-World — ROS2 Dynamic Classes', annotated)
        cv2.waitKey(1)

    def destroy(self):
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = YOLOWorldNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('收到中断信号...')
    finally:
        node.destroy()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
