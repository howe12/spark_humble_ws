#!/usr/bin/python3.10
"""
================================================================================
hybrid_detector.py — YOLOv8s 初筛 + RT-DETR-L 精检  混合检测策略
================================================================================

设计动机
--------
YOLO 和 RT-DETR 各有所长：
  · YOLO       → 速度快（~150ms）、召回高、适合大面积初筛
  · RT-DETR    → 精度高（NMS-free）、全局注意力、适合精确判断

混合策略将两者串联：
  1. YOLOv8s 用极低阈值（conf=0.1）扫描全图，找出所有"可疑区域"
  2. 裁剪每个可疑区域，扩展 10% 防止截断
  3. RT-DETR 用高阈值（conf=0.5）对每个裁剪区精确识别
  4. 将局部坐标映射回原图，输出最终结果

这样做的好处：
  · 召回率 = YOLO 低阈值覆盖面（不会漏）
  · 精度   = RT-DETR 高阈值判定（不会误）
  · 速度   = YOLO 全图一遍（快）+ RT-DETR 仅跑小块（少）

对比纯策略：
  纯 YOLO conf=0.5  → 可能漏检（小目标、遮挡）
  纯 RT-DETR 全图   → 慢（大图 Transformer 计算量大）
  混合              → 又快又准

执行流程（7 步）
---------------
Step 1  加载模型       YOLOv8s + RT-DETR-L 同时驻留内存
Step 2  读取图片       支持命令行指定或默认 street_crowd.jpg
Step 3  YOLO 初筛      conf=0.1，提取所有候选边界框
Step 4  区域扩展       每个候选框四边扩展 10%，防裁剪过紧
Step 5  裁剪+精检      逐个裁剪区域送入 RT-DETR（conf=0.5）
Step 6  坐标映射       局部检测框 → 全局原图坐标
Step 7  显示+保存      cv2.imshow + imwrite 输出

用法
----
    python3 hybrid_detector.py                              # 默认图片
    python3 hybrid_detector.py ../pictures/street_crowd.jpg # 指定图片

依赖
----
    · ultralytics >= 8.2.0（RTDETR + YOLO）
    · rtdetr-l.pt  在 vision_basics/model/（66.5MB）
    · yolov8s.pt   在 vision_basics/model/（22.6MB）

================================================================================
"""

import os, sys, time

# ═══════════════════════════════════════════════════════════════════════════════
# Spark 显示配置（必须在 import cv2 之前）
# ═══════════════════════════════════════════════════════════════════════════════
if 'DISPLAY' not in os.environ:
    os.environ['DISPLAY'] = ':0'

import cv2
import numpy as np
from ultralytics import YOLO, RTDETR

from ament_index_python.packages import get_package_share_directory

# ═══════════════════════════════════════════════════════════════════════════════
# 路径常量
# ═══════════════════════════════════════════════════════════════════════════════
MODEL_DIR = os.path.join(get_package_share_directory('vision_basics'), 'model')
_base = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.join(_base, '..')

# ═══════════════════════════════════════════════════════════════════════════════
# 超参数（可调）
# ═══════════════════════════════════════════════════════════════════════════════
YOLO_CONF = 0.1       # 初筛阈值：极低，宁错勿漏
RTDETR_CONF = 0.5     # 精检阈值：高，精确判定
EXPAND_RATIO = 0.1    # 候选区扩展比例


def load_image(path):
    """
    Step 2: 读取图片
    优先命令行参数，否则用默认测试图
    """
    img_path = path if path else f'{PROJ_DIR}/pictures/street_crowd.jpg'
    img = cv2.imread(img_path)
    if img is None:
        print(f'❌ 无法读取图片: {img_path}')
        sys.exit(1)
    print(f'图片: {os.path.basename(img_path)} ({img.shape[1]}×{img.shape[0]})')
    return img


def yolo_prescreen(model, img):
    """
    Step 3: YOLO 初筛（高召回）
    
    用极低置信度阈值扫描全图，返回所有"可能是目标"的区域。
    宁可多框 100 个候选项，也不漏掉 1 个真目标。
    
    Returns:
        list of [x1, y1, x2, y2] 候选边界框
    """
    results = model(img, conf=YOLO_CONF, verbose=False)
    boxes = results[0].boxes
    if boxes is None or len(boxes) == 0:
        return []
    return boxes.xyxy.tolist()


def expand_boxes(boxes, img_w, img_h):
    """
    Step 4: 边界框扩展
    
    每个候选框四边扩展 10%，防止 YOLO 的框过紧导致目标被截断。
    同时 clamp 到图像边界内。
    """
    expanded = []
    for box in boxes:
        x1, y1, x2, y2 = box
        bw, bh = x2 - x1, y2 - y1
        # 各边扩展 EXPAND_RATIO
        x1 = max(0, int(x1 - bw * EXPAND_RATIO))
        y1 = max(0, int(y1 - bh * EXPAND_RATIO))
        x2 = min(img_w, int(x2 + bw * EXPAND_RATIO))
        y2 = min(img_h, int(y2 + bh * EXPAND_RATIO))
        expanded.append([x1, y1, x2, y2])
    return expanded


