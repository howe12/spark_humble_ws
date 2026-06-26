#!/usr/bin/env python3
"""04-2 YOLO实例分割: 本地图片实例分割

用 YOLOv8n-seg 对 lena.png + two_blue_cube.png 做实例分割,
打印每个实例: 类别/置信度/边界框/遮罩点数。

与 04-1 目标检测的唯一区别: 模型名加 -seg, 输出含 result.masks。
"""

import sys
import os
import cv2
from ament_index_python.packages import get_package_share_directory
from ultralytics import YOLO

# 模型路径 — 需要先下载: yolo predict model=yolov8n-seg.pt (参考版第4章)
MODEL_NAME = 'yolov8n-seg.pt'

local_model = os.path.join(
    get_package_share_directory('vision_basics'), 'model', MODEL_NAME)
if os.path.exists(local_model):
    model_path = local_model
else:
    model_path = MODEL_NAME  # ultralytics 自动下载

print(f"模型: {model_path}")
model = YOLO(model_path)

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
    masks = r.masks
    names = r.names

    if boxes is None or len(boxes) == 0:
        print("  未检测到目标")
        annotated = r.plot()
        cv2.imshow(f'Seg {i+1}', annotated)
        cv2.waitKey(0)
        continue

    for j in range(len(boxes)):
        cls_id = int(boxes.cls[j])
        conf = float(boxes.conf[j])
        xywh = boxes.xywh[j]
        name = names.get(cls_id, f'id:{cls_id}')

        # 遮罩点数
        mask_pts = len(masks.xy[j]) if masks and j < len(masks.xy) else 0

        print(f"  {name:<12} conf={conf:.2f} "
              f"center=({int(xywh[0])},{int(xywh[1])}) "
              f"mask_pts={mask_pts}")

    annotated = r.plot()
    cv2.imshow(f'Instance Seg {i+1}', annotated)
    cv2.waitKey(0)

cv2.destroyAllWindows()
