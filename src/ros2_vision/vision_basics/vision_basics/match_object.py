#!/usr/bin/env python3
"""02-10 特征匹配: 物体识别 — 模板匹配 + 单应性框

从 test_pattern.png 中裁取一块作为"物体模板"，
用 ORB + KNN 匹配 + RANSAC 单应性在整图中找到它并画框。
"""

import cv2
import numpy as np
import os

# --- 1. 加载场景 & 裁取模板 ---
base = os.path.dirname(__file__)
scene = cv2.imread(os.path.join(base, '..', 'pictures', 'test_pattern.png'))
h, w = scene.shape[:2]

# 裁取右上角的彩色方块区域作为"物体"
template = scene[50:250, 350:550]
tmpl_h, tmpl_w = template.shape[:2]

# --- 2. ORB 检测描述 ---
orb = cv2.ORB_create(500)
kp_t, des_t = orb.detectAndCompute(template, None)
kp_s, des_s = orb.detectAndCompute(scene, None)

# --- 3. 匹配 + 比率测试 ---
bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
raw = bf.knnMatch(des_t, des_s, k=2)
good = [m for m, n in raw if m.distance < 0.75 * n.distance]
print(f"Template→Scene matches (ratio test): {len(good)}")

if len(good) < 4:
    print(f"匹配点不足 ({len(good)} < 4)，无法计算单应性")
    exit(1)

# --- 4. RANSAC 单应性 ---
src = np.float32([kp_t[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
dst = np.float32([kp_s[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
print(f"Homography: {np.sum(mask)} inliers")

# --- 5. 投影模板四角 → 画框 ---
corners = np.float32([[0, 0], [tmpl_w, 0],
                      [tmpl_w, tmpl_h], [0, tmpl_h]]).reshape(-1, 1, 2)
proj = cv2.perspectiveTransform(corners, H)
result = scene.copy()
cv2.polylines(result, [np.int32(proj)], True, (0, 255, 0), 3)

# --- 6. 显示: 模板 | 匹配 | 识别结果 ---
cv2.imshow('Template (object to find)', template)

match_viz = cv2.drawMatches(
    template, kp_t, scene, kp_s, good[:30], None,
    flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
)
cv2.imshow('Matches (top 30)', match_viz)
cv2.imshow('Object detected — green box', result)

print("按任意键退出")
cv2.waitKey(0)
cv2.destroyAllWindows()
