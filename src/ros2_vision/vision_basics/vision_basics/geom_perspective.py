import cv2
import numpy as np
import sys

image_path = sys.path[0]
img = cv2.imread(image_path + "/../pictures/test_pattern.png")
h, w = img.shape[:2]

# 透视变换：4 组点对确定 8 个自由度
# 源点——模拟"倾斜拍摄"的效果（左上角往里推、右下角往外拉）
pts1 = np.float32([[56, 65], [368, 52], [389, 390], [28, 387]])

# 目标——规整的矩形（"从正上方看"）
pts2 = np.float32([[0, 0], [300, 0], [300, 400], [0, 400]])

M = cv2.getPerspectiveTransform(pts1, pts2)
warped = cv2.warpPerspective(img, M, (300, 400))

# 在原图上画四边形标记
img_marked = img.copy()
cv2.polylines(img_marked, [pts1.astype(int)], True, (0, 255, 0), 2)

cv2.imshow('Original (green=selected area)', img_marked)
cv2.imshow('Perspective Warped (top-down view)', warped)
cv2.waitKey(0)
cv2.destroyAllWindows()
