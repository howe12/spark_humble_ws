#!/usr/bin/env python3
"""
YOLOv8 本地摄像头/视频肢体识别

用法：
    python3 yolo_pose.py           # 默认摄像头 0
    python3 yolo_pose.py 0         # 摄像头
    python3 yolo_pose.py dance.mp4 # 视频文件

模型：yolov8n-pose.pt（首次运行自动下载）
"""

import sys
import cv2
from ultralytics import YOLO


# ── 模型路径：优先本地，其次自动下载 ──
MODEL_NAME = 'yolov8n-pose.pt'
MODEL = MODEL_NAME  # ultralytics 会自动从 hub 下载


def main():
    model = YOLO(MODEL)
    print(f"模型已加载: {MODEL} (COCO 17 关键点)")

    # ── 打开摄像头或视频文件 ──
    arg = sys.argv[1] if len(sys.argv) > 1 else '0'
    if arg.isdigit():
        src = int(arg)
        cap = cv2.VideoCapture(src)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        print(f"摄像头 {src} 已打开 (640×480)")
    else:
        cap = cv2.VideoCapture(arg)
        print(f"视频文件已加载: {arg}")

    if not cap.isOpened():
        print("无法打开视频源")
        return

    # COCO 骨架连接（用于自绘火柴人，比 plot() 更灵活）
    SKELETON = [
        (0, 1), (0, 2), (1, 3), (2, 4),       # 头
        (5, 6), (5, 11), (6, 12), (11, 12),    # 躯干
        (5, 7), (7, 9),                         # 左臂
        (6, 8), (8, 10),                        # 右臂
        (11, 13), (13, 15),                     # 左腿
        (12, 14), (14, 16),                     # 右腿
    ]

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # YOLO-Pose 推理
        results = model(frame, conf=0.4, verbose=False)

        # 绘制结果
        annotated = results[0].plot()
        cv2.imshow('YOLOv8 Pose — 按 q 退出', annotated)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("已退出")


if __name__ == '__main__':
    main()
