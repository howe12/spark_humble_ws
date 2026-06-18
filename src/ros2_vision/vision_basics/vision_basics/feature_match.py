#!/usr/bin/env python3
"""特征匹配 — SIFT vs ORB，BFMatcher + drawMatches，自生成旋转图匹配"""
import cv2, sys, numpy as np

img_path = sys.path[0] + "/../pictures/test_pattern.png"
img1 = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

# 自生成旋转 20° 的图
h, w = img1.shape
M = cv2.getRotationMatrix2D((w/2, h/2), 20, 1.0)
img2 = cv2.warpAffine(img1, M, (w, h))

results = []
for name, detector, matcher_type in [
    ("SIFT", cv2.SIFT_create(nfeatures=300), "L2"),
    ("ORB", cv2.ORB_create(nfeatures=300), "HAMMING")]:
    
    kp1, des1 = detector.detectAndCompute(img1, None)
    kp2, des2 = detector.detectAndCompute(img2, None)
    
    if matcher_type == "HAMMING":
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    else:
        bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=True)
    
    matches = bf.match(des1, des2)
    matches = sorted(matches, key=lambda x: x.distance)[:50]
    
    result = cv2.drawMatches(img1, kp1, img2, kp2, matches, None,
                             flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
    results.append((name, result, len(matches), len(kp1), len(kp2)))
    print(f"{name}: {len(kp1)}/{len(kp2)} kpts → {len(matches)} matches "
          f"(best distance={matches[0].distance:.1f})")

# 上下拼接两个匹配结果
h_sift = results[0][1].shape[0]
h_orb = results[1][1].shape[0]
if results[0][1].shape[1] != results[1][1].shape[1]:
    results[1][1] = cv2.resize(results[1][1], (results[0][1].shape[1], results[1][1].shape[0]))
combined = np.vstack([results[0][1], results[1][1]])
cv2.putText(combined, f"SIFT: {results[0][2]} matches", (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
cv2.putText(combined, f"ORB: {results[1][2]} matches", (10, h_sift+30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

cv2.imshow("Feature Matching (top=SIFT, bottom=ORB)", combined)
cv2.imshow("Original", img1)
cv2.imshow("Rotated 20 deg", img2)
cv2.waitKey(0)
cv2.destroyAllWindows()
