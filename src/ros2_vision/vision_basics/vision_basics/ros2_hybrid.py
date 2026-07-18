#!/usr/bin/python3.10
"""
================================================================================
ros2_hybrid.py — ROS2 YOLOv8s 初筛 + RT-DETR-L 精检  实时混合检测节点
================================================================================

设计动机
--------
与 hybrid_detector.py 策略相同，但接入 ROS2 相机流实现实时检测：
  1. 订阅 /camera/camera/color/image_raw 话题
  2. 每帧：YOLOv8s (conf=0.1) 初筛 → RT-DETR (conf=0.5) 精检
  3. 画面叠加 FPS + 检测数 + 策略标注

为什么选择混合而非纯 RT-DETR？
  · 纯 RT-DETR 全图推理在 CPU 上太慢（~3s/帧），无法实时
  · YOLO 先缩减候选区，RT-DETR 只需处理小块，整体 ~1s/帧
  · 精度不降反升（RT-DETR 在裁剪区上 conf 更高）

权衡提示
--------
  · 本节点适合「精度优先」场景（巡检、抓取验证）
  · 不适合「速度优先」场景（避障、快速导航）→ 纯 YOLO 更好
  · CPU 下约 0.5-2 FPS，GPU 下可达到 10+ FPS

与 ros2_rtdetr.py 的区别
------------------------
  · ros2_rtdetr.py：单一 RT-DETR 模型，全图推理
  · ros2_hybrid.py：双模型串联，YOLO 预筛选 + RT-DETR 复核

执行流程
--------
  callback():
    1. 接收 ROS2 图像消息 → cv2 格式
    2. YOLO 初筛（低阈值）→ 候选框列表
    3. 候选框扩展 10%
    4. 逐个裁剪 → RT-DETR 精检（高阈值）
    5. 局部坐标 → 全局坐标映射
    6. 绘制检测框 + FPS 叠加
    7. cv2.imshow 显示

用法
----
    ros2 launch camera_driver_transfer start_camera.launch.py
    ros2 run vision_basics ros2_hybrid

依赖
----
    · ROS2 Humble
    · ultralytics >= 8.2.0
    · cv_bridge, sensor_msgs
    · rtdetr-l.pt + yolov8s.pt（均在 vision_basics/model/）

参考版对比
----------
    参考版无 ROS2 混合节点（只有本地 HybridDetector 类）
    实践版新增，展示 ROS2 中双模型协作模式

作者   : Spark 机器人课程实践版
更新   : 2026-06-29 实测通过
================================================================================
"""

import time
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from ultralytics import YOLO, RTDETR

# ═══════════════════════════════════════════════════════════════════════════════
# 超参数
# ═══════════════════════════════════════════════════════════════════════════════
YOLO_CONF = 0.1        # 初筛阈值（低=高召回）
RTDETR_CONF = 0.5      # 精检阈值（高=高精度）
EXPAND_RATIO = 0.1     # 候选区扩展比例
CAMERA_TOPIC = '/camera/camera/color/image_raw'


class HybridNode(Node):
    """
    ROS2 混合检测节点
    
    内部维护两个 ultralytics 模型：
      self.yolo   → YOLOv8s（轻量，负责快速初筛）
      self.rtdetr → RT-DETR-L（高精度，负责候选区复核）
    """

    def __init__(self):
        super().__init__('hybrid_detector')

        # ── 加载双模型 ──
        # ROS2 包 share 目录下的模型路径
        from ament_index_python.packages import get_package_share_directory
        share_dir = get_package_share_directory('vision_basics')
        model_dir = f'{share_dir}/model'

        self.yolo = YOLO(f'{model_dir}/yolov8s.pt')
        self.rtdetr = RTDETR(f'{model_dir}/rtdetr-l.pt')

        self.get_logger().info(
            f'YOLOv8s (conf={YOLO_CONF}) + RT-DETR-L (conf={RTDETR_CONF}) 就绪'
        )

        # ── ROS2 通信 ──
        self.bridge = CvBridge()
        self.sub = self.create_subscription(
            Image, CAMERA_TOPIC, self.callback, 10)

        # ── 统计 ──
        self.fps = 0.0
        self.frame_count = 0

    def callback(self, msg: Image):
        """
        每帧回调：YOLO 初筛 → RT-DETR 精检 → 显示
        
        参数:
            msg: ROS2 Image 消息（BGR8 编码）
        """
        # ── 1. 解码图像 ──
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        h, w = frame.shape[:2]
        t_start = time.time()

        # ── 2. YOLO 初筛（高召回） ──
        yolo_results = self.yolo(frame, conf=YOLO_CONF, verbose=False)
        boxes = yolo_results[0].boxes
        if boxes is None or len(boxes) == 0:
            # 无可疑目标，直接显示原帧
            n_yolo = 0
            candidates = []
        else:
            n_yolo = len(boxes)
            candidates = boxes.xyxy.tolist()

        # ── 3. 区域扩展 ──
        expanded = []
        for box in candidates:
            x1, y1, x2, y2 = box
            bw, bh = x2 - x1, y2 - y1
            x1 = max(0, int(x1 - bw * EXPAND_RATIO))
            y1 = max(0, int(y1 - bh * EXPAND_RATIO))
            x2 = min(w, int(x2 + bw * EXPAND_RATIO))
            y2 = min(h, int(y2 + bh * EXPAND_RATIO))
            expanded.append([x1, y1, x2, y2])

        # ── 4. RT-DETR 精检（高精度）──
        detections = []
        for box in expanded:
            x1, y1, x2, y2 = box
            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            rt_results = self.rtdetr(crop, conf=RTDETR_CONF, verbose=False)
            for r_box in rt_results[0].boxes:
                rx1, ry1, rx2, ry2 = r_box.xyxy[0].tolist()
                cls_id = int(r_box.cls[0])
                cls_name = self.rtdetr.names[cls_id]
                conf_val = float(r_box.conf[0])
                detections.append({
                    'bbox': [x1 + rx1, y1 + ry1, x1 + rx2, y1 + ry2],
                    'class': cls_name,
                    'conf': conf_val,
                })

        # ── 5. FPS 计算（滑动平均）──
        elapsed = time.time() - t_start
        alpha = 0.3  # 平滑系数（越小越稳定）
        self.fps = alpha * (1.0 / elapsed) + (1 - alpha) * self.fps
        self.frame_count += 1

        # ── 6. 绘制 ──
        output = frame.copy()

        # 检测框（绿色）
        for d in detections:
            x1, y1, x2, y2 = [int(v) for v in d['bbox']]
            cv2.rectangle(output, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"{d['class']}: {d['conf']:.2f}"
            cv2.putText(output, label, (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

        # 状态栏（左上角）
        status_lines = [
            f'HYBRID: YOLO({n_yolo}) -> RTDETR({len(detections)})',
            f'FPS: {self.fps:.1f} | conf: {YOLO_CONF}/{RTDETR_CONF}',
        ]
        for i, text in enumerate(status_lines):
            y_pos = 25 + i * 22
            cv2.putText(output, text, (8, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)

        # ── 7. 显示 ──
        cv2.imshow('ROS2 Hybrid: YOLO -> RTDETR', output)
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC 退出
            self.get_logger().info('ESC pressed, shutting down')
            rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = HybridNode()
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
