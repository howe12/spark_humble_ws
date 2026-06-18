import cv2
import numpy as np

# 创建测试图：白色方块 + 白点噪声 + 黑点空洞
img = np.zeros((300, 300), dtype=np.uint8)
cv2.rectangle(img, (50, 50), (200, 200), 255, -1)  # 白色方块

# 添加白点噪声（腐蚀能去掉这些）
for _ in range(20):
    x, y = np.random.randint(0, 300, 2)
    cv2.circle(img, (x, y), 2, 255, -1)

# 添加黑点空洞（膨胀能填上这些）
for _ in range(20):
    x, y = np.random.randint(50, 200, 2)
    cv2.circle(img, (x, y), 3, 0, -1)

# 核
kernel = np.ones((5, 5), np.uint8)

# 腐蚀：取核覆盖区域的最小值 → 白色被蚕食
eroded = cv2.erode(img, kernel, iterations=1)

# 膨胀：取核覆盖区域的最大值 → 白色扩张
dilated = cv2.dilate(img, kernel, iterations=1)

# 显示三窗口对比
cv2.imshow('Original (noise + holes)', img)
cv2.imshow('Eroded (white shrinks)', eroded)
cv2.imshow('Dilated (white expands)', dilated)
cv2.waitKey(0)
cv2.destroyAllWindows()
