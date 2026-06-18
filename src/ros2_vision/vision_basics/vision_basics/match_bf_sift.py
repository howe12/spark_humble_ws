#!/usr/bin/env python3
"""02-10 特征匹配: SIFT + BFMatcher(NORM_L2) + match()

暴力匹配最简入门: SIFT 检测 → 计算描述子 → BFMatcher 单最近邻匹配 → 可视化前 30 对。
演示 match() 返回值: DMatch.distance / queryIdx / trainIdx。
"""

import cv2
import numpy as np
import os

# --- 1. 生成测试场景对 ---
base = os.path.dirname(__file__)
scene = cv2.imread(os.path.join(base, '..', 'pictures', 'test_pattern.png'))
h, w = scene.shape[:2]

# 对原图做旋转 + 缩小模拟不同视角
M = cv2.getRotationMatrix2D((w / 2, h / 2), 20, 0.85)
query = cv2.warpAffine(scene, M, (w, h))

# --- 2. SIFT 检测 + 描述 ---
sift = cv2.SIFT_create()
kp_scene, des_scene = sift.detectAndCompute(cv2.cvtColor(scene, cv2.COLOR_BGR2GRAY), None)
kp_query, des_query = sift.detectAndCompute(cv2.cvtColor(query, cv2.COLOR_BGR2GRAY), None)

print(f"Scene: {len(kp_scene)} keypoints  |  Query: {len(kp_query)} keypoints")

# --- 3. BFMatcher(NORM_L2) 单最近邻匹配 ---
bf = cv2.BFMatcher(cv2.NORM_L2)
matches = bf.match(des_query, des_scene)

# --- 4. 排序，取前 30 ---
matches = sorted(matches, key=lambda m: m.distance)
print(f"Total matches: {len(matches)} | Showing top 30")

result = cv2.drawMatches(
    query, kp_query,
    scene, kp_scene,
    matches[:30], None,
    flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
)

# --- 5. 显示 ---
cv2.imshow('BFMatcher SIFT — NORM_L2 (top 30)', result)
print("按任意键退出")
cv2.waitKey(0)
cv2.destroyAllWindows()
