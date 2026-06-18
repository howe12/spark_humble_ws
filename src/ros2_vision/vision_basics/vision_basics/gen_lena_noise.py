#!/usr/bin/env python3
"""为 lena.png 添加噪声，生成测试用噪声图像。

生成 4 种:
  - lena_sp.png         椒盐噪声 (salt & pepper)
  - lena_gauss.png      高斯噪声
  - lena_mixed.png      混合噪声 (椒盐 + 高斯)
  - lena_sp_noise.png   椒盐噪声 (与参考版 lena_salt_pepper_noise.jpeg 对应)
"""

import cv2
import numpy as np
import os

base = os.path.dirname(__file__)
pictures = os.path.join(base, '..', 'pictures')

# 加载原始 lena
src_path = os.path.join(pictures, 'lena.png')
if not os.path.exists(src_path):
    print(f"❌ 找不到 {src_path}")
    exit(1)

img = cv2.imread(src_path)
h, w = img.shape[:2]
print(f"lena.png: {w}×{h}")

# --- 1. 椒盐噪声 ---
def add_salt_pepper(image, amount=0.02):
    noisy = image.copy()
    n = int(amount * image.size)
    # 盐 (白点)
    coords = [np.random.randint(0, i-1, n) for i in image.shape[:2]]
    noisy[coords[0], coords[1]] = 255
    # 椒 (黑点)
    coords = [np.random.randint(0, i-1, n) for i in image.shape[:2]]
    noisy[coords[0], coords[1]] = 0
    return noisy

sp = add_salt_pepper(img, 0.02)
cv2.imwrite(os.path.join(pictures, 'lena_sp.png'), sp)
cv2.imwrite(os.path.join(pictures, 'lena_sp_noise.png'), sp)
print("lena_sp.png / lena_sp_noise.png — 椒盐噪声 2%")

# --- 2. 高斯噪声 ---
def add_gaussian(image, sigma=25):
    noise = np.random.normal(0, sigma, image.shape).astype(np.int16)
    noisy = image.astype(np.int16) + noise
    return np.clip(noisy, 0, 255).astype(np.uint8)

gauss = add_gaussian(img, 25)
cv2.imwrite(os.path.join(pictures, 'lena_gauss.png'), gauss)
print("lena_gauss.png — 高斯噪声 σ=25")

# --- 3. 混合噪声 ---
mixed = add_salt_pepper(add_gaussian(img, 15), 0.01)
cv2.imwrite(os.path.join(pictures, 'lena_mixed.png'), mixed)
print("lena_mixed.png — 混合噪声(高斯σ=15 + 椒盐1%)")

print("\n✅ 全部生成完成")
