#!/usr/bin/env python3
"""
SAM 交互式点提示分割

用鼠标点击目标 → SAM 自动分割该目标。

操作：
    左键点击 = 前景点（"我要这个"）
    右键点击 = 背景点（"不要这个"）
    按 r 键  = 运行 SAM 推理
    按 c 键  = 清除所有点
    按 s 键  = 保存当前 mask
    按 q 键  = 退出

这是 SAM 最独特的卖点：零样本交互式分割——点哪切哪。

用法：
    python3 sam_prompt.py              # lena.png
    python3 sam_prompt.py image.jpg    # 自定义图片

模型：sam_b.pt（首次运行自动下载，约 350MB）
"""

import os, sys
from ament_index_python.packages import get_package_share_directory
import cv2
import numpy as np
from ultralytics import SAM

MODEL_DIR = os.path.join(get_package_share_directory('vision_basics'), 'model')
_base = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.join(_base, '..')

# 颜色
GREEN = (0, 255, 0)      # 前景点
RED = (0, 0, 255)        # 背景点
YELLOW = (0, 255, 255)   # mask 叠加


def get_model(name):
    local = os.path.join(MODEL_DIR, name)
    return local if os.path.exists(local) else name


def mouse_cb(event, x, y, flags, param):
    """收集点击点"""
    points, labels = param
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append([x, y])
        labels.append(1)  # 前景
        print(f'  前景点: ({x}, {y})')
    elif event == cv2.EVENT_RBUTTONDOWN:
        points.append([x, y])
        labels.append(0)  # 背景
        print(f'  背景点: ({x}, {y})')


def main():
    model_path = get_model('sam_b.pt')
    print(f'模型: {model_path}')
    m = SAM(model_path)

    img_path = sys.argv[1] if len(sys.argv) > 1 else f'{PROJ_DIR}/pictures/lena.png'
    img = cv2.imread(img_path)
    print(f'图片: {os.path.basename(img_path)} ({img.shape[1]}×{img.shape[0]})')
    print('\n操作: 左键=前景  右键=背景  r=推理  c=清除  s=保存  q=退出\n')

    points = []   # [[x,y], ...]
    labels = []   # [1/0, ...]

    cv2.namedWindow('SAM Point Prompt')
    cv2.setMouseCallback('SAM Point Prompt', mouse_cb, (points, labels))

    display = img.copy()
    mask_overlay = None

    while True:
        display = img.copy()

        # 绘制已选点
        for (px, py), lb in zip(points, labels):
            color = GREEN if lb == 1 else RED
            cv2.circle(display, (int(px), int(py)), 5, color, -1)
            cv2.circle(display, (int(px), int(py)), 7, color, 2)

        # 叠加 mask
        if mask_overlay is not None:
            display[mask_overlay] = (display[mask_overlay] * 0.5 + np.array(YELLOW) * 0.5).astype(np.uint8)

        cv2.imshow('SAM Point Prompt', display)
        key = cv2.waitKey(20) & 0xFF

        if key == ord('q'):
            break
        elif key == ord('c'):
            points.clear()
            labels.clear()
            mask_overlay = None
            print('已清除所有点')
        elif key == ord('r'):
            if not points:
                print('请先点选至少一个点')
                continue
            print(f'推理中... ({len(points)} 个提示点)')
            results = m(img, points=points, labels=labels, verbose=False)
            if results[0].masks is not None:
                m_data = results[0].masks.data.cpu().numpy()
                # 取置信度最高的 mask
                best_idx = np.argmax(results[0].masks.conf.cpu().numpy()
                                     if hasattr(results[0].masks, 'conf')
                                     else [1])
                mask_overlay = m_data[best_idx] > 0.5
                print(f'  完成! mask 面积: {mask_overlay.sum()}px')
            else:
                print('  未生成 mask，尝试加更多点')
        elif key == ord('s') and mask_overlay is not None:
            cv2.imwrite('/tmp/sam_mask.png', (mask_overlay * 255).astype(np.uint8))
            print('已保存 /tmp/sam_mask.png')

    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
