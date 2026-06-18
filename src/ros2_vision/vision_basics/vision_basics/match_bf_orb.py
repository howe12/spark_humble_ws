#!/usr/bin/env python3
"""02-10 特征匹配: ORB + BFMatcher(NORM_HAMMING) + knnMatch + 比率测试

二进制描述子的标准匹配流程:
  ORB 检测 → BFMatcher(NORM_HAMMING) → knnMatch(k=2) → Lowe 比率测试 (0.75)
"""

import cv2
import numpy as np
import os

# --- 1. 生成测试场景对 ---
base = os.path.dirname(__file__)
scene = cv2.imread(os.path.join(base, '..', 'pictures', 'test_pattern.png'))
h, w = scene.shape[:2]

# 旋转 + 缩小
M = cv2.getRotationMatrix2D((w / 2, h / 2), 30, 0.75)
query = cv2.warpAffine(scene, M, (w, h))

# --- 2. ORB 检测 + 描述 ---
orb = cv2.ORB_create(800)
kp_scene, des_scene = orb.detectAndCompute(scene, None)
kp_query, des_query = orb.detectAndCompute(query, None)

print(f"Scene: {len(kp_scene)} keypoints  |  Query: {len(kp_query)} keypoints")

# --- 3. BFMatcher (汉明距离) + knnMatch(k=2) ---
bf = cv2.BFMatcher(cv2.NORM_HAMMING)
raw_matches = bf.knnMatch(des_query, des_scene, k=2)

# --- 4. Lowe 比率测试 ---
RATIO = 0.75
good = [m for m, n in raw_matches if m.distance < RATIO * n.distance]
print(f"All matches: {len(raw_matches)} | After ratio test: {len(good)}")

# --- 5. 并排对比: 全匹配 vs 比率测试后 ---
all_img = cv2.drawMatches(
    query, kp_query, scene, kp_scene,
    [m[0] for m in raw_matches[:50]], None,
    flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
)
good_img = cv2.drawMatches(
    query, kp_query, scene, kp_scene,
    good[:50], None,
    flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
)

cv2.imshow('All matches (50)', all_img)
cv2.imshow(f'Ratio test 0.75 (top 50 of {len(good)})', good_img)
print("按任意键退出")
cv2.waitKey(0)
cv2.destroyAllWindows()
