#!/usr/bin/env python3
"""
RT-DETR 实时 Transformer 目标检测

RT-DETR 是百度提出的实时端到端 Transformer 检测器，直接通过 YOLO() 加载。
与 YOLOv8 的 API 完全一致——唯一区别是模型名。

用法：
    python3 rtdetr_detect.py              # 用 lena.png
    python3 rtdetr_detect.py image.jpg    # 自定义图片

模型：rtdetr-l.pt（首次运行自动下载，约 128MB）
"""

import os, sys, time
from ament_index_python.packages import get_package_share_directory
import cv2
from ultralytics import YOLO

MODEL_DIR = os.path.join(get_package_share_directory('vision_basics'), 'model')
_base = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.join(_base, '..')


def get_model(name):
    local = os.path.join(MODEL_DIR, name)
    return local if os.path.exists(local) else name


def main():
    # MODEL 可与 YOLO 互换：YOLO('rtdetr-l.pt') 和 RTDETR('rtdetr-l.pt') 等效
    model_path = get_model('rtdetr-l.pt')
    print(f'模型: {model_path}')
    model = YOLO(model_path)
    print(f'任务: {model.task}')

    img_path = sys.argv[1] if len(sys.argv) > 1 else f'{PROJ_DIR}/pictures/lena.png'
    img = cv2.imread(img_path)
    print(f'图片: {os.path.basename(img_path)} ({img.shape[1]}×{img.shape[0]})')

    # 推理
    t0 = time.time()
    results = model(img, conf=0.25, verbose=False)
    ms = (time.time() - t0) * 1000

    r = results[0]
    n = len(r.boxes) if r.boxes is not None else 0
    print(f'检测: {n} 个目标, 推理 {ms:.0f}ms')

    annotated = r.plot()
    cv2.imshow('RT-DETR — 按任意键退出', annotated)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
