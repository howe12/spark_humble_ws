#!/usr/bin/env python3
"""角点匹配配准 — Shi-Tomasi + LK光流 + findHomography，自生成旋转图配准"""
import cv2, sys, numpy as np

img_path = sys.path[0] + "/../pictures/test_pattern.png"
img1 = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

# 自生成"第二张图"：旋转 15 度模拟视角变化
h, w = img1.shape
M = cv2.getRotationMatrix2D((w/2, h/2), 15, 1.0)
img2_orig = cv2.warpAffine(img1, M, (w, h))

# 提取 Shi-Tomasi 角点
corners1 = cv2.goodFeaturesToTrack(img1, maxCorners=200, qualityLevel=0.01, minDistance=15)
if corners1 is None:
    print("No corners in img1"); exit()

# LK 光流跟踪：从 img1 的角点跟踪到 img2
corners2, status, err = cv2.calcOpticalFlowPyrLK(
    img1, img2_orig, corners1, None,
    winSize=(21, 21), maxLevel=3,
    criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01)
)

# 筛选成功跟踪的点
good1 = corners1[status == 1]
good2 = corners2[status == 1]
print(f"Shi-Tomasi 角点: {len(corners1)}  →  LK 跟踪成功: {len(good1)}")

# 计算单应性矩阵 + 校正
if len(good1) >= 4:
    H, mask = cv2.findHomography(good2.reshape(-1, 1, 2),
                                  good1.reshape(-1, 1, 2),
                                  cv2.RANSAC, 5.0)
    aligned = cv2.warpPerspective(img2_orig, H, (w, h))
    print(f"单应性矩阵 H:\n{H}")
    print(f"配准完成")
else:
    print("跟踪点不足，无法配准")
    aligned = img2_orig

# 可视化匹配线
vis = cv2.cvtColor(img1, cv2.COLOR_GRAY2BGR)
img2_color = cv2.cvtColor(img2_orig, cv2.COLOR_GRAY2BGR)
match_vis = np.hstack([vis, img2_color])
for (x1, y1), (x2, y2) in zip(good1[:30].reshape(-1, 2), good2[:30].reshape(-1, 2)):
    cv2.line(match_vis, (int(x1), int(y1)), (int(x2)+w, int(y2)),
             (0, 255, 0), 1)
    cv2.circle(match_vis, (int(x1), int(y1)), 3, (0, 0, 255), -1)

cv2.imshow("Corner Matches (green lines = tracked)", match_vis)
cv2.imshow("Original", img1)
cv2.imshow("Rotated 15deg", img2_orig)
cv2.imshow("Aligned (corrected)", aligned)
cv2.waitKey(0)
cv2.destroyAllWindows()
