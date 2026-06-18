#!/usr/bin/env python3
"""02-10 特征匹配: FLANN 匹配 — KD-Tree(SIFT) vs LSH(ORB)

FLANN 是近似最近邻库，用索引结构加速大规模匹配。
本程序对比两种描述子类型对应的 FLANN 索引:
  SIFT 浮点描述子 → KD-Tree (算法 1)
  ORB 二进制描述子 → LSH (算法 6)
"""

import cv2
import os
import time

# --- 1. 生成测试场景对 ---
base = os.path.dirname(__file__)
scene = cv2.imread(os.path.join(base, '..', 'pictures', 'test_pattern.png'))
h, w = scene.shape[:2]

M = cv2.getRotationMatrix2D((w / 2, h / 2), 25, 0.8)
query = cv2.warpAffine(scene, M, (w, h))

gray_scene = cv2.cvtColor(scene, cv2.COLOR_BGR2GRAY)
gray_query = cv2.cvtColor(query, cv2.COLOR_BGR2GRAY)

# --- 2. SIFT + FLANN (KD-Tree) ---
sift = cv2.SIFT_create()
kp1, des1 = sift.detectAndCompute(gray_query, None)
kp2, des2 = sift.detectAndCompute(gray_scene, None)

FLANN_INDEX_KDTREE = 1
index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
search_params = dict(checks=50)

t0 = time.time()
flann = cv2.FlannBasedMatcher(index_params, search_params)
matches_sift = flann.knnMatch(des1, des2, k=2)
t_sift = time.time() - t0

good_sift = [m for m, n in matches_sift if m.distance < 0.75 * n.distance]
print(f"SIFT: {len(matches_sift)} raw → {len(good_sift)} good (KD-Tree, {t_sift:.3f}s)")

# --- 3. ORB + FLANN (LSH) ---
orb = cv2.ORB_create(800)
kp1o, des1o = orb.detectAndCompute(gray_query, None)
kp2o, des2o = orb.detectAndCompute(gray_scene, None)

FLANN_INDEX_LSH = 6
index_params_o = dict(algorithm=FLANN_INDEX_LSH,
                      table_number=6, key_size=12, multi_probe_level=1)
search_params_o = dict(checks=50)

t0 = time.time()
flann_o = cv2.FlannBasedMatcher(index_params_o, search_params_o)
matches_orb = flann_o.knnMatch(des1o, des2o, k=2)
t_orb = time.time() - t0

good_orb = []
for pair in matches_orb:
    if len(pair) >= 2 and pair[0].distance < 0.75 * pair[1].distance:
        good_orb.append(pair[0])
print(f"ORB:  {len(matches_orb)} raw → {len(good_orb)} good (LSH,    {t_orb:.3f}s)")

# --- 4. 可视化并排 ---
img_sift = cv2.drawMatches(
    query, kp1, scene, kp2, good_sift[:40], None,
    flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
)
img_orb = cv2.drawMatches(
    query, kp1o, scene, kp2o, good_orb[:40], None,
    flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
)

cv2.imshow('FLANN SIFT (KD-Tree) — top 40', img_sift)
cv2.imshow('FLANN ORB  (LSH)    — top 40', img_orb)
print("按任意键退出")
cv2.waitKey(0)
cv2.destroyAllWindows()
