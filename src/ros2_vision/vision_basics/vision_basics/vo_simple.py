#!/usr/bin/env python3
"""03-7 ORB-SLAM3: 简化视觉里程计 — ORB 特征匹配 + 运动估计

用 test_pattern.png 和它的旋转版模拟连续两帧，
演示 V-SLAM 前端的核心流程:
  ORB 特征 → BF 匹配 → 本质矩阵 → R,t 分解 → 轨迹累积

不需要 ORB-SLAM3 安装——纯 OpenCV 演示前端概念。
"""

import cv2
import numpy as np
import os

# --- 1. 模拟两帧: 原图 + 旋转版 ---
base = os.path.dirname(__file__)
frame1 = cv2.imread(os.path.join(base, '..', 'pictures', 'test_pattern.png'))
h, w = frame1.shape[:2]

# 第二帧: 旋转 10° + 平移 (模拟相机运动)
M = cv2.getRotationMatrix2D((w/2, h/2), 10, 1.0)
M[0, 2] += 15  # 水平平移
M[1, 2] += 5   # 垂直平移
frame2 = cv2.warpAffine(frame1, M, (w, h))

gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

# --- 2. ORB 特征检测 + 匹配 ---
orb = cv2.ORB_create(500)
kp1, des1 = orb.detectAndCompute(gray1, None)
kp2, des2 = orb.detectAndCompute(gray2, None)

bf = cv2.BFMatcher(cv2.NORM_HAMMING)
matches = bf.knnMatch(des1, des2, k=2)
good = [m for m, n in matches if m.distance < 0.75 * n.distance]
print(f"ORB 匹配: {len(matches)} 对 → 比率测试后 {len(good)} 对")

# --- 3. 本质矩阵 → R, t ---
src = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
dst = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

# D435 内参
K = np.array([[613.4, 0, 330.2], [0, 612.2, 240.6], [0, 0, 1]], dtype=np.float32)

E, mask = cv2.findEssentialMat(src, dst, K, cv2.RANSAC, 0.999, 1.0)
inliers = np.sum(mask)
print(f"本质矩阵 inliers: {inliers}/{len(good)}")

_, R, t, _ = cv2.recoverPose(E, src, dst, K)
print(f"\n旋转矩阵 R:\n{R}")
print(f"平移向量 t: {t.ravel()}")

# --- 4. 轨迹可视化 ---
# 累积轨迹(简化: 只显示两帧间的运动)
trajectory = np.zeros((300, 500, 3), dtype=np.uint8)
cv2.circle(trajectory, (250, 150), 3, (0, 255, 0), -1)
cv2.putText(trajectory, 'Frame 1', (210, 140),
            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

# 第二帧位置 = t 的 xz 分量投影
dx = int(t[0] * 500)
dy = int(t[2] * 500)
cv2.circle(trajectory, (250+dx, 150+dy), 3, (0, 0, 255), -1)
cv2.putText(trajectory, 'Frame 2', (250+dx+5, 150+dy-5),
            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
cv2.line(trajectory, (250, 150), (250+dx, 150+dy), (255, 255, 0), 1)

# 匹配可视化
match_viz = cv2.drawMatches(frame1, kp1, frame2, kp2,
    [g for i, g in enumerate(good) if mask[i]], None,
    flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)

cv2.imshow('VO: ORB Matching (inliers only)', match_viz)
cv2.imshow('Estimated Trajectory (top-down)', trajectory)
print("\n绿点=帧1  红点=帧2  黄线=估计运动")
print("按任意键退出")
cv2.waitKey(0)
cv2.destroyAllWindows()
