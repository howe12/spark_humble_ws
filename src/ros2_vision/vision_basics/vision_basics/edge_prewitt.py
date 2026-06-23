import cv2
import numpy as np
import sys

# 读取图像（转灰度图——边缘检测必须在灰度图上做）
image_path = sys.path[0]
image = cv2.imread(image_path + "/../pictures/lena.png", cv2.IMREAD_GRAYSCALE)

# Prewitt 算子（水平和垂直）
prewitt_x = np.array([[-1, 0, 1],
                       [-1, 0, 1],
                       [-1, 0, 1]], dtype=np.float32)

prewitt_y = np.array([[-1, -1, -1],
                       [ 0,  0,  0],
                       [ 1,  1,  1]], dtype=np.float32)

# 用 cv2.filter2D() 计算水平和垂直梯度
gradient_x = cv2.filter2D(image, -1, prewitt_x)
gradient_y = cv2.filter2D(image, -1, prewitt_y)

# 梯度强度：sqrt(Gx^2 + Gy^2)，归一化到 0~255
gradient_magnitude = np.sqrt(gradient_x**2 + gradient_y**2)
gradient_magnitude = gradient_magnitude / gradient_magnitude.max() * 255

# 显示
cv2.imshow('Original', image)
cv2.imshow('Prewitt Edges', gradient_magnitude.astype(np.uint8))
cv2.waitKey(0)
cv2.destroyAllWindows()
