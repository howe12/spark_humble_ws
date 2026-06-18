#!/usr/bin/env python3
"""SIFT 特征检测 — cv2.SIFT_create + detectAndCompute + drawKeypoints"""
import cv2, sys, numpy as np

img_path = sys.path[0] + "/../pictures/test_pattern.png"
img = cv2.imread(img_path)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# SIFT 检测 + 描述
sift = cv2.SIFT_create(nfeatures=500)
keypoints, descriptors = sift.detectAndCompute(gray, None)

# 绘制（带方向和尺度的丰富显示）
result = cv2.drawKeypoints(img, keypoints, None,
                           flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

print(f"SIFT: {len(keypoints)} keypoints, descriptor shape={descriptors.shape}")
print(f"  第一个关键点: pt=({keypoints[0].pt[0]:.1f},{keypoints[0].pt[1]:.1f}) "
      f"size={keypoints[0].size:.1f} angle={keypoints[0].angle:.1f}")

cv2.imshow("Original", img)
cv2.imshow("SIFT Keypoints (rich: direction+scale)", result)
cv2.waitKey(0)
cv2.destroyAllWindows()
