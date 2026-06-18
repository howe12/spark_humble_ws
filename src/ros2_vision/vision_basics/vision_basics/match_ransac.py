#!/usr/bin/env python3
"""02-10 特征匹配: RANSAC 单应性过滤 — inliers vs outliers

完整流程:
  ORB → BFMatcher(NORM_HAMMING) → knnMatch(k=2) → 比率测试
  → findHomography(RANSAC) → 内点 vs 外点对比可视化

关键: findHomography 返回 mask，mask[i]==1 表示 inlier。
"""

import cv2
import numpy as np
import os

# --- 1. 生成场景对 ---
base = os.path.dirname(__file__)
scene = cv2.imread(os.path.join(base, '..', 'pictures', 'test_pattern.png'))
h, w = scene.shape[:2]

# 透视变换产生明显视角差异
src_pts = np.float32([[0, 0], [w - 1, 0], [0, h - 1], [w - 1, h - 1]])
dst_pts = np.float32([[40, 30], [w - 50, 10], [20, h - 40], [w - 30, h - 20]])
P = cv2.getPerspectiveTransform(src_pts, dst_pts)
query = cv2.warpPerspective(scene, P, (w, h))

# --- 2. ORB → 匹配 → 比率测试 ---
orb = cv2.ORB_create(1000)
kp1, des1 = orb.detectAndCompute(query, None)
kp2, des2 = orb.detectAndCompute(scene, None)

bf = cv2.BFMatcher(cv2.NORM_HAMMING)
raw = bf.knnMatch(des1, des2, k=2)
good = [m for m, n in raw if m.distance < 0.75 * n.distance]
print(f"比率测试后: {len(good)} matches")

# --- 3. findHomography + RANSAC ---
src = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
dst = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)

inliers = [good[i] for i in range(len(good)) if mask[i]]
outliers = [good[i] for i in range(len(good)) if not mask[i]]
print(f"RANSAC: {len(inliers)} inliers | {len(outliers)} outliers | H:\n{H}")

# --- 4. 并排对比: 无 RANSAC 全匹配 vs 仅内点 ---
before = cv2.drawMatches(
    query, kp1, scene, kp2, good[:60], None,
    flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
)
after = cv2.drawMatches(
    query, kp1, scene, kp2, inliers, None,
    flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
)

cv2.imshow(f'Before RANSAC ({len(good)} matches, top 60)', before)
cv2.imshow(f'After RANSAC ({len(inliers)} inliers only)', after)
print("按任意键退出")
cv2.waitKey(0)
cv2.destroyAllWindows()
