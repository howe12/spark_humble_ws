#!/usr/bin/env python3
"""Shi-Tomasi 角点检测 — cv2.goodFeaturesToTrack，自动选出最优角点"""
import cv2, sys, numpy as np

img_path = sys.path[0] + "/../pictures/test_pattern.png"
img = cv2.imread(img_path)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Shi-Tomasi 检测
corners = cv2.goodFeaturesToTrack(
    gray, maxCorners=100, qualityLevel=0.01, minDistance=10
)

if corners is None:
    print("未检测到角点")
    exit()

corners = np.int0(corners)
corners_list = corners.reshape(-1, 2)

# 绘制
result = img.copy()
for x, y in corners_list:
    cv2.circle(result, (x, y), 5, (0, 0, 255), -1)  # 实心红点
    cv2.circle(result, (x, y), 8, (0, 255, 0), 1)   # 绿色外圈

print(f"Shi-Tomasi: maxCorners=100, qualityLevel=0.01, minDistance=10")
print(f"检测到 {len(corners_list)} 个角点")

cv2.imshow("Original", img)
cv2.imshow("Shi-Tomasi Corners", result)
cv2.waitKey(0)
cv2.destroyAllWindows()
