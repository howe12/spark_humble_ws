#!/usr/bin/env python3
"""Harris vs Shi-Tomasi 同图对比 — 左右分屏，直观比较两种算法"""
import cv2, sys, numpy as np

img_path = sys.path[0] + "/../pictures/test_pattern.png"
img = cv2.imread(img_path)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
gray_f = np.float32(gray)

# === Harris ===
dst = cv2.cornerHarris(gray_f, blockSize=2, ksize=3, k=0.04)
dst = cv2.dilate(dst, None)
harris_result = img.copy()
harris_result[dst > 0.01 * dst.max()] = [0, 0, 255]
h_corners = np.argwhere(dst > 0.01 * dst.max())
for x, y in h_corners[:, [1, 0]]:
    cv2.circle(harris_result, (x, y), 4, (0, 255, 0), 1)
print(f"Harris: {len(h_corners)} corners (blockSize=2, k=0.04)")

# === Shi-Tomasi ===
st_corners = cv2.goodFeaturesToTrack(gray, maxCorners=len(h_corners),
                                       qualityLevel=0.01, minDistance=10)
st_result = img.copy()
if st_corners is not None:
    st_corners = np.int0(st_corners).reshape(-1, 2)
    for x, y in st_corners:
        cv2.circle(st_result, (x, y), 5, (0, 0, 255), -1)
        cv2.circle(st_result, (x, y), 8, (0, 255, 0), 1)
    print(f"Shi-Tomasi: {len(st_corners)} corners (same count)")

# 左右拼接
side = np.hstack([harris_result, st_result])
h, w = side.shape[:2]
cv2.putText(side, "Harris", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
cv2.putText(side, "Shi-Tomasi", (w//2 + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

cv2.imshow("Harris (left) vs Shi-Tomasi (right)", side)
cv2.waitKey(0)
cv2.destroyAllWindows()
