#!/usr/bin/env python3
"""
YOLOv8 姿态关键点动作分析

基于 COCO 17 关键点实现三种分析：
  1. 举手检测 — 手腕 y < 肩膀 y
  2. 手肘角度 — 肩-肘-腕三点夹角
  3. 深蹲计数 — 髋-膝-踝夹角 + 状态机

用法：
    python3 pose_actions.py          # 默认摄像头 0
    python3 pose_actions.py 0        # 指定摄像头
    python3 pose_actions.py vid.mp4  # 视频文件

按 q 退出，按 r 重置深蹲计数。
"""

import math
import sys
import cv2
import numpy as np
from ultralytics import YOLO


MODEL = 'yolov8n-pose.pt'

# ── COCO 17 关键点索引 ──
NOSE, L_EYE, R_EYE, L_EAR, R_EAR = 0, 1, 2, 3, 4
L_SHOULDER, R_SHOULDER = 5, 6
L_ELBOW, R_ELBOW = 7, 8
L_WRIST, R_WRIST = 9, 10
L_HIP, R_HIP = 11, 12
L_KNEE, R_KNEE = 13, 14
L_ANKLE, R_ANKLE = 15, 16


def safe_angle(a, b, c) -> float:
    """三点夹角 ∠abc（度）。出错返回 0。"""
    try:
        ba = a - b
        bc = c - b
        cos = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-9)
        cos = np.clip(cos, -1.0, 1.0)
        return math.degrees(math.acos(cos))
    except Exception:
        return 0.0


def check_raise_hand(kps, conf, idx_wrist, idx_shoulder):
    """手腕 y < 肩膀 y 判定举手"""
    if conf[idx_wrist] > 0.5 and conf[idx_shoulder] > 0.5:
        return kps[idx_wrist][1] < kps[idx_shoulder][1]
    return False


def main():
    model = YOLO(MODEL)

    arg = sys.argv[1] if len(sys.argv) > 1 else '0'
    src = int(arg) if arg.isdigit() else arg
    cap = cv2.VideoCapture(src)
    if src == 0 or src == 1:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("无法打开视频源")
        return

    # 深蹲状态机
    squat_state = 'standing'
    squat_count = 0

    print("动作分析已启动 | q=退出 r=重置计数")
    print("  左上角：举手状态")
    print("  右上角：深蹲计数")
    print("  手肘角度：右键>130°=伸直，<80°=弯曲")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame, conf=0.4, verbose=False)
        r = results[0]

        if r.keypoints is not None and r.keypoints.xy.shape[0] > 0:
            kps = r.keypoints.xy[0].cpu().numpy()  # (17, 2)
            conf = r.keypoints.conf[0].cpu().numpy()  # (17,)

            # ── 1. 举手检测 ──
            l_raise = check_raise_hand(kps, conf, L_WRIST, L_SHOULDER)
            r_raise = check_raise_hand(kps, conf, R_WRIST, R_SHOULDER)
            if l_raise and r_raise:
                hand_status = '双手举起'
            elif l_raise:
                hand_status = '左手举起'
            elif r_raise:
                hand_status = '右手举起'
            else:
                hand_status = '未举手'

            # ── 2. 左臂角度 ──
            l_angle = safe_angle(kps[L_SHOULDER], kps[L_ELBOW], kps[L_WRIST])
            r_angle = safe_angle(kps[R_SHOULDER], kps[R_ELBOW], kps[R_WRIST])

            # ── 3. 深蹲计数 ──
            l_knee_angle = safe_angle(kps[L_HIP], kps[L_KNEE], kps[L_ANKLE])
            r_knee_angle = safe_angle(kps[R_HIP], kps[R_KNEE], kps[R_ANKLE])
            knee_angle = (l_knee_angle + r_knee_angle) / 2

            if squat_state == 'standing' and knee_angle < 110:
                squat_state = 'squatting'
            elif squat_state == 'squatting' and knee_angle > 150:
                squat_state = 'standing'
                squat_count += 1

        else:
            hand_status = '(无人)'
            l_angle = r_angle = 0.0
            knee_angle = 180.0

        # ── 绘制 ──
        annotated = r.plot()

        # 左上角：举手状态
        cv2.putText(annotated, hand_status, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)

        # 右上角：深蹲计数
        cv2.putText(annotated, f'Squat: {squat_count}', (annotated.shape[1] - 220, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        # 左臂角度
        if l_angle > 0:
            cv2.putText(annotated, f'L:{l_angle:.0f}d', (10, 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)
        # 右臂角度
        if r_angle > 0:
            cv2.putText(annotated, f'R:{r_angle:.0f}d', (10, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)
        # 膝盖角度
        cv2.putText(annotated, f'Knee:{knee_angle:.0f}d', (10, 115),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 255), 2)

        cv2.imshow('动作分析 — q退出 r重置', annotated)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            squat_count = 0
            squat_state = 'standing'
            print("深蹲计数已重置")

    cap.release()
    cv2.destroyAllWindows()
    print(f"已退出。最终深蹲计数: {squat_count}")


if __name__ == '__main__':
    main()
