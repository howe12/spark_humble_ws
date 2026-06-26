#!/usr/bin/env python3
"""04-2 实战：解析 mask 数据

对本地图片运行 YOLOv8n-seg，深入解析 mask 数据结构：
  - masks.xy: 轮廓坐标 → 点数/面积/中心
  - masks.data: 概率热力图 → 有效像素/覆盖面积
  - 逐实例提取 → 独立 mask 可视化

用法：
    python3 yolo_seg_mask_explore.py                     # 默认 two_blue_cube.png
    python3 yolo_seg_mask_explore.py pictures/lena.png   # 指定图片
"""

import os, sys
import cv2
import numpy as np
from ament_index_python.packages import get_package_share_directory
from ultralytics import YOLO

# ── 模型加载 ──
MODEL_DIR = os.path.join(get_package_share_directory('vision_basics'), 'model')
model = YOLO(os.path.join(MODEL_DIR, 'yolov8n-seg.pt'))

# ── 图片加载 ──
_base = os.path.dirname(os.path.abspath(__file__))
PIC_DIR = os.path.join(_base, '..', 'pictures')
img_name = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PIC_DIR, 'two_blue_cube.png')
if not os.path.isabs(img_name):
    img_name = os.path.join(PIC_DIR, img_name)

img = cv2.imread(img_name)
if img is None:
    print(f'❌ 图片不存在: {img_name}')
    sys.exit(1)
print(f'📷 图片: {os.path.basename(img_name)} ({img.shape[1]}x{img.shape[0]})')

# ── 推理 ──
results = model(img, conf=0.25, verbose=False)
r = results[0]
boxes = r.boxes
masks = r.masks
names = r.names

