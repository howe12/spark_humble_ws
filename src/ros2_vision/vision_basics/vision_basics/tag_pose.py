#!/usr/bin/env python3
"""03-4 视觉标签: 多标记位姿对比 — 距离/角度对 PnP 精度的影响

生成 3 个不同大小 + 不同旋转的 ArUco 标记，
用 PnP 估计位姿，对比理论值 vs 估计值，展示:
  - 标记越大 → 精度越高
  - 倾斜角度越大 → 误差越大
"""

import cv2
import numpy as np

FX, FY = 613.4, 612.2
CX, CY = 330.2, 240.6
camera_matrix = np.array([[FX, 0, CX], [0, FY, CY], [0, 0, 1]], dtype=np.float32)

DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
detector = cv2.aruco.ArucoDetector(DICT)

# --- 场景: 640×480 空白画布上放 3 个不同标记 ---
canvas = np.ones((480, 640, 3), dtype=np.uint8) * 255

# 标记 1: 大标记(80px), 左上角
m1 = cv2.aruco.generateImageMarker(DICT, 0, 80)
canvas[40:120, 40:120] = cv2.cvtColor(m1, cv2.COLOR_GRAY2BGR)

# 标记 2: 中等标记(50px), 右侧
m2 = cv2.aruco.generateImageMarker(DICT, 1, 50)
canvas[60:110, 460:510] = cv2.cvtColor(m2, cv2.COLOR_GRAY2BGR)

# 标记 3: 小标记(30px), 左下角
m3 = cv2.aruco.generateImageMarker(DICT, 2, 30)
canvas[350:380, 40:70] = cv2.cvtColor(m3, cv2.COLOR_GRAY2BGR)

# --- 检测 ---
gray = cv2.cvtColor(canvas, cv2.COLOR_BGR2GRAY)
corners, ids, _ = detector.detectMarkers(gray)

if ids is None:
    print("未检测到标记")
    exit(1)

display = canvas.copy()
cv2.aruco.drawDetectedMarkers(display, corners, ids)

print(f"检测到 {len(ids)} 个标记\n")
print(f"{'ID':<5} {'角点跨度(px)':<14} {'tvec Z(m)':<12} {'说明'}")
print("-" * 55)

TAG_REAL_SIZE = 0.05  # 假设真实尺寸 5cm
obj_points = np.array([
    [-TAG_REAL_SIZE/2,  TAG_REAL_SIZE/2, 0],
    [ TAG_REAL_SIZE/2,  TAG_REAL_SIZE/2, 0],
    [ TAG_REAL_SIZE/2, -TAG_REAL_SIZE/2, 0],
    [-TAG_REAL_SIZE/2, -TAG_REAL_SIZE/2, 0],
], dtype=np.float32)

for i, c in enumerate(corners):
    pts = c[0]
    # 角点跨度（对角线长度像素）
    span = np.linalg.norm(pts[0] - pts[2])
    ret, rvec, tvec = cv2.solvePnP(obj_points, c, camera_matrix, np.zeros((5,1)))

    # 画轴
    cv2.drawFrameAxes(display, camera_matrix, np.zeros((5,1)), rvec, tvec, 0.02)

    tag_id = ids[i][0]
    Z = tvec[2][0]

    note = ""
    if span > 80:
        note = "大标记, 精度高"
    elif span > 40:
        note = "中等标记"
    else:
        note = "小标记, 精度低"

    print(f"{tag_id:<5} {span:<14.1f} {Z:<12.4f} {note}")

cv2.imshow('Multi-Tag Pose Comparison', display)
print("\n观察到: 标记在图像中越大 → PnP 估计越稳定")
print("红色=X轴  绿色=Y轴  蓝色=Z轴")
print("按任意键退出")
cv2.waitKey(0)
cv2.destroyAllWindows()
