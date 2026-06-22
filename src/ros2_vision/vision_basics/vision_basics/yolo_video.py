#!/usr/bin/env python3
"""04-1 YOLO: 本地视频目标检测

用 OpenCV 读取视频文件, 逐帧 YOLOv8n 推理,
显示 FPS + 检测框。按 q 退出。

参考版使用外网下载的 fruit.mp4，
实践版接受命令行参数或默认用摄像头。
"""

import sys
import os
import cv2
from ultralytics import YOLO

MODEL = os.path.expanduser(
    '~/Music/spark_humble/src/spark_app/spark_yolov8/model/yolov8n.pt')

# 视频源: 命令行参数 > 默认摄像头
video_src = sys.argv[1] if len(sys.argv) > 1 else 0
cap = cv2.VideoCapture(video_src)

if not cap.isOpened():
    print(f"无法打开视频源: {video_src}")
    exit(1)

model = YOLO(MODEL)
print(f"模型: {MODEL} | 视频源: {video_src} | 按 q 退出")

cv2.namedWindow('YOLOv8 Video', cv2.WINDOW_NORMAL)
cv2.resizeWindow('YOLOv8 Video', 800, 600)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, conf=0.3, verbose=False)
    annotated = results[0].plot()

    fps = 1000.0 / results[0].speed['inference'] if results[0].speed else 0
    cv2.putText(annotated, f'FPS: {int(fps)}', (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    cv2.imshow('YOLOv8 Video', annotated)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
