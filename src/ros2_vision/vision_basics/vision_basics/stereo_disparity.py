#!/usr/bin/env python3
"""03-5 多相机融合: 合成立体视觉 — SGBM 视差图演示

用单张图的水平平移生成"右视图"(模拟双目视差),
然后 SGBM 匹配 → 视差图 → 可视化。

公式: Z = f × B / d  (f=焦距, B=基线, d=视差)
"""

import cv2
import numpy as np
import os

# --- 1. 加载图像 ---
base = os.path.dirname(__file__)
img = cv2.imread(os.path.join(base, '..', 'pictures', 'test_pattern.png'))
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
h, w = gray.shape

# --- 2. 合成右视图（水平偏移模拟视差） ---
SHIFT = 8  # 水平偏移像素（模拟基线产生的视差）
right = np.zeros_like(gray)
right[:, SHIFT:] = gray[:, :w-SHIFT]

# --- 3. SGBM 立体匹配 ---
stereo = cv2.StereoSGBM_create(
    minDisparity=0,
    numDisparities=64,
    blockSize=5,
    P1=8 * 3 * 5 ** 2,
    P2=32 * 3 * 5 ** 2,
    disp12MaxDiff=1,
    uniquenessRatio=10,
    speckleWindowSize=100,
    speckleRange=32
)

disparity = stereo.compute(gray, right).astype(np.float32) / 16.0
disparity[disparity < 0] = 0

# --- 4. 可视化 ---
# 原始左右图并列
stereo_pair = np.hstack([gray, right])

# 视差图伪彩色
disp_color = cv2.applyColorMap(
    cv2.normalize(disparity, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U),
    cv2.COLORMAP_JET)

# 深度公式演示（设基线 B=0.05m, f=613px）
B, f = 0.05, 613.0
valid = disparity > 0
if np.any(valid):
    d_mean = disparity[valid].mean()
    Z = f * B / d_mean
    print(f"合成视差: shift={SHIFT}px")
    print(f"平均视差 d={d_mean:.1f}px → 深度 Z=f×B/d = {Z:.3f}m")
    print(f"(f={f:.0f}px, B={B:.3f}m)")
else:
    print("未检测到有效视差")

cv2.imshow('Left / Right (synthetic stereo)', stereo_pair)
cv2.imshow('SGBM Disparity (JET colormap)', disp_color)
print("\n左侧: 原图(左) + 合成右图  右侧: SGBM 视差图(暖色=近, 冷色=远)")
print("按任意键退出")
cv2.waitKey(0)
cv2.destroyAllWindows()
