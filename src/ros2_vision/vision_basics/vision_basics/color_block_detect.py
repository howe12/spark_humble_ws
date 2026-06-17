# 颜色方块识别 —— 蓝色方块 HSV 阈值提取 + 轮廓检测 + 中心点定位
import cv2
import sys
import numpy as np

scripts_path = sys.path[0]

# 1. 读取图片
image = cv2.imread(scripts_path + "/../pictures/two_blue_cube.png")

# 2. BGR→HSV 色彩空间转换
hsv_img = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

# 3. 蓝色 HSV 阈值范围（需根据实际光照调整）
LowerBlue = np.array([95, 120, 80])
UpperBlue = np.array([130, 255, 255])

# 4. 阈值处理 → 二值 mask
mask = cv2.inRange(hsv_img, LowerBlue, UpperBlue)

cv2.imshow("hsv_img", hsv_img)
cv2.imshow("mask", mask)

# 5. 轮廓检测
contours, hier = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
cv2.drawContours(image, contours, -1, (0, 255, 0), 2)

# 6. 获取每个轮廓的中心点并标注
for i, contour in enumerate(contours):
    x, y, w, h = cv2.boundingRect(contour)

    # 面积过滤：忽略噪点
    block_size = w * h
    if block_size < 20000:
        continue

    top_left = (x, y)
    top_right = (x + w, y)
    bottom_left = (x, y + h)
    bottom_right = (x + w, y + h)

    # 计算中心点
    center_x = x + w // 2
    center_y = y + h // 2
    center_point = (center_x, center_y)

    # 打印信息
    print(f"Contour {i}:")
    print(f"  Top Left: {top_left}")
    print(f"  Top Right: {top_right}")
    print(f"  Bottom Left: {bottom_left}")
    print(f"  Bottom Right: {bottom_right}")
    print(f"  Center Point: {center_point}")
    print(f"  Block Size: {block_size}")

    # 在图像上绘制矩形和中心点
    cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
    cv2.circle(image, center_point, 5, (255, 0, 0), -1)
    cv2.putText(image, str(center_point), center_point,
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

cv2.imshow("origin_img", image)
cv2.waitKey()
cv2.destroyAllWindows()
