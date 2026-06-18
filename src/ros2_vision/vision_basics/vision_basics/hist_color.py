#!/usr/bin/env python3
"""彩色直方图 — 分别计算 B/G/R 三通道直方图并叠加显示"""
import cv2, sys, numpy as np

img_path = sys.path[0] + "/../pictures/test_pattern.png"
img = cv2.imread(img_path)

# 三通道直方图
colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]  # B, G, R
labels = ['Blue', 'Green', 'Red']

hist_img = np.zeros((300, 256, 3), dtype=np.uint8)
for i, (color, label) in enumerate(zip(colors, labels)):
    hist = cv2.calcHist([img], [i], None, [256], [0, 256])
    hist_norm = hist / hist.max() * 280
    peak = int(np.argmax(hist))
    print(f"{label}: peak @ bin {peak} (count={int(hist.max())})")
    for x in range(256):
        cv2.line(hist_img, (x, 299), (x, 299 - int(hist_norm[x])), color, 1)

cv2.imshow("Original (BGR)", img)
cv2.imshow("Color Histogram (B/G/R)", hist_img)
cv2.waitKey(0)
cv2.destroyAllWindows()