if boxes is None or len(boxes) == 0:
    print('⚠️ 未检测到目标')
    cv2.imshow('Original', img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    sys.exit(0)

n = len(boxes)
print(f'🎯 检测到 {n} 个实例\n')

# ══════════════════════════════════════════════════
# 1. 逐实例打印 mask 数据
# ══════════════════════════════════════════════════
print('═' * 60)
print('📊 逐实例 mask 数据')
print('═' * 60)

instance_masks = []  # 收集每个实例的独立二值 mask

for i in range(n):
    cls_id = int(boxes.cls[i])
    conf = float(boxes.conf[i])
    name = names.get(cls_id, f'id:{cls_id}')

    # ── masks.xy: 轮廓坐标 ──
    if masks is not None and i < len(masks.xy):
        contour = masks.xy[i]  # shape: (N_pts, 2)
        n_pts = len(contour)

        # 面积（用 Shoelace 公式）
        if n_pts >= 3:
            x, y = contour[:, 0], contour[:, 1]
            area = 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
        else:
            area = 0

        # 中心
        cx, cy = contour[:, 0].mean(), contour[:, 1].mean()

        # 边界框
        xmin, ymin = contour[:, 0].min(), contour[:, 1].min()
        xmax, ymax = contour[:, 0].max(), contour[:, 1].max()

        print(f'\n实例 {i}: {name} (conf={conf:.2f})')
        print(f'  masks.xy 形状: ({n_pts}, 2) — {n_pts} 个轮廓点')
        print(f'  轮廓面积:     {area:.0f} px²')
        print(f'  轮廓中心:     ({cx:.0f}, {cy:.0f})')
        print(f'  轮廓边界框:   ({xmin:.0f}, {ymin:.0f}) → ({xmax:.0f}, {ymax:.0f})')
        print(f'  boxes.xywh:   ({boxes.xywh[i][0]:.0f}, {boxes.xywh[i][1]:.0f}, '
              f'{boxes.xywh[i][2]:.0f}, {boxes.xywh[i][3]:.0f})')

        # 生成独立二值 mask（画多边形填充）
        bin_mask = np.zeros(img.shape[:2], dtype=np.uint8)
        pts = contour.astype(np.int32).reshape((-1, 1, 2))
        cv2.fillPoly(bin_mask, [pts], 255)
        mask_pixels = cv2.countNonZero(bin_mask)
        print(f'  二值 mask 像素数: {mask_pixels}')
        print(f'  mask 占图像比:    {mask_pixels / (img.shape[0]*img.shape[1]) * 100:.1f}%')

        instance_masks.append((name, bin_mask, contour))

    else:
        print(f'\n实例 {i}: {name} (conf={conf:.2f})')
        print(f'  ⚠️ 无 mask 数据')

    # ── masks.data: 概率热力图（仅第一个实例演示）──
    if masks is not None and i == 0 and hasattr(masks, 'data'):
        prob = masks.data[0].cpu().numpy()  # (H, W) 概率图
        print(f'\n💡 masks.data 概率热力图（实例 0 演示）:')
        print(f'  data 形状:    {masks.data.shape}')
        print(f'  data 范围:    [{prob.min():.3f}, {prob.max():.3f}]')
        print(f'  data ≥ 0.5:   {(prob >= 0.5).sum()} px')
        print(f'  data ≥ 0.9:   {(prob >= 0.9).sum()} px')

# ══════════════════════════════════════════════════
# 2. 可视化：原始图 + 逐实例 mask
# ══════════════════════════════════════════════════
print(f'\n{"═"*60}')
print('🖼️  可视化：原始 → 全量 → 逐实例')
print('═' * 60)

# 面板 0: 原始图
panels = [img.copy()]
labels = ['Original']

# 面板 1: YOLO 全量标注
annotated = r.plot()
panels.append(annotated)
labels.append('All masks (r.plot)')

# 面板 2+: 每个实例的独立 mask
colors = [
    (0, 0, 255), (0, 255, 0), (255, 0, 0),
    (255, 255, 0), (255, 0, 255), (0, 255, 255),
]
for idx, (name, bin_mask, contour) in enumerate(instance_masks):
    overlay = img.copy()
    color = colors[idx % len(colors)]

    # 半透明 mask 叠加
    colored = np.zeros_like(img)
    colored[bin_mask > 0] = color
    overlay = cv2.addWeighted(overlay, 0.6, colored, 0.4, 0)

    # 轮廓线
    pts = contour.astype(np.int32).reshape((-1, 1, 2))
    cv2.polylines(overlay, [pts], True, color, 2)

    # 标签
    cx, cy = int(contour[:, 0].mean()), int(contour[:, 1].mean())
    cv2.putText(overlay, f'{idx}:{name}', (cx - 30, cy),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    panels.append(overlay)
    labels.append(f'{name} only')

# 拼成网格（每行 3 个）
ROWS = (len(panels) + 2) // 3
cell_h, cell_w = 200, 300
grid = np.zeros((ROWS * cell_h, 3 * cell_w, 3), dtype=np.uint8)

for i, (panel, label) in enumerate(zip(panels, labels)):
    r, c = i // 3, i % 3
    y1, y2 = r * cell_h, (r + 1) * cell_h
    x1, x2 = c * cell_w, (c + 1) * cell_w

    resized = cv2.resize(panel, (cell_w, cell_h))
    grid[y1:y2, x1:x2] = resized

    # 标签
    cv2.putText(grid, label, (x1 + 5, y1 + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

cv2.namedWindow('Mask 数据探索 — 按任意键退出', cv2.WINDOW_NORMAL)
cv2.resizeWindow('Mask 数据探索 — 按任意键退出', 900, 600)
cv2.imshow('Mask 数据探索 — 按任意键退出', grid)
cv2.waitKey(0)
cv2.destroyAllWindows()

print('\n✅ 完成。每个面板的含义：')
print('  Original        — 原始图片')
print('  All masks       — YOLO r.plot() 全量标注')
print('  {name} only     — 单个实例的半透明 mask + 轮廓')
