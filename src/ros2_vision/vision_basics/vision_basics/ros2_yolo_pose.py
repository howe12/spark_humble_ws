#!/usr/bin/env python3
"""04-3 YOLO姿态识别: ROS2 D435 相机实时姿态估计

订阅 D435 彩色图像 → YOLOv8n-pose 推理 → 绘制火柴人+FPS → 显示。
与 ros2_yolo.py 的唯一区别: 模型换 yolov8n-pose.pt, 输出含关键点。

运行前确保:
  source install/setup.bash
  ros2 launch spark_bringup d435.launch.py   # 或类似启动相机
  export DISPLAY=:0
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import os
from ament_index_python.packages import get_package_share_directory
from ultralytics import YOLO

MODEL_PATH = os.path.join(
    get_package_share_directory('vision_basics'), 'model', 'yolov8n-pose.pt')

# ── COCO 关键点名称 ──
KEYPOINT_NAMES = {
    0: "鼻子",  1: "左眼",  2: "右眼",
    3: "左耳",  4: "右耳",
    5: "左肩",  6: "右肩",
    7: "左肘",  8: "右肘",
    9: "左腕", 10: "右腕",
   11: "左髋", 12: "右髋",
   13: "左膝", 14: "右膝",
   15: "左踝", 16: "右踝",
}

class YoloPoseNode(Node):
    def __init__(self):
        super().__init__('yolo_pose_node')
        self.bridge = CvBridge()
        self.model = YOLO(MODEL_PATH)
        self.conf = 0.3

        # Spark D435 彩色图像话题
        self.sub = self.create_subscription(
            Image, '/camera/camera/color/image_raw', self.callback, 10)
        self.get_logger().info(f'YOLOv8n-pose 已加载 | 等待 D435 相机帧')

    def callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

        results = self.model(frame, conf=self.conf, verbose=False)
        annotated = results[0].plot()

        # ── FPS ──
        speed = results[0].speed
        if speed and 'inference' in speed:
            fps = 1000.0 / speed['inference']
            cv2.putText(annotated, f'FPS: {int(fps)}', (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # ── 额外：打印关键点信息到终端 ──
        keypoints = results[0].keypoints
        if keypoints is not None and keypoints.xy.shape[0] > 0:
            kp = keypoints.xy[0]    # 第一个人的关键点
            conf = keypoints.conf[0]
            # 只打印高置信度关键点
            high_conf = [(i, KEYPOINT_NAMES.get(i, f'kp{i}'),
                          int(kp[i][0]), int(kp[i][1]), float(conf[i]))
                         for i in range(17) if conf[i] > 0.5]
            if high_conf:
                parts = [f'{name}({x},{y})' for _, name, x, y, _ in high_conf[:6]]
                self.get_logger().info(f'  {" ".join(parts)}')

        cv2.imshow('YOLOv8 Pose - D435', annotated)
        cv2.waitKey(1)


def main():
    rclpy.init()
    node = YoloPoseNode()
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
