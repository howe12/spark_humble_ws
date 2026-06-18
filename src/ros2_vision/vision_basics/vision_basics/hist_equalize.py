#!/usr/bin/env python3
"""直方图均衡化 — cv2.equalizeHist vs CLAHE 对比"""
import cv2, sys, numpy as np

img_path = sys.path[0] + "/../pictures/test_pattern.png"
gray = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

# 1. 普通均衡化
equ = cv2.equalizeHist(gray)

# 2. CLAHE（局部自适应）
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
cl = clahe.apply(gray)

# 终端统计
print(f"原图: 亮度范围 [{gray.min()}, {gray.max()}], 均值 {gray.mean():.1f}")
print(f"均衡化: 亮度范围 [{equ.min()}, {equ.max()}], 均值 {equ.mean():.1f}")
print(f"CLAHE: 亮度范围 [{cl.min()}, {cl.max()}], 均值 {cl.mean():.1f}")

# 四窗口对比
cv2.imshow("1.Original (Gray)", gray)
cv2.imshow("2.Equalized (Global)", equ)
cv2.imshow("3.CLAHE (Local)", cl)

# 直方图对比
hist_img = np.zeros((300, 256, 3), dtype=np.uint8)
for data, color, label in [(gray, (200, 200, 200), 'orig'),
                             (equ, (0, 255, 0), 'equ'),
                             (cl, (255, 0, 0), 'clahe')]:
    h = cv2.calcHist([data], [0], None, [256], [0, 256])
    hn = h / h.max() * 280
    for x in range(256):
        cv2.line(hist_img, (x, 299), (x, 299 - int(hn[x])), color, 1)
cv2.imshow("4.Histograms (gray=orig, green=equ, red=clahe)", hist_img)

cv2.waitKey(0)
cv2.destroyAllWindows()
