#!/usr/bin/env python3
"""灰度直方图 — cv2.calcHist 计算灰度图像素分布，绘制柱状图"""
import cv2, sys, numpy as np

img_path = sys.path[0] + "/../pictures/test_pattern.png"
gray = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

# 计算直方图
hist = cv2.calcHist([gray], [0], None, [256], [0, 256])

# 终端统计
print(f"图像尺寸: {gray.shape}")
print(f"平均亮度: {gray.mean():.1f}  最暗: {gray.min()}  最亮: {gray.max()}")
print(f"峰值 bin: {np.argmax(hist)} (count={int(hist.max())})")

# 用 OpenCV 绘制直方图（不需要 matplotlib）
hist_img = np.zeros((300, 256, 3), dtype=np.uint8)
hist_norm = hist / hist.max() * 280  # 归一化到 280px 高
for i in range(256):
    cv2.line(hist_img, (i, 299), (i, 299 - int(hist_norm[i])), (0, 255, 0), 1)

cv2.imshow("Original (Gray)", gray)
cv2.imshow("Histogram", hist_img)
cv2.waitKey(0)
cv2.destroyAllWindows()
