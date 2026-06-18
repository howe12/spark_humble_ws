import sys
import cv2

# 读取带椒盐噪声的图像
image_path = sys.path[0]
img = cv2.imread(image_path + "/../pictures/lena_sp.png")

# 调整分辨率
dsize = (640, 640)
resize_frame = cv2.resize(img, dsize)

# 中值滤波（窗口大小 9，必须为奇数）
blurred_image = cv2.medianBlur(resize_frame, 9)

# 显示对比
cv2.imshow('Original (salt & pepper)', resize_frame)
cv2.imshow('Median Blur (9)', blurred_image)
cv2.waitKey(0)
cv2.destroyAllWindows()
