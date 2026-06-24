import cv2
import numpy as np
import sys

# 读取图像（转灰度图）
image_path = sys.path[0]
image = cv2.imread(image_path + "/../pictures/lena.png", cv2.IMREAD_GRAYSCALE)

# 用 cv2.Sobel() 计算水平和垂直梯度
# cv2.CV_64F：保留负值（梯度方向信息）
sobel_x = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
sobel_y = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)

# 梯度强度
gradient_magnitude = np.sqrt(sobel_x**2 + sobel_y**2)

# 归一化到 0-255（cv2.Sobel 的输出范围不是 0-255）
magnitude_norm = np.uint8(gradient_magnitude / gradient_magnitude.max() * 255)

# 显示
cv2.imshow('Original', image)
cv2.imshow('Sobel Edges', magnitude_norm)
cv2.waitKey(0)
cv2.destroyAllWindows()
