import cv2
import numpy as np
import sys

image_path = sys.path[0]
img = cv2.imread(image_path + "/../pictures/test_pattern.png")
h, w = img.shape[:2]

# 绕中心逆时针 45 度
M = cv2.getRotationMatrix2D((w / 2, h / 2), 45, 1.0)
rotated = cv2.warpAffine(img, M, (w, h))

cv2.imshow('Original', img)
cv2.imshow('Rotated 45deg', rotated)
cv2.waitKey(0)
cv2.destroyAllWindows()
