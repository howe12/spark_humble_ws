#!/usr/bin/env python3
"""
YOLO + SAM 联合分割管线

YOLO 先检测目标框 → SAM 用检测框做 prompt 精确分割每个目标。

这是机器人视觉的经典组合：
  YOLO = "有什么？在哪？（快）"
  SAM  = "精确轮廓是什么？（准）"

用法：
    python3 yolo_sam_combo.py               # lena.png
    python3 yolo_sam_combo.py image.jpg     # 自定义

模型：yolov8n.pt + sam_b.pt（首次运行自动下载）
"""

import os, sys
import cv2
import numpy as np
from ultralytics import YOLO, SAM

MODEL_DIR = os.path.expanduser('~/Music/spark_humble/src/spark_app/spark_yolov8/model')
PROJ_DIR = os.path.expanduser('~/Music/spark_humble/src/ros2_vision/vision_basics')


def get_model(name):
    local = os.path.join(MODEL_DIR, name)
    return local if os.path.exists(local) else name


def main():
    # ── 加载模型 ──
    yolo_path = get_model('yolov8n.pt')
    sam_path = get_model('sam_b.pt')

    print(f'YOLO: {yolo_path}')
    yolo = YOLO(yolo_path)
    print(f'SAM:  {sam_path}')
    sam = SAM(sam_path)

    img_path = sys.argv[1] if len(sys.argv) > 1 else f'{PROJ_DIR}/pictures/lena.png'
    img = cv2.imread(img_path)
    print(f'\n图片: {os.path.basename(img_path)} ({img.shape[1]}×{img.shape[0]})')

    # ── 步骤 1: YOLO 检测 ──
    yolo_results = yolo(img, conf=0.3, verbose=False)
    boxes = yolo_results[0].boxes

    if boxes is None or len(boxes) == 0:
        print('YOLO 未检测到目标，直接用 SAM 自动分割')
        sam_results = sam(img, verbose=False)
        annotated = sam_results[0].plot()
    else:
        xyxy = boxes.xyxy.cpu().numpy()  # (N, 4)
        print(f'YOLO 检测: {len(xyxy)} 个目标')

        # ── 步骤 2: SAM 用 YOLO 框做 prompt ──
        sam_results = sam(img, bboxes=xyxy, verbose=False)

        # ── 步骤 3: 可视化 ──
        annotated = yolo_results[0].plot()  # 先画 YOLO 框

        if sam_results[0].masks is not None:
            masks = sam_results[0].masks.data.cpu().numpy()  # (N, H, W)
            print(f'SAM 分割: {len(masks)} 个 mask')

            # 半透明叠加每个 mask（不同颜色）
            overlay = annotated.copy()
            for i, mask in enumerate(masks):
                color = np.random.randint(50, 255, 3).tolist()
                mask_bool = mask > 0.5
                overlay[mask_bool] = (
                    overlay[mask_bool] * 0.3 + np.array(color) * 0.7
                ).astype(np.uint8)
            annotated = cv2.addWeighted(annotated, 0.4, overlay, 0.6, 0)

    # ── 并排对比 ──
    yolo_only = yolo_results[0].plot()
    comparison = np.hstack([yolo_only, annotated])
    cv2.putText(comparison, 'YOLO only', (5, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(comparison, 'YOLO + SAM', (img.shape[1] + 5, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.imshow('YOLO (左) vs YOLO+SAM (右) — 按任意键退出', comparison)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
