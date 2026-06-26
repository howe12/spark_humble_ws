#!/usr/bin/env python3
"""04-3 YOLO姿态识别: 关键点解析 — 举手检测 + 手臂角度

从摄像头读取帧 → YOLOv8n-pose 推理 → 判断是否举手 + 计算手臂角度。
这是「从检测到应用」的关键一步：把关键点坐标变成语义动作。
"""
import os
import sys
import cv2
import math
import numpy as np
from ament_index_python.packages import get_package_share_directory
from ultralytics import YOLO

# ── 模型 ──
MODEL_PATH = os.path.join(
    get_package_share_directory('vision_basics'), 'model', 'yolov8n-pose.pt')
model = YOLO(MODEL_PATH)

# ── COCO 关键点索引 ──
LEFT_SHOULDER  = 5
RIGHT_SHOULDER = 6
LEFT_ELBOW     = 7
RIGHT_ELBOW    = 8
LEFT_WRIST     = 9
RIGHT_WRIST    = 10

def calc_angle(a, b, c):
    """计算三点夹角 ∠ABC (a=肩, b=肘, c=腕)"""
    v1 = a - b
    v2 = c - b
    cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
    return math.degrees(math.acos(np.clip(cos_angle, -1, 1)))

def analyze_pose(keypoints, person_idx=0):
    """分析单个人体姿态: 举手方向 + 手臂角度"""
    if keypoints is None or keypoints.xy.shape[0] == 0:
        return None
    kp = keypoints.xy[person_idx]
    conf = keypoints.conf[person_idx]

    result = []

    # ── 左臂 ──
    if all(conf[i] > 0.3 for i in [LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST]):
        l_angle = calc_angle(kp[LEFT_SHOULDER], kp[LEFT_ELBOW], kp[LEFT_WRIST])
        l_wrist_y = kp[LEFT_WRIST][1]
        l_shoulder_y = kp[LEFT_SHOULDER][1]
        result.append(f'左臂: {l_angle:.0f}°')
        if l_wrist_y < l_shoulder_y and l_angle > 120:
            result.append('  ⬆ 左手举起!')

    # ── 右臂 ──
    if all(conf[i] > 0.3 for i in [RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST]):
        r_angle = calc_angle(kp[RIGHT_SHOULDER], kp[RIGHT_ELBOW], kp[RIGHT_WRIST])
        r_wrist_y = kp[RIGHT_WRIST][1]
        r_shoulder_y = kp[RIGHT_SHOULDER][1]
        result.append(f'右臂: {r_angle:.0f}°')
        if r_wrist_y < r_shoulder_y and r_angle > 120:
            result.append('  ⬆ 右手举起!')

    return '\n'.join(result) if result else '未检测到完整手臂'

# ── 主循环 ──
video_src = sys.argv[1] if len(sys.argv) > 1 else 0
cap = cv2.VideoCapture(video_src)
print(f'视频源: {video_src} | 举手检测中 | 按 q 退出')
print(f'模型: {MODEL_PATH}')

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, conf=0.3, verbose=False)
    annotated = results[0].plot()

    # ── 分析第一个人的姿态 ──
    analysis = analyze_pose(results[0].keypoints, 0)
    if analysis:
        # 多行文字叠加
        y_offset = 60
        for line in analysis.split('\n'):
            cv2.putText(annotated, line, (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            y_offset += 25

    cv2.imshow('Pose Action Analysis', annotated)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
