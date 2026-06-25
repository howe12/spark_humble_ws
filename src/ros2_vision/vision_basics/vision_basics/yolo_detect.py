#!/usr/bin/env python3
"""04-1 YOLO: 本地图片目标检测

用 YOLOv8n 检测 lena.png + two_blue_cube.png,
打印每个检测结果: 类别/置信度/边界框。

参考版使用 fruit_1.jpg 等外网图片，
实践版用本地已有图片演示核心 API。
"""

import sys
import os
import cv2
from ultralytics import YOLO
from ament_index_python.packages import get_package_share_directory

# 模型路径（从 spark_yolov8 包中定位）
MODEL = os.path.join(
    get_package_share_directory('spark_yolov8'), 'model', 'yolov8n.pt')

# 加载模型
model = YOLO(MODEL)
print(f"模型: {MODEL}")

# 检测图片
base = os.path.dirname(__file__)
pics = os.path.join(base, '..', 'pictures')
images = [
    os.path.join(pics, 'lena.png'),
    os.path.join(pics, 'two_blue_cube.png'),
]

results = model(images, conf=0.25)

for i, r in enumerate(results):
    print(f"\n{'='*50}")
    print(f"图片 {i+1}: {os.path.basename(r.path)}")

    boxes = r.boxes
    if boxes is None or len(boxes) == 0:
        print("  未检测到目标")
        continue

    names = r.names  # {0: 'person', 1: 'bicycle', ...}

    for j in range(len(boxes)):
        cls_id = int(boxes.cls[j])
        conf = float(boxes.conf[j])
        xywh = boxes.xywh[j]  # (cx, cy, w, h)
        cx, cy, w, h = int(xywh[0]), int(xywh[1]), int(xywh[2]), int(xywh[3])
        name = names.get(cls_id, f'id:{cls_id}')

        print(f"  {name:<12} conf={conf:.2f} "
              f"center=({cx},{cy}) size=({w}x{h})")

    # 显示
    annotated = r.plot()
    cv2.imshow(f'Image {i+1}', annotated)
    cv2.waitKey(0)

cv2.destroyAllWindows()
