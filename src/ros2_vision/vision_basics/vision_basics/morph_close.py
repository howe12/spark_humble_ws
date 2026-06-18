import cv2
import numpy as np

# 自生成测试图：白色方块 + 黑点空洞
img = np.zeros((300, 300), dtype=np.uint8)
cv2.rectangle(img, (50, 50), (200, 200), 255, -1)
for _ in range(30):
    x, y = np.random.randint(50, 200, 2)
    cv2.circle(img, (x, y), 3, 0, -1)

kernel = np.ones((5, 5), np.uint8)
closed = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)

cv2.imshow('Original (black holes)', img)
cv2.imshow('Closed (holes filled, size restored)', closed)
cv2.waitKey(0)
cv2.destroyAllWindows()
