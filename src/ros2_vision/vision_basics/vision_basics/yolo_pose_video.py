#!/usr/bin/env python3
"""04-3 YOLO姿态识别: 摄像头实时姿态估计

打开摄像头(默认 /dev/video0) → YOLOv8n-pose 逐帧推理 → 绘制火柴人 + FPS。
按 q 退出。第一个参数可以传视频文件路径。
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

# ── 视频源 ──
video_src = sys.argv[1] if len(sys.argv) > 1 else 0
cap = cv2.VideoCapture(video_src)
if not cap.isOpened():
    print(f'无法打开视频源: {video_src}')
    exit(1)
print(f'视频源: {video_src} | 按 q 退出')

cv2.namedWindow('YOLOv8 Pose', cv2.WINDOW_NORMAL)
cv2.resizeWindow('YOLOv8 Pose', 800, 600)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, conf=0.3, verbose=False)
    annotated = results[0].plot()

    # ── FPS ──
    speed = results[0].speed
    if speed and 'inference' in speed:
        fps = 1000.0 / speed['inference']
        cv2.putText(annotated, f'FPS: {int(fps)}', (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    cv2.imshow('YOLOv8 Pose', annotated)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
