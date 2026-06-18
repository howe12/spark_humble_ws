#!/usr/bin/env python3
"""ORB 特征检测 — cv2.ORB_create + detectAndCompute（免费、实时）"""
import cv2, sys, numpy as np

img_path = sys.path[0] + "/../pictures/test_pattern.png"
img = cv2.imread(img_path)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# ORB 检测 + 描述
orb = cv2.ORB_create(nfeatures=500, scaleFactor=1.2, nlevels=8)
keypoints, descriptors = orb.detectAndCompute(gray, None)

# 绘制
result = cv2.drawKeypoints(img, keypoints, None, (0, 255, 0), 2)

print(f"ORB: {len(keypoints)} keypoints, descriptor shape={descriptors.shape}")
print(f"  descriptor dtype={descriptors.dtype} (binary, 每维 0-255)")

cv2.imshow("Original", img)
cv2.imshow("ORB Keypoints", result)
cv2.waitKey(0)
cv2.destroyAllWindows()
