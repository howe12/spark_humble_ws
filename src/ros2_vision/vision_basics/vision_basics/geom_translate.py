import cv2
import numpy as np
import sys

image_path = sys.path[0]
img = cv2.imread(image_path + "/../pictures/test_pattern.png")
h, w = img.shape[:2]

# 向右 100，向下 50
M = np.float32([[1, 0, 100], [0, 1, 50]])
translated = cv2.warpAffine(img, M, (w, h))

cv2.imshow('Original', img)
cv2.imshow('Translated (x+100, y+50)', translated)
cv2.waitKey(0)
cv2.destroyAllWindows()
