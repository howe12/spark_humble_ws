#!/usr/bin/env python3
"""04-3 YOLO姿态识别: 本地图片关键点提取

读取图片 → YOLOv8n-pose 推理 → 打印每个人 17 个关键点的坐标和置信度。
与 04-1 目标检测的区别: 模型换 -pose, 输出含 keypoints。
"""
import os
import sys
import cv2
from ament_index_python.packages import get_package_share_directory
from ultralytics import YOLO

# ── 模型 ──
MODEL_PATH = os.path.join(
    get_package_share_directory('vision_basics'), 'model', 'yolov8n-pose.pt')
model = YOLO(MODEL_PATH)
print(f'模型: {MODEL_PATH}')

# ── 图片 ──
base = os.path.dirname(os.path.abspath(__file__))
img_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(base, '..', 'pictures', 'lena.png')
img = cv2.imread(img_path)
print(f'图片: {os.path.basename(img_path)} ({img.shape[1]}×{img.shape[0]})')

# ── 推理 ──
results = model(img, conf=0.3, verbose=False)
r = results[0]

# ── 关键点索引 ──
KEYPOINT_NAMES = {
    0: "鼻子",  1: "左眼",  2: "右眼",
    3: "左耳",  4: "右耳",
    5: "左肩",  6: "右肩",
    7: "左肘",  8: "右肘",
    9: "左腕", 10: "右腕",
   11: "左髋", 12: "右髋",
   13: "左膝", 14: "右膝",
   15: "左踝", 16: "右踝",
}

keypoints = r.keypoints
if keypoints is not None:
    n_people = keypoints.xy.shape[0]
    print(f'\n检测到 {n_people} 个人:')
    for p in range(n_people):
        print(f'\n── 人 {p+1} ──')
        kp = keypoints.xy[p]      # (17, 2)
        conf = keypoints.conf[p]  # (17,)
        for i in range(17):
            name = KEYPOINT_NAMES.get(i, f'kp{i}')
            x, y = int(kp[i][0]), int(kp[i][1])
            c = float(conf[i])
            bar = '█' * int(c * 10) + '░' * (10 - int(c * 10))
            print(f'  {i:2d} {name:4s} ({x:4d},{y:4d}) 置信度 {c:.2f} {bar}')
else:
    print('未检测到任何人')

# ── 可视化 ──
annotated = r.plot()
cv2.imshow('YOLOv8-Pose Image', annotated)
print('\n按任意键关闭窗口')
cv2.waitKey(0)
cv2.destroyAllWindows()
