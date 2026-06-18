#!/usr/bin/env python3
"""反向投影 — cv2.calcBackProject 演示：用直方图找到图中与模板颜色相近的区域"""
import cv2, sys, numpy as np

img_path = sys.path[0] + "/../pictures/test_pattern.png"
img = cv2.imread(img_path)
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

# 模拟"选取目标区域"：取图像中央 80×80 的区域作为模板
h, w = hsv.shape[:2]
roi = hsv[h//2-40:h//2+40, w//2-40:w//2+40]

# 计算模板 H 通道直方图
roi_hist = cv2.calcHist([roi], [0], None, [180], [0, 180])
cv2.normalize(roi_hist, roi_hist, 0, 255, cv2.NORM_MINMAX)

# 反向投影：全图中与模板 H 值相似的像素得高分
backproj = cv2.calcBackProject([hsv], [0], roi_hist, [0, 180], 1)

# 显示
cv2.imshow("Original", img)
cv2.imshow("ROI (template region)", img[h//2-40:h//2+40, w//2-40:w//2+40])
cv2.imshow("Back Projection (brighter = more similar)", backproj)

# 融合显示
backproj_color = cv2.merge([np.zeros_like(backproj), backproj, np.zeros_like(backproj)])
blend = cv2.addWeighted(img, 0.7, backproj_color, 0.3, 0)
cv2.imshow("Blended (green = matched region)", blend)

cv2.waitKey(0)
cv2.destroyAllWindows()
