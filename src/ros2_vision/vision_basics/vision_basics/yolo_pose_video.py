#!/usr/bin/env python3
"""04-3 YOLO姿态识别: 本地视频姿态估计

默认使用 pictures/dance.mp4，传参可覆盖。
按 q 退出，按 +/- 调整跳帧数。

FPS 优化策略:
  - imgsz=320（默认640→320，速度提升约4x，精度损失小）
  - frame_skip=2（每2帧推理1次，其他帧复用结果，有效FPS翻倍）
"""
import os
import sys
import time
import cv2
from ament_index_python.packages import get_package_share_directory
from ultralytics import YOLO

# ── 可调参数 ──
IMGSZ = 320          # 推理分辨率（越小越快，320 是精度/速度平衡点）
CONF = 0.3           # 置信度阈值
FRAME_SKIP = 2       # 跳帧数：每隔 N 帧推理一次
HALF = True          # FP16 半精度（仅 GPU 有效，CPU 自动忽略）

# ── 模型 ──
MODEL_PATH = os.path.join(
    get_package_share_directory('vision_basics'), 'model', 'yolov8n-pose.pt')
model = YOLO(MODEL_PATH)
print(f'模型: {MODEL_PATH}')
print(f'设置: imgsz={IMGSZ}, conf={CONF}, frame_skip={FRAME_SKIP}, half={HALF}')

# ── 视频源 ──
# 默认本地视频文件，传参可覆盖
DEFAULT_VIDEO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'pictures', 'dance.mp4')
video_src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_VIDEO
cap = cv2.VideoCapture(video_src)
if not cap.isOpened():
    print(f'无法打开视频源: {video_src}')
    exit(1)
print(f'视频源: {video_src} | 按 q 退出 | +/- 调跳帧')

cv2.namedWindow('YOLOv8 Pose', cv2.WINDOW_NORMAL)
cv2.resizeWindow('YOLOv8 Pose', 800, 600)

last_result = None   # 缓存上次推理结果
frame_count = 0
fps_window = []      # 滑动窗口计算实际 FPS
t_start = time.time()

while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame_count += 1

    # ── 跳帧策略：每隔 FRAME_SKIP 帧才推理 ──
    if frame_count % FRAME_SKIP == 0:
        t0 = time.time()
        results = model(frame, imgsz=IMGSZ, conf=CONF, half=HALF, verbose=False)
        t_infer = time.time() - t0
        last_result = results[0]
        inference_ms = t_infer * 1000
    else:
        inference_ms = 0  # 复用缓存，无推理耗时

    # 绘制（始终用最新结果）
    if last_result is not None:
        annotated = last_result.plot()

        # ── 实际 FPS（含绘制）──
        t_now = time.time()
        fps_window.append(t_now)
        fps_window = [t for t in fps_window if t > t_now - 2.0]  # 2 秒滑动窗口
        real_fps = len(fps_window) / 2.0

        # 显示信息
        info_lines = [
            f'Inference: {inference_ms:.0f}ms',
            f'Real FPS: {real_fps:.0f}',
            f'Skip: 1/{FRAME_SKIP}  (+/- to adjust)',
        ]
        for j, txt in enumerate(info_lines):
            cv2.putText(annotated, txt, (10, 30 + j * 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    else:
        annotated = frame

    cv2.imshow('YOLOv8 Pose', annotated)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('+') or key == ord('='):
        FRAME_SKIP = max(1, FRAME_SKIP - 1)
        print(f'frame_skip -> {FRAME_SKIP}')
    elif key == ord('-'):
        FRAME_SKIP = min(10, FRAME_SKIP + 1)
        print(f'frame_skip -> {FRAME_SKIP}')

cap.release()
cv2.destroyAllWindows()
elapsed = time.time() - t_start
print(f'完成: {frame_count} 帧 / {elapsed:.1f}s = {frame_count/elapsed:.1f} FPS 平均')
