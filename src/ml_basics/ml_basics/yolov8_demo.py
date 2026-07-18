#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLOv8 演示脚本 — Lesson 3.2 深度学习-YOLOv8配置课程

功能:
  - 演示 YOLOv8 安装、模型加载、图像推理全流程
  - 使用 ultralytics YOLO 官方包
  - 自动下载测试图片（或生成合成图片作为后备）
  - 将检测结果保存为 /tmp/yolov8_result.jpg
  - 打印检测到的目标数量、类别名称和置信度

设计思路:
  - 参考 doc_3.2 课程文档中的验证代码，扩展为独立可运行脚本
  - 使用 matplotlib Agg 后端，支持无图形界面的服务器环境
  - 自动处理模型首次下载 (yolov8n.pt ≈ 6.3MB)

环境要求:
  pip install ultralytics opencv-python matplotlib numpy
"""

import os
import sys
import urllib.request
import warnings

# ============================================================
# 0. 在导入 matplotlib 之前设置 Agg 后端 (无头模式)
# ============================================================
os.environ.setdefault('MPLBACKEND', 'Agg')
import matplotlib
matplotlib.use('Agg')  # 必须在 import pyplot 之前

import matplotlib.pyplot as plt
import numpy as np
import cv2


# ============================================================
# 辅助函数
# ============================================================

def ensure_test_image(save_path: str = '/tmp/yolov8_test_input.jpg') -> str:
    """
    获取测试图片: 优先从网络下载，失败则生成合成图片。

    Returns:
        str: 测试图片的路径
    """
    # 如果已经存在，直接返回
    if os.path.exists(save_path):
        print(f'[INFO] 使用已有测试图片: {save_path}')
        return save_path

    # 尝试从网络下载 (zidane.jpg — Ultralytics 官方测试图)
    test_urls = [
        'https://ultralytics.com/images/zidane.jpg',
        'https://raw.githubusercontent.com/ultralytics/yolov5/master/data/images/zidane.jpg',
        'https://raw.githubusercontent.com/ultralytics/assets/main/imgs/zidane.jpg',
    ]

    for url in test_urls:
        try:
            print(f'[INFO] 尝试下载测试图片: {url}')
            urllib.request.urlretrieve(url, save_path)
            print(f'[INFO] 测试图片已下载到: {save_path}')
            return save_path
        except Exception as e:
            print(f'[WARN] 下载失败 ({e}), 尝试下一个...')

    # 后备方案: 生成一张合成图片 (彩色几何图形)
    print('[INFO] 网络不可用, 生成合成测试图片...')
    img = _generate_synthetic_image()
    cv2.imwrite(save_path, img)
    print(f'[INFO] 合成图片已保存到: {save_path}')
    return save_path


def _generate_synthetic_image(size=(640, 480)) -> np.ndarray:
    """
    生成一张包含人/车/交通灯等常见物体的示意图片。
    使用彩色矩形和圆形模拟检测目标场景。
    """
    img = np.ones((size[1], size[0], 3), dtype=np.uint8) * 180  # 浅灰背景

    # 模拟 "人" — 红色矩形
    cv2.rectangle(img, (80, 60), (200, 420), (40, 40, 200), -1)
    cv2.putText(img, 'PERSON', (85, 250), cv2.FONT_HERSHEY_SIMPLEX,
                0.7, (255, 255, 255), 2)

    # 模拟 "车" — 蓝色矩形
    cv2.rectangle(img, (250, 180), (600, 420), (200, 80, 30), -1)
    cv2.putText(img, 'CAR', (370, 310), cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (255, 255, 255), 2)

    # 模拟 "交通灯" — 三个彩色圆
    cv2.rectangle(img, (560, 50), (620, 160), (60, 60, 60), -1)
    cv2.circle(img, (590, 75), 15, (0, 0, 255), -1)   # 红
    cv2.circle(img, (590, 105), 15, (0, 220, 220), -1)  # 黄
    cv2.circle(img, (590, 135), 15, (0, 255, 0), -1)   # 绿

    # 模拟 "瓶子" — 绿色矩形
    cv2.rectangle(img, (30, 200), (70, 400), (0, 180, 60), -1)
    cv2.putText(img, 'BOTTLE', (10, 300), cv2.FONT_HERSHEY_SIMPLEX,
                0.5, (255, 255, 255), 1)

    return img


def draw_results(image_bgr: np.ndarray, results, output_path: str):
    """
    使用 matplotlib 在检测结果图像上绘制边界框和标签，并保存。

    说明:
      - ultralytics 自带 result.plot() 可快速绘制，但本函数展示手动绘制过程
      - 利于教学理解: 坐标提取、类别映射、绘制逻辑

    Args:
        image_bgr: BGR 格式原始图像
        results:   YOLO model() 返回的 Results 对象列表
        output_path: 保存路径
    """
    result = results[0]
    boxes = result.boxes
    annotated = image_bgr.copy()

    if boxes is not None and len(boxes) > 0:
        for box in boxes:
            # 提取坐标 (xyxy 格式: x1, y1, x2, y2)
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            # 类别名称通过 model.names 字典获取
            class_name = result.names[cls_id]

            # 绘制边界框 (绿色)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # 绘制标签背景 + 文字
            label = f'{class_name} {conf:.2f}'
            (label_w, label_h), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(annotated,
                          (x1, y1 - label_h - baseline - 2),
                          (x1 + label_w, y1),
                          (0, 255, 0), -1)
            cv2.putText(annotated, label,
                        (x1, y1 - baseline),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

    # 转换为 RGB 供 matplotlib 显示
    annotated_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)

    # 使用 matplotlib 保存 (无头模式, 不弹出窗口)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].imshow(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))
    axes[0].set_title('Original Image')
    axes[0].axis('off')

    axes[1].imshow(annotated_rgb)
    axes[1].set_title(f'YOLOv8 Detection ({len(boxes)} objects)')
    axes[1].axis('off')

    plt.tight_layout()
    fig.savefig(output_path, dpi=100, bbox_inches='tight')
    plt.close(fig)
    print(f'[INFO] 检测结果已保存到: {output_path}')


def check_dependencies() -> bool:
    """
    检查 ultralytics 是否已安装。未安装时给出安装指引。

    Returns:
        bool: 依赖满足返回 True
    """
    try:
        import ultralytics
        print(f'[INFO] ultralytics 已安装, 版本: {ultralytics.__version__}')
        return True
    except ImportError:
        print('=' * 60)
        print('[ERROR] 未找到 ultralytics 包!')
        print('请先安装:')
        print('  pip install ultralytics')
        print('')
        print('如果网络较慢, 可指定国内镜像:')
        print('  pip install ultralytics -i https://pypi.tuna.tsinghua.edu.cn/simple')
        print('=' * 60)
        return False


# ============================================================
# 主流程
# ============================================================

def main():
    """YOLOv8 演示主入口"""

    # --- 0. 环境准备 ---
    # 抑制 matplotlib GUI 警告
    warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

    print('=' * 60)
    print('  YOLOv8 演示脚本 — Lesson 3.2')
    print('  深度学习-YOLOv8 配置课程')
    print('=' * 60)
    print()

    # --- 1. 依赖检查 ---
    if not check_dependencies():
        sys.exit(1)

    from ultralytics import YOLO

    # --- 2. 获取测试图片 ---
    test_image = ensure_test_image('/tmp/yolov8_test_input.jpg')

    # --- 3. 加载模型 ---
    # yolov8n.pt: nano 版本, 约 6.3MB, 适合 CPU 推理
    # 首次运行会自动从 ultralytics 服务器下载
    print(f'\n[STEP 1] 加载 YOLOv8n 模型...')
    model = YOLO('yolov8n.pt')
    print(f'[INFO] 模型加载成功!')
    print(f'  - 模型路径: {model.model_name if hasattr(model, "model_name") else "yolov8n.pt"}')
    print(f'  - 类别数量: {len(model.names)} 类')
    print(f'  - 设备类型: {"cuda" if model.device.type == "cuda" else "cpu"}')

    # --- 4. 读取图片并推理 ---
    print(f'\n[STEP 2] 读取图片并执行推理...')
    image = cv2.imread(test_image)
    if image is None:
        print(f'[ERROR] 无法读取图片: {test_image}')
        sys.exit(1)
    print(f'  - 图片尺寸: {image.shape[1]}x{image.shape[0]}')

    # 执行推理 (verbose=False 关闭详细输出)
    results = model(image, verbose=False)

    # --- 5. 输出检测结果 ---
    print(f'\n[STEP 3] 检测结果:')
    result = results[0]
    boxes = result.boxes

    if boxes is not None and len(boxes) > 0:
        print(f'  ✓ 检测到 {len(boxes)} 个目标:')
        # 按置信度降序排列
        confs = boxes.conf.cpu().numpy() if hasattr(boxes.conf, 'cpu') else boxes.conf
        cls_ids = boxes.cls.cpu().numpy() if hasattr(boxes.cls, 'cpu') else boxes.cls
        # 获取排序索引
        sort_idx = np.argsort(-confs)
        for i, idx in enumerate(sort_idx):
            cls_id = int(cls_ids[idx])
            conf = float(confs[idx])
            name = result.names[cls_id]
            x1, y1, x2, y2 = boxes.xyxy[idx].tolist()
            print(f'  [{i+1:2d}] {name:<15s}  置信度: {conf:.3f}  '
                  f'框: ({int(x1)},{int(y1)})-({int(x2)},{int(y2)})')
    else:
        print('  ✗ 未检测到任何目标')

    # --- 6. 绘制并保存结果 ---
    print(f'\n[STEP 4] 绘制检测框并保存结果...')
    draw_results(image, results, '/tmp/yolov8_result.jpg')

    # --- 7. 课程要点总结 ---
    print(f'\n' + '=' * 60)
    print('  📚 课程要点总结')
    print('=' * 60)
    print(f"""
  1. YOLOv8n 中的 "n" 代表 nano (轻量版)
     其他后缀: n(nano), s(small), m(medium), l(large), x(xlarge)
     数字越大模型越大, 精度越高, 但推理速度越慢

  2. CPU 推理推荐 nano/small 模型:
     实训机器人 (Scorpio) 使用 CPU 推理, nano 模型仅 6.3MB
     在 CPU 上可达 5-10 FPS, 满足实时检测需求

  3. 模型首次加载:
     YOLO('yolov8n.pt') 会从 ultralytics 仓库自动下载模型
     也可手动下载: wget https://github.com/ultralytics/assets/releases/
                      download/v8.2.0/yolov8n.pt -O ~/.cache/ultralytics/yolov8n.pt

  4. verbose=False 的作用:
     抑制每个检测框的详细日志输出, 仅保留最终检测结果

  5. 结果保存:
     检测结果图像: /tmp/yolov8_result.jpg
     (ROS 实战中通过 cv_bridge 发布为 sensor_msgs/Image)
""")
    print('=' * 60)
    print('  演示完成! ✓')
    print('=' * 60)


if __name__ == '__main__':
    main()
