import cv2
import sys

image_path = sys.path[0]
img = cv2.imread(image_path + "/../pictures/test_pattern.png")

# 水平翻转
flipped = cv2.flip(img, 1)

cv2.imshow('Original', img)
cv2.imshow('Flipped Horizontally', flipped)
cv2.waitKey(0)
cv2.destroyAllWindows()
