#!/usr/bin/env python3
"""高斯金字塔 — cv2.pyrDown/pyrUp 构建图像金字塔，逐层缩小"""
import cv2, sys, numpy as np

img_path = sys.path[0] + "/../pictures/test_pattern.png"
img = cv2.imread(img_path)

# 构建 4 层金字塔
layers = [img]
for i in range(3):
    layers.append(cv2.pyrDown(layers[-1]))

# 终端打印各层信息
for i, layer in enumerate(layers):
    print(f"Layer {i}: {layer.shape[1]}×{layer.shape[0]}  ({layer.shape[1]*layer.shape[0]/1000:.0f}k px)")

# 拼接显示：把小图放大到同高度方便对比
h = layers[0].shape[0]
canvas = layers[0].copy()
for i, layer in enumerate(layers[1:], 1):
    # 放大到 Layer 0 的高度
    scale = h / layer.shape[0]
    big = cv2.resize(layer, (int(layer.shape[1]*scale), h))
    cv2.putText(big, f"L{i}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    canvas = np.hstack([canvas, big])

cv2.imshow("Gaussian Pyramid (L0→L3)", canvas)
cv2.waitKey(0)
cv2.destroyAllWindows()
