import sys
import cv2

# 读取带高斯噪声的图像
image_path = sys.path[0]
img = cv2.imread(image_path + "/../pictures/test_pattern_gauss.png")

# 调整分辨率
dsize = (640, 640)
resize_frame = cv2.resize(img, dsize)

# 高斯滤波（窗口 9x9，标准差 5）
blurred_image = cv2.GaussianBlur(resize_frame, (9, 9), 5)

# 显示对比
cv2.imshow('Original (gauss noise)', resize_frame)
cv2.imshow('Gaussian Blur (9x9, sigma=5)', blurred_image)
cv2.waitKey(0)
cv2.destroyAllWindows()
