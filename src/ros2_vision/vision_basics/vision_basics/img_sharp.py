import sys
import cv2

# 读取图像（用混合噪声图测试锐化效果）
image_path = sys.path[0]
img = cv2.imread(image_path + "/../pictures/lena_mixed.png")

# 两级模糊：轻度和重度
blurred_low = cv2.medianBlur(img, 3)     # 轻度模糊
blurred_high = cv2.medianBlur(img, 13)    # 重度模糊

# 提取边缘（低模糊 - 高模糊）
edge = cv2.addWeighted(blurred_low, 1, blurred_high, -1, 0)

# 锐化（低模糊图 + 边缘）
sharpened = cv2.addWeighted(blurred_low, 1, edge, 1, 0)

# 显示所有结果
cv2.imshow('Original', img)
cv2.imshow('Blur Low (3)', blurred_low)
cv2.imshow('Blur High (13)', blurred_high)
cv2.imshow('Edge', edge)
cv2.imshow('Sharpened', sharpened)
cv2.waitKey(0)
cv2.destroyAllWindows()
