#!/usr/bin/env python3
"""SIFT vs ORB 同图对比 — 左右分屏，比较特征点分布和检测数量"""
import cv2, sys, numpy as np

img_path = sys.path[0] + "/../pictures/test_pattern.png"
img = cv2.imread(img_path)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# SIFT
sift = cv2.SIFT_create(nfeatures=300)
kp_s, _ = sift.detectAndCompute(gray, None)
s = cv2.drawKeypoints(img, kp_s, None, flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

# ORB
orb = cv2.ORB_create(nfeatures=300)
kp_o, _ = orb.detectAndCompute(gray, None)
o = cv2.drawKeypoints(img, kp_o, None, (0, 255, 0), 2)

side = np.hstack([s, o])
w = side.shape[1]//2
cv2.putText(side, f"SIFT ({len(kp_s)} pts)", (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,0), 2)
cv2.putText(side, f"ORB ({len(kp_o)} pts)", (w+10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,0), 2)

print(f"SIFT: {len(kp_s)} keypoints  |  ORB: {len(kp_o)} keypoints")
cv2.imshow("SIFT (left) vs ORB (right)", side)
cv2.waitKey(0)
cv2.destroyAllWindows()
