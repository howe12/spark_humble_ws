import cv2
import numpy as np

# 自生成测试图：白色方块 + 白点噪声
img = np.zeros((300, 300), dtype=np.uint8)
cv2.rectangle(img, (50, 50), (200, 200), 255, -1)
for _ in range(20):
    x, y = np.random.randint(0, 300, 2)
    cv2.circle(img, (x, y), 2, 255, -1)

kernel = np.ones((5, 5), np.uint8)
eroded = cv2.erode(img, kernel, iterations=1)

cv2.imshow('Original', img)
cv2.imshow('Eroded (white shrinks, noise gone)', eroded)
cv2.waitKey(0)
cv2.destroyAllWindows()
