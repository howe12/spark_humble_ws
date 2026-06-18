import cv2
import numpy as np

# 创建测试图：白色方块 + 白点 + 黑点
img = np.zeros((300, 300), dtype=np.uint8)
cv2.rectangle(img, (50, 50), (200, 200), 255, -1)

# 白点噪声（开运算能去掉）
for _ in range(30):
    x, y = np.random.randint(0, 300, 2)
    cv2.circle(img, (x, y), 2, 255, -1)

# 黑点空洞（闭运算能填上）
for _ in range(30):
    x, y = np.random.randint(50, 200, 2)
    cv2.circle(img, (x, y), 3, 0, -1)

kernel = np.ones((5, 5), np.uint8)

# 开运算：先腐蚀（去白点）→ 再膨胀（恢复大小）
opened = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel)

# 闭运算：先膨胀（填黑洞）→ 再腐蚀（恢复大小）
closed = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)

# 顺序组合：先开后闭 = 去白点 + 填黑洞
clean = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)

cv2.imshow('Original (noise + holes)', img)
cv2.imshow('Opened (white noise gone)', opened)
cv2.imshow('Closed (black holes filled)', closed)
cv2.imshow('Open + Close (clean)', clean)
cv2.waitKey(0)
cv2.destroyAllWindows()
