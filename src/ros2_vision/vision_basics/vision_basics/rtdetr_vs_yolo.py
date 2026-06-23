#!/usr/bin/env python3
"""
RT-DETR vs YOLOv8 横向对比

同一张图上运行 RT-DETR 和 YOLOv8，对比：
  - 检测框数 + 类别分布
  - 推理时间（ms）
  - 模型大小（MB）
  - 并排标注图（左 RT-DETR / 右 YOLOv8）

用法：
    python3 rtdetr_vs_yolo.py               # lena.png
    python3 rtdetr_vs_yolo.py scene.jpg     # 自定义
"""

import os, sys, time
import cv2
import numpy as np
from ultralytics import YOLO

MODEL_DIR = os.path.expanduser('~/Music/spark_humble/src/spark_app/spark_yolov8/model')
PROJ_DIR = os.path.expanduser('~/Music/spark_humble/src/ros2_vision/vision_basics')


def get_model(name):
    local = os.path.join(MODEL_DIR, name)
    return local if os.path.exists(local) else name


def run_one(model_path, label, img):
    t0 = time.time()
    try:
        m = YOLO(model_path)
        # 预热
        _ = m(img, verbose=False)
        t1 = time.time()
        r = m(img, conf=0.25, verbose=False)
        t2 = time.time()
    except Exception as e:
        return None, str(e)[:60], 0, 0

    n = len(r[0].boxes) if r[0].boxes is not None else 0
    annotated = r[0].plot()
    size_mb = os.path.getsize(model_path) / 1e6 if os.path.exists(model_path) else 0
    infer_ms = (t2 - t1) * 1000
    return annotated, f'{n} 框', size_mb, infer_ms


def main():
    img_path = sys.argv[1] if len(sys.argv) > 1 else f'{PROJ_DIR}/pictures/lena.png'
    img = cv2.imread(img_path)
    print(f'测试图片: {os.path.basename(img_path)} ({img.shape[1]}×{img.shape[0]})\n')

    pairs = [
        ('rtdetr-l.pt',  'RT-DETR-L (Transformer)'),
        ('yolov8m.pt',   'YOLOv8m (CNN)'),
    ]

    panels = []

    for fname, label in pairs:
        path = get_model(fname)
        source = '本地' if path != fname else '下载'
        print(f'{label} [{source}]: {fname}', end=' ')
        annotated, info, size_mb, ms = run_one(path, label, img)
        if annotated is None:
            print(f'❌ {info}')
            continue
        print(f'→ {info}, {ms:.0f}ms, {size_mb:.1f}MB')

        # 叠加标注
        cv2.putText(annotated, f'{label} | {info} | {ms:.0f}ms | {size_mb:.1f}MB',
                    (5, annotated.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        panels.append(annotated)

    if len(panels) >= 2:
        # 统一高度后并排
        h = max(p.shape[0] for p in panels)
        resized = [cv2.resize(p, (int(p.shape[1] * h / p.shape[0]), h)) for p in panels]
        comparison = np.hstack(resized)
        cv2.imshow('RT-DETR (左) vs YOLOv8 (右) — 按任意键退出', comparison)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
