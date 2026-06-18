import cv2
import numpy as np
import sys

# 读取测试图（用 02-2 的蓝色方块图做颜色识别 + 形态学后处理）
image_path = sys.path[0]
img = cv2.imread(image_path + "/../pictures/two_blue_cube.png")

# BGR → HSV
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

# 蓝色 HSV 阈值（同 02-2 color_block_detect）
LowerBlue = np.array([95, 120, 80])
UpperBlue = np.array([130, 255, 255])
mask = cv2.inRange(hsv, LowerBlue, UpperBlue)

# 形态学后处理：先开后闭
kernel = np.ones((5, 5), np.uint8)
mask_open = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)   # 去小白点
mask_clean = cv2.morphologyEx(mask_open, cv2.MORPH_CLOSE, kernel)  # 填小黑洞

# 轮廓检测（形态学处理后噪声更少）
contours_raw, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
contours_clean, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# 在原图上标注
result = img.copy()
for c in contours_clean:
    x, y, w, h = cv2.boundingRect(c)
    if w * h > 100:
        cv2.rectangle(result, (x, y), (x + w, y + h), (0, 255, 0), 2)

print(f"处理前轮廓数: {len(contours_raw)}")
print(f"处理后轮廓数: {len(contours_clean)}")

cv2.imshow('Original Mask (noisy)', mask)
cv2.imshow('Cleaned Mask (after morphology)', mask_clean)
cv2.imshow('Detection Result', result)
cv2.waitKey(0)
cv2.destroyAllWindows()
