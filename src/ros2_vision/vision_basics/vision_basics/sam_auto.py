#!/usr/bin/env python3
"""
SAM 自动分割一切

加载 SAM 模型，自动分割图片中的所有目标，用随机颜色显示。

SAM (Segment Anything Model) 是 Meta 的基础分割模型，
不需要任何 prompt — 自动找出图中所有可分割区域。

用法：
    python3 sam_auto.py                 # lena.png
    python3 sam_auto.py image.jpg       # 自定义图片

模型：sam_b.pt（首次运行自动下载，约 350MB）
"""

import os, sys
from ament_index_python.packages import get_package_share_directory
import cv2
import numpy as np
from ultralytics import SAM

# 模型路径（从 spark_yolov8 包中定位）
MODEL_DIR = os.path.join(get_package_share_directory('spark_yolov8'), 'model')
PROJ_DIR = os.path.expanduser('~/Music/spark_humble/src/ros2_vision/vision_basics')


def get_model(name):
    local = os.path.join(MODEL_DIR, name)
    return local if os.path.exists(local) else name


def main():
    model_path = get_model('sam_b.pt')
    print(f'模型: {model_path}')
    m = SAM(model_path)
    print(f'任务: {m.task}')

    img_path = sys.argv[1] if len(sys.argv) > 1 else f'{PROJ_DIR}/pictures/lena.png'
    img = cv2.imread(img_path)
    print(f'图片: {os.path.basename(img_path)} ({img.shape[1]}×{img.shape[0]})')

    # SAM 自动分割所有目标
    results = m(img, verbose=False)

    if results[0].masks is None:
        print('未检测到任何分割区域')
        return

    masks = results[0].masks.data.cpu().numpy()  # (N, H, W) float
    print(f'自动分割: {len(masks)} 个区域')

    # 用随机颜色叠加所有 mask
    overlay = img.copy()
    for i, mask in enumerate(masks):
        color = np.random.randint(50, 255, 3).tolist()
        mask_bool = mask > 0.5
        overlay[mask_bool] = (overlay[mask_bool] * 0.4 + np.array(color) * 0.6).astype(np.uint8)

    result = np.hstack([img, overlay])
    cv2.putText(result, 'Original', (5, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(result, f'SAM: {len(masks)} regions', (img.shape[1] + 5, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.imshow('SAM Auto Segment Everything — 按任意键退出', result)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
