#!/usr/bin/env python3
"""多尺度模板匹配 — 用图像金字塔在多个尺度上搜索模板，找到最佳匹配位置"""
import cv2, sys, numpy as np

img_path = sys.path[0] + "/../pictures/test_pattern.png"
img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

# 自生成"模板"：取图像中央一小块
h, w = img.shape
roi = img[h//2-30:h//2+30, w//2-30:w//2+30]
template = roi.copy()

# 多尺度搜索
best_val, best_loc, best_scale, best_shape = -1, (0, 0), 1.0, template.shape
for scale in np.arange(0.5, 2.0, 0.1):
    new_w = int(template.shape[1] * scale)
    new_h = int(template.shape[0] * scale)
    if new_w < 1 or new_h < 1 or new_w > w or new_h > h:
        continue
    scaled_tmpl = cv2.resize(template, (new_w, new_h))
    result = cv2.matchTemplate(img, scaled_tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    if max_val > best_val:
        best_val, best_loc, best_scale, best_shape = max_val, max_loc, scale, scaled_tmpl.shape

# 绘制结果
top_left = best_loc
bottom_right = (top_left[0] + best_shape[1], top_left[1] + best_shape[0])
result_img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
cv2.rectangle(result_img, top_left, bottom_right, (0, 255, 0), 2)
cv2.putText(result_img, f"scale={best_scale:.1f} val={best_val:.3f}",
            (top_left[0], max(top_left[1]-10, 15)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

print(f"最佳匹配: scale={best_scale:.1f}, confidence={best_val:.3f}")
print(f"位置: ({top_left[0]}, {top_left[1]})  模板尺寸: {best_shape[1]}×{best_shape[0]}")

cv2.imshow("Template", template)
cv2.imshow("Multi-Scale Match Result", result_img)
cv2.waitKey(0)
cv2.destroyAllWindows()
