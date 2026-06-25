#!/usr/bin/env python3
"""
YOLO-World 开放词汇目标检测

最大的不同：不用重新训练，只需告诉模型"我要找什么"。
set_classes(['person', 'red cup', 'laptop']) → 只检测这些类别。

用法：
    python3 yolo_world_detect.py                      # lena.png, COCO默认类
    python3 yolo_world_detect.py "red cup,laptop"     # 自定义类别
    python3 yolo_world_detect.py "dog,cat" image.jpg  # 自定义+图片

模型：yolov8s-world.pt（首次运行自动下载，约 75MB）
"""

import os, sys
from ament_index_python.packages import get_package_share_directory
import cv2
from ultralytics import YOLOWorld

MODEL_DIR = os.path.join(get_package_share_directory('spark_yolov8'), 'model')
PROJ_DIR = os.path.expanduser('~/Music/spark_humble/src/ros2_vision/vision_basics')


def get_model(name):
    local = os.path.join(MODEL_DIR, name)
    return local if os.path.exists(local) else name


def main():
    model_path = get_model('yolov8s-world.pt')
    print(f'模型: {model_path}')
    model = YOLOWorld(model_path)
    print(f'任务: {model.task}')

    # ── 解析参数 ──
    args = sys.argv[1:]
    custom_classes = None
    img_arg = None

    for a in args:
        if ',' in a and not a.endswith(('.jpg', '.png', '.jpeg')):
            custom_classes = [c.strip() for c in a.split(',')]
        elif a.endswith(('.jpg', '.png', '.jpeg')):
            img_arg = a

    img_path = img_arg or f'{PROJ_DIR}/pictures/lena.png'
    img = cv2.imread(img_path)
    print(f'图片: {os.path.basename(img_path)} ({img.shape[1]}×{img.shape[0]})')

    # ── 设置检测类别 ──
    if custom_classes:
        model.set_classes(custom_classes)
        print(f'检测类别: {custom_classes}')
    else:
        print('检测类别: COCO 默认 80 类')

    # ── 推理 ──
    results = model(img, conf=0.3, verbose=False)
    r = results[0]

    if r.boxes is not None and len(r.boxes) > 0:
        boxes = r.boxes
        for i in range(len(boxes)):
            cls_id = int(boxes.cls[i])
            name = model.names[cls_id]
            conf = boxes.conf[i]
            x1, y1, x2, y2 = boxes.xyxy[i]
            print(f'  {name:<20} conf={conf:.2f}  box=({x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f})')
    else:
        print('  未检测到目标')

    annotated = r.plot()
    cv2.imshow('YOLO-World — 开放词汇检测', annotated)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
