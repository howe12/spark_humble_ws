#!/usr/bin/env python3
"""FAST 角点检测 — cv2.FastFeatureDetector_create（极速，只检测不描述）"""
import cv2, sys

img_path = sys.path[0] + "/../pictures/test_pattern.png"
img = cv2.imread(img_path)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# FAST 检测（只检测角点，不计算描述子）
fast = cv2.FastFeatureDetector_create(threshold=20)
keypoints = fast.detect(gray, None)

result = cv2.drawKeypoints(img, keypoints, None, (0, 0, 255))

print(f"FAST: {len(keypoints)} keypoints (threshold=20)")
print(f"  FAST 只检测角点位置，不生成描述子——不能直接匹配")

cv2.imshow("Original", img)
cv2.imshow("FAST Keypoints (no descriptor)", result)
cv2.waitKey(0)
cv2.destroyAllWindows()
