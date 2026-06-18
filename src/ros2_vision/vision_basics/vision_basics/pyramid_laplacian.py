#!/usr/bin/env python3
"""拉普拉斯金字塔 — 每层 = 高斯层 - 上层上采样的结果，提取高频细节"""
import cv2, sys, numpy as np

img_path = sys.path[0] + "/../pictures/test_pattern.png"
img = cv2.imread(img_path)

# 1. 构建高斯金字塔
gp = [img]
for _ in range(3):
    gp.append(cv2.pyrDown(gp[-1]))

# 2. 构建拉普拉斯金字塔
lp = []
for i in range(3):
    # 上层上采样并尺寸对齐
    expanded = cv2.pyrUp(gp[i+1])
    h, w = gp[i].shape[:2]
    expanded = cv2.resize(expanded, (w, h))
    # 拉普拉斯 = 本层 - 上层上采样（高频细节）
    laplacian = cv2.subtract(gp[i], expanded)
    lp.append(laplacian)

# 终端统计
for i, (g, l) in enumerate(zip(gp[:-1], lp)):
    print(f"Layer {i}: Gaussian {g.shape[1]}×{g.shape[0]}  →  Laplacian sigma={l.std():.1f}")

# 拼接拉普拉斯金字塔
h = lp[0].shape[0]
canvas = lp[0].copy()
for i, layer in enumerate(lp[1:], 1):
    scale = h / layer.shape[0]
    big = cv2.resize(layer, (int(layer.shape[1]*scale), h))
    cv2.putText(big, f"L{i}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    canvas = np.hstack([canvas, big])

cv2.imshow("Original", img)
cv2.imshow("Laplacian Pyramid (high-frequency details)", canvas)
cv2.waitKey(0)
cv2.destroyAllWindows()
