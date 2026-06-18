#!/usr/bin/env python3
"""03-3 物体识别抓取: HSV 颜色检测

对 test_pattern.png 检测红/蓝/黄三种颜色方块:
  BGR→HSV → cv2.inRange → 形态学 → findContours → minAreaRect → 画框
打印每个检测到的物体的像素中心 + 旋转角度。
"""

import cv2
import numpy as np
import os

# --- 1. 加载测试图 ---
base = os.path.dirname(__file__)
img = cv2.imread(os.path.join(base, '..', 'pictures', 'test_pattern.png'))
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

# --- 2. 颜色 HSV 阈值（参考值，需根据实际环境标定） ---
COLORS = {
    'Red':    ([0, 100, 100],   [10, 255, 255]),    # 红色 H 低段
    'Red2':   ([160, 100, 100], [180, 255, 255]),   # 红色 H 高段（环绕）
    'Blue':   ([100, 100, 100], [130, 255, 255]),   # 蓝色
    'Yellow': ([20, 100, 100],  [35, 255, 255]),    # 黄色
    'Green':  ([40, 100, 100],  [80, 255, 255]),    # 绿色
}

result = img.copy()
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

for name, (lower, upper) in COLORS.items():
    low = np.array(lower)
    high = np.array(upper)
    mask = cv2.inRange(hsv, low, high)

    # 合并红色的两个 H 段
    if name == 'Red2':
        continue  # 下面统一处理

    if name == 'Red':
        # 红色需要合并 [0,10] 和 [160,180] 两段
        mask2 = cv2.inRange(hsv, np.array([160, 100, 100]), np.array([180, 255, 255]))
        mask = cv2.bitwise_or(mask, mask2)
        name = 'Red'

    if name in ('Red2',):
        continue

    # 形态学去噪
    mask = cv2.erode(mask, kernel, iterations=1)
    mask = cv2.dilate(mask, kernel, iterations=1)

    # 查找轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 200:  # 过滤小噪点
            continue

        min_rect = cv2.minAreaRect(cnt)
        center, size, angle = min_rect

        # 画旋转矩形
        box = cv2.boxPoints(min_rect)
        box = np.int32(box)
        cv2.drawContours(result, [box], 0, (0, 255, 0), 2)
        cv2.circle(result, (int(center[0]), int(center[1])), 4, (0, 0, 255), -1)

        print(f'{name}: center=({center[0]:.0f}, {center[1]:.0f}) '
              f'size=({size[0]:.0f}, {size[1]:.0f}) angle={angle:.1f}° area={area:.0f}')

cv2.imshow('HSV Color Detection', result)
print("按任意键退出")
cv2.waitKey(0)
cv2.destroyAllWindows()