def rtdetr_refine(model, img, candidates):
    """
    Step 5+6: RT-DETR 精检 + 坐标映射
    
    对每个候选区：
      1. 裁剪图像 → 送入 RT-DETR（高阈值）
      2. 局部检测坐标 → 映射回原图全局坐标
      3. 收集 class + confidence + bbox
    
    Returns:
        list of dict: {bbox: [x1,y1,x2,y2], class: str, conf: float}
    """
    final = []
    for box in candidates:
        x1, y1, x2, y2 = box
        crop = img[y1:y2, x1:x2]
        if crop.size == 0:
            continue

        results = model(crop, conf=RTDETR_CONF, verbose=False)
        for r_box in results[0].boxes:
            rx1, ry1, rx2, ry2 = r_box.xyxy[0].tolist()
            cls_id = int(r_box.cls[0])
            cls_name = model.names[cls_id]
            conf_val = float(r_box.conf[0])

            # 局部 → 全局坐标映射
            final.append({
                'bbox': [x1 + rx1, y1 + ry1, x1 + rx2, y1 + ry2],
                'class': cls_name,
                'conf': conf_val,
            })
    return final


def draw_results(img, detections):
    """
    Step 7a: 在图像上绘制检测框 + 标签
    
    颜色规则：
      绿色 (0,255,0)  → 正常检测
    """
    output = img.copy()
    for d in detections:
        x1, y1, x2, y2 = [int(v) for v in d['bbox']]
        label = f"{d['class']}: {d['conf']:.2f}"

        # 边界框（绿色）
        cv2.rectangle(output, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # 标签背景
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(output, (x1, y1 - th - 4), (x1 + tw, y1), (0, 255, 0), -1)

        # 标签文字（黑色）
        cv2.putText(output, label, (x1, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    return output


def main():
    """
    Step 0: 主入口
    
    7 步流水线：
      Load models → Read image → YOLO prescreen → Expand → RTDETR refine → Draw → Save/Show
    """
    # ── Step 1: 加载模型 ──
    yolo = YOLO(os.path.join(MODEL_DIR, 'yolov8s.pt'))
    rtdetr = RTDETR(os.path.join(MODEL_DIR, 'rtdetr-l.pt'))
    print(f'YOLOv8s  (初筛, conf={YOLO_CONF}) + RT-DETR-L (精检, conf={RTDETR_CONF})')
    print(f'模型大小: {os.path.getsize(os.path.join(MODEL_DIR, "yolov8s.pt"))/1e6:.1f}MB + '
          f'{os.path.getsize(os.path.join(MODEL_DIR, "rtdetr-l.pt"))/1e6:.1f}MB')

    # ── Step 2: 读取图片 ──
    img_path = sys.argv[1] if len(sys.argv) > 1 else None
    img = load_image(img_path)
    h, w = img.shape[:2]
    t_total = time.time()

    # ── Step 3: YOLO 初筛 ──
    candidates = yolo_prescreen(yolo, img)
    n_candidates = len(candidates)
    if n_candidates == 0:
        print('YOLO 初筛: 无可疑区域（场景可能太简单，尝试降低 conf 或换图）')
        return
    print(f'YOLO 初筛: {n_candidates} 个候选区域')

    # ── Step 4: 区域扩展 ──
    expanded = expand_boxes(candidates, w, h)

    # ── Step 5+6: RT-DETR 精检 ──
    detections = rtdetr_refine(rtdetr, img, expanded)
    n_final = len(detections)
    ms = (time.time() - t_total) * 1000

    # ── 结果汇总 ──
    print(f'RT-DETR 精检: {n_final} 个目标（从 {n_candidates} 个候选区中检出）')
    print(f'总耗时: {ms:.0f}ms')
    if detections:
        print('检测结果:')
        for d in detections:
            b = d['bbox']
            print(f'  [{d["class"]}] conf={d["conf"]:.2f}  '
                  f'box=({b[0]:.0f},{b[1]:.0f},{b[2]:.0f},{b[3]:.0f})')

    # ── Step 7: 绘制 + 保存 + 显示 ──
    output = draw_results(img, detections)

    out_path = os.path.join(os.path.dirname(__file__), 'hybrid_result.png')
    cv2.imwrite(out_path, output)
    print(f'\n已保存: {out_path}')

    cv2.namedWindow('Hybrid: YOLOv8s prescreen + RT-DETR refine', cv2.WINDOW_NORMAL)
    cv2.imshow('Hybrid: YOLOv8s prescreen + RT-DETR refine', output)
    print('窗口已打开，按任意键退出...')
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
