import cv2
import numpy as np
import sys

image_path = sys.path[0]
img = cv2.imread(image_path + "/../pictures/test_pattern.png")
h, w = img.shape[:2]

# 仿射变换：3 组点对确定 6 个自由度
# 源点（原图上的三个角）
pts1 = np.float32([[50, 50], [200, 50], [50, 200]])
# 目标点（变换后的位置）
pts2 = np.float32([[10, 100], [200, 50], [100, 250]])

M = cv2.getAffineTransform(pts1, pts2)
affined = cv2.warpAffine(img, M, (w, h))

# 在原图上标记源点位置
img_marked = img.copy()
for pt in pts1:
    cv2.circle(img_marked, tuple(pt.astype(int)), 5, (0, 0, 255), -1)

# 在变换图上标记目标位置
affined_marked = affined.copy()
for pt in pts2:
    cv2.circle(affined_marked, tuple(pt.astype(int)), 5, (0, 255, 0), -1)

cv2.imshow('Original (red=source pts)', img_marked)
cv2.imshow('Affined (green=target pts)', affined_marked)
cv2.waitKey(0)
cv2.destroyAllWindows()
