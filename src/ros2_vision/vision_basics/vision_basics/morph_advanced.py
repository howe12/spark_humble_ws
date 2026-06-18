import cv2
import numpy as np

# 用 test_pattern 转灰度做演示
import sys
image_path = sys.path[0]
img = cv2.imread(image_path + "/../pictures/test_pattern.png", cv2.IMREAD_GRAYSCALE)

# 二值化（方便看形态学效果）
_, binary = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)

# 核
kernel_small = np.ones((3, 3), np.uint8)
kernel_large = np.ones((25, 25), np.uint8)

# 形态学梯度：膨胀 - 腐蚀 = 边缘
gradient = cv2.morphologyEx(binary, cv2.MORPH_GRADIENT, kernel_small)

# 礼帽：原图 - 开运算 = 亮细节
tophat = cv2.morphologyEx(binary, cv2.MORPH_TOPHAT, kernel_large)

# 黑帽：闭运算 - 原图 = 暗细节
blackhat = cv2.morphologyEx(binary, cv2.MORPH_BLACKHAT, kernel_large)

cv2.imshow('Binary', binary)
cv2.imshow('Gradient (edges)', gradient)
cv2.imshow('TopHat (bright details)', tophat)
cv2.imshow('BlackHat (dark details)', blackhat)
cv2.waitKey(0)
cv2.destroyAllWindows()
