# 本地图像 BGR→HSV 色彩空间转换
import sys
import cv2

# 读取图像
image_path = sys.path[0]
img = cv2.imread(image_path + "/../pictures/test_image.png")

cv2.imshow('BGR Image', img)

# 将 BGR 色彩空间转换为 HSV 色彩空间
hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

# 显示 HSV 图像
cv2.imshow('HSV Image', hsv_img)
cv2.waitKey(0)
cv2.destroyAllWindows()
