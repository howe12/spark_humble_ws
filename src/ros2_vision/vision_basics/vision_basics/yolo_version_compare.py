#!/usr/bin/env python3
"""
YOLO 版本横向对比

在同一张图上运行多个 YOLO 模型，对比：
  - 检测框数量
  - 推理时间（ms）
  - 模型大小（MB）
  - 参数数量（M）

模型优先从本地加载，本地没有则尝试自动下载。

用法：
    python3 yolo_version_compare.py               # 用 lena.png
    python3 yolo_version_compare.py image.jpg     # 自定义图片
"""

import os, sys, time
from ament_index_python.packages import get_package_share_directory
import cv2
import numpy as np
from ultralytics import YOLO

MODEL_DIR = os.path.join(get_package_share_directory('vision_basics'), 'model')
_base = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.join(_base, '..')

# ── 候选模型列表（名称, 展示名, 任务类型）──
CANDIDATES = [
    ('yolov8n.pt',       'YOLOv8n (2023)',       'detect'),
    ('yolov9c.pt',       'YOLOv9c (2024.2)',     'detect'),
    ('yolov10n.pt',      'YOLOv10n (2024.5)',    'detect'),
    ('yolo11n.pt',       'YOLO11n (2024.9)',     'detect'),
    ('yolo12n.pt',       'YOLO12n (2025.2)',     'detect'),
]


def get_model_path(name):
    """本地路径优先"""
    local = os.path.join(MODEL_DIR, name)
    return local if os.path.exists(local) else name


def truncate_model_info(model):
    """提取模型元信息"""
    try:
        import torch
        params_m = sum(p.numel() for p in model.model.parameters()) / 1e6
        flops_b = 0  # GFLOPs not reliably available
        return params_m, flops_b
    except Exception:
        return 0, 0


def main():
    img_path = sys.argv[1] if len(sys.argv) > 1 else f'{PROJ_DIR}/pictures/lena.png'
    if not os.path.exists(img_path):
        print(f'图片不存在: {img_path}')
        return

    img = cv2.imread(img_path)
    print(f'测试图片: {os.path.basename(img_path)} ({img.shape[1]}×{img.shape[0]})')
    print()
    print(f'{"模型":<28} {"状态":<8} {"框数":<6} {"时间ms":<8} {"大小MB":<8} {"参数M":<8}')
    print('-' * 72)

    results_data = []

    for fname, label, task in CANDIDATES:
        path = get_model_path(fname)
        status = '本地' if path != fname else '下载'

        try:
            model = YOLO(path)
            size_mb = os.path.getsize(path) / 1e6 if os.path.exists(path) else 0
            params_m, flops_b = truncate_model_info(model)

            # 预热一次
            _ = model(img, verbose=False)

            # 计时推理
            t0 = time.time()
            results = model(img, conf=0.25, verbose=False)
            elapsed = (time.time() - t0) * 1000

            r = results[0]
            n_boxes = len(r.boxes) if r.boxes is not None else 0
            annotated = r.plot()

            results_data.append((label, annotated, n_boxes, elapsed, size_mb, params_m))

            print(f'{label:<28} {status:<8} {n_boxes:<6} {elapsed:<8.1f} {size_mb:<8.1f} {params_m:<8.1f}')

        except Exception as e:
            short = str(e).split('\n')[0][:60]
            print(f'{label:<28} {"❌失败":<8} {"-":<6} {"-":<8} {"-":<8} {"-":<8}')
            print(f'  原因: {short}')

    # ── 并排对比图 ──
    if len(results_data) >= 1:
        panels = []
        for label, annotated, n, t, sz, p in results_data:
            h, w = annotated.shape[:2]
            # 叠加 label
            cv2.putText(annotated, f'{label} | {n}框 {t:.0f}ms',
                        (5, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            panels.append(annotated)

        # 拼成一行（最多 3 列）
        max_h = max(p.shape[0] for p in panels)
        rows = []
        for i in range(0, len(panels), 3):
            row = panels[i:i+3]
            # 统一高度
            row_resized = []
            for p in row:
                scale = max_h / p.shape[0]
                rw = int(p.shape[1] * scale)
                row_resized.append(cv2.resize(p, (rw, max_h)))
            rows.append(np.hstack(row_resized))

        comparison = np.vstack(rows)
        cv2.imshow('YOLO 版本对比 — 按任意键退出', comparison)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    print()
    print('窗口显示对比结果，按任意键关闭。')


if __name__ == '__main__':
    main()
