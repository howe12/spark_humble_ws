#!/usr/bin/env python3
"""Harris 角点检测 — cv2.cornerHarris + dilate + 阈值标记"""
import cv2, sys, numpy as np

img_path = sys.path[0] + "/../pictures/test_pattern.png"
img = cv2.imread(img_path)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
gray_f = np.float32(gray)

# Harris 角点检测
dst = cv2.cornerHarris(gray_f, blockSize=2, ksize=3, k=0.04)

# 膨胀角点响应（便于可视化）
dst = cv2.dilate(dst, None)

# 阈值化：响应值 > 1% 最大值的像素标红
result = img.copy()
result[dst > 0.01 * dst.max()] = [0, 0, 255]

# 提取角点坐标并画圈
corners = np.argwhere(dst > 0.01 * dst.max())
corners_xy = corners[:, [1, 0]]  # (y,x) → (x,y)
for x, y in corners_xy:
    cv2.circle(result, (x, y), 4, (0, 255, 0), 1)

print(f"blockSize=2, ksize=3, k=0.04")
print(f"检测到 {len(corners_xy)} 个角点")
print(f"响应范围: [{dst.min():.6f}, {dst.max():.6f}]")

cv2.imshow("Original", img)
cv2.imshow("Harris Corners (red=corner, green=circle)", result)
cv2.waitKey(0)
cv2.destroyAllWindows()
