import cv2
import numpy as np
import sys

image_path = sys.path[0]
img = cv2.imread(image_path + "/../pictures/test_pattern.png")
h, w = img.shape[:2]

# 1. 平移：向右 100，向下 50
M_trans = np.float32([[1, 0, 100], [0, 1, 50]])
translated = cv2.warpAffine(img, M_trans, (w, h))

# 2. 缩放：缩小到一半
scaled_down = cv2.resize(img, (w // 2, h // 2))
scaled_up = cv2.resize(img, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)

# 3. 旋转：绕中心逆时针 45 度
M_rot = cv2.getRotationMatrix2D((w / 2, h / 2), 45, 1.0)
rotated = cv2.warpAffine(img, M_rot, (w, h))

# 4. 翻转
flipped_h = cv2.flip(img, 1)   # 水平
flipped_v = cv2.flip(img, 0)   # 垂直

# 显示
cv2.imshow('Original', img)
cv2.imshow('Translated (100,50)', translated)
cv2.imshow('Scaled Down (1/2)', scaled_down)
cv2.imshow('Rotated 45deg', rotated)
cv2.imshow('Flipped H', flipped_h)
cv2.imshow('Flipped V', flipped_v)
cv2.waitKey(0)
cv2.destroyAllWindows()
