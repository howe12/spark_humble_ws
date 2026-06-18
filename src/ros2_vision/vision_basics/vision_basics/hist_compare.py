#!/usr/bin/env python3
"""直方图对比 — cv2.compareHist 计算两张图直方图相似度（4种方法）"""
import cv2, sys, numpy as np

img_path = sys.path[0] + "/../pictures/test_pattern.png"
gray = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

# 生成对比图：原图 vs 均衡化图 vs 亮50%
equ = cv2.equalizeHist(gray)
bright = cv2.convertScaleAbs(gray, alpha=1.0, beta=50)

hist_orig = cv2.calcHist([gray], [0], None, [256], [0, 256])
hist_equ = cv2.calcHist([equ], [0], None, [256], [0, 256])
hist_bright = cv2.calcHist([bright], [0], None, [256], [0, 256])

# 归一化
for h in [hist_orig, hist_equ, hist_bright]:
    cv2.normalize(h, h, 0, 1, cv2.NORM_MINMAX)

methods = [
    ('CORREL', cv2.HISTCMP_CORREL, '越接近 1 越相似'),
    ('CHISQR', cv2.HISTCMP_CHISQR, '越接近 0 越相似'),
    ('INTERSECT', cv2.HISTCMP_INTERSECT, '越大越相似'),
    ('BHATTACHARYYA', cv2.HISTCMP_BHATTACHARYYA, '越接近 0 越相似'),
]

print(f"{'Method':<15} {'原图 vs 均衡化':<20} {'原图 vs 亮50%':<20} {'含义'}")
print("-" * 80)
for name, method, desc in methods:
    d1 = cv2.compareHist(hist_orig, hist_equ, method)
    d2 = cv2.compareHist(hist_orig, hist_bright, method)
    print(f"{name:<15} {d1:<20.4f} {d2:<20.4f} {desc}")

cv2.imshow("Original", gray)
cv2.imshow("Equalized", equ)
cv2.imshow("Bright+50", bright)
cv2.waitKey(0)
cv2.destroyAllWindows()
