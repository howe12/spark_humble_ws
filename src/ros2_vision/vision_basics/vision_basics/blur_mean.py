import sys
import cv2

# 读取带噪声的图像（参考版 lena_salt_pepper_noise.jpeg → 实践版 sp_noise.png）
image_path = sys.path[0]
img = cv2.imread(image_path + "/../pictures/test_pattern_sp.png")

# 调整分辨率
dsize = (640, 640)
resize_frame = cv2.resize(img, dsize)

# 均值滤波（5x5 卷积核）
blurred_image = cv2.blur(resize_frame, (5, 5))

# 显示对比
cv2.imshow('Original (noise)', resize_frame)
cv2.imshow('Mean Blur (5x5)', blurred_image)
cv2.waitKey(0)
cv2.destroyAllWindows()
