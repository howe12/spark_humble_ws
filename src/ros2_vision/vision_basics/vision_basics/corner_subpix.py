#!/usr/bin/env python3
"""亚像素角点精化 — cv2.cornerSubPix 将像素级角点精化到亚像素精度"""
import cv2, sys, numpy as np

img_path = sys.path[0] + "/../pictures/test_pattern.png"
img = cv2.imread(img_path)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# 先用 Shi-Tomasi 粗检
corners = cv2.goodFeaturesToTrack(gray, maxCorners=50, qualityLevel=0.01, minDistance=20)
if corners is None:
    print("no corners"); exit()

# 精化到亚像素
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.001)
corners_sub = cv2.cornerSubPix(gray, corners, winSize=(5, 5),
                                zeroZone=(-1, -1), criteria=criteria)

# 对比显示
result = img.copy()
result_sub = img.copy()
for (x, y), (xs, ys) in zip(corners.reshape(-1, 2), corners_sub.reshape(-1, 2)):
    cv2.circle(result, (int(x), int(y)), 5, (0, 0, 255), -1)
    cv2.circle(result_sub, (int(xs), int(ys)), 5, (0, 255, 0), -1)
    # 位移箭头
    cv2.arrowedLine(result_sub, (int(x), int(y)), (int(xs), int(ys)),
                    (255, 0, 0), 1, tipLength=0.3)

# 打印前 5 个点的像素位移
print(f"亚像素精化: {len(corners)} 个角点")
print(f"{'#':<4} {'原始(x,y)':<20} {'精化(x,y)':<20} {'位移(px)':<10}")
for i in range(min(5, len(corners))):
    ox, oy = corners[i].ravel()
    sx, sy = corners_sub[i].ravel()
    d = np.sqrt((ox-sx)**2 + (oy-sy)**2)
    print(f"{i:<4} ({ox:6.1f}, {oy:6.1f})   ({sx:6.2f}, {sy:6.2f})   {d:.3f}")

cv2.imshow("Original (pixel-level)", result)
cv2.imshow("Subpixel Refined (green=refined, arrows=shift)", result_sub)
cv2.waitKey(0)
cv2.destroyAllWindows()
