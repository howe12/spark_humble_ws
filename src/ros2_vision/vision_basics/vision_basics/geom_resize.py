import cv2
import sys

image_path = sys.path[0]
img = cv2.imread(image_path + "/../pictures/test_pattern.png")
h, w = img.shape[:2]

# 缩小一半（INTER_AREA 适合缩小）
small = cv2.resize(img, (w // 2, h // 2), interpolation=cv2.INTER_AREA)

cv2.imshow('Original', img)
cv2.imshow('Resized (1/2)', small)
cv2.waitKey(0)
cv2.destroyAllWindows()
