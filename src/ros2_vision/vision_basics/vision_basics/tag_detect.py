#!/usr/bin/env python3
"""03-4 AprilTag/视觉标签: ArUco 标记检测与位姿估计

用 OpenCV 内置 cv2.aruco 演示视觉标签检测的完整流程:
  1. 生成 ArUco 标记图 → 2. 检测角点 + ID
  3. PnP 位姿估计 → 4. 画坐标轴验证

ArUco 与 AprilTag 原理相同（角点→PnP→6D位姿），
OpenCV 内置无需额外安装，适合教学演示。
"""

import cv2
import numpy as np

# --- D435 典型内参 (640×480) ---
FX, FY = 613.4, 612.2
CX, CY = 330.2, 240.6
camera_matrix = np.array([[FX, 0, CX], [0, FY, CY], [0, 0, 1]], dtype=np.float32)
dist_coeffs = np.zeros((5, 1))  # D435 出厂已校正，畸变为 0

# --- 1. 生成 ArUco 标记图 ---
DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
MARKER_SIZE = 400
marker_img = cv2.aruco.generateImageMarker(DICT, 0, MARKER_SIZE)

# 加白色边框（ArUco 需要边框来定位）
BORDER = 80
marker_img = cv2.copyMakeBorder(marker_img, BORDER, BORDER, BORDER, BORDER,
                                cv2.BORDER_CONSTANT, value=255)
display = cv2.cvtColor(marker_img, cv2.COLOR_GRAY2BGR)

# --- 2. 检测 ArUco ---
detector = cv2.aruco.ArucoDetector(DICT)
corners, ids, _ = detector.detectMarkers(marker_img)

if ids is None:
    print("❌ 未检测到标记")
    exit(1)

print(f"检测到 {len(ids)} 个标记: IDs = {ids.flatten()}")

# --- 3. 画角点 + ID ---
cv2.aruco.drawDetectedMarkers(display, corners, ids)

# 打印角点坐标
for i, c in enumerate(corners):
    pts = c[0]
    print(f"Tag {ids[i][0]}: 四角 = {pts}")

# --- 4. PnP 位姿估计 ---
# 标记实际尺寸 0.05m (5cm), 角点 3D 坐标 (以标记中心为原点)
TAG_SIZE = 0.05
obj_points = np.array([
    [-TAG_SIZE/2,  TAG_SIZE/2, 0],  # 左上
    [ TAG_SIZE/2,  TAG_SIZE/2, 0],  # 右上
    [ TAG_SIZE/2, -TAG_SIZE/2, 0],  # 右下
    [-TAG_SIZE/2, -TAG_SIZE/2, 0],  # 左下
], dtype=np.float32)

for c in corners:
    ret, rvec, tvec = cv2.solvePnP(obj_points, c, camera_matrix, dist_coeffs)

    # 画坐标轴 (红色=X, 绿色=Y, 蓝色=Z)
    cv2.drawFrameAxes(display, camera_matrix, dist_coeffs, rvec, tvec, 0.03)

    # 位姿信息
    R, _ = cv2.Rodrigues(rvec)
    print(f"\nPnP 位姿估计:")
    print(f"  平移 tvec (m): [{tvec[0][0]:.4f}, {tvec[1][0]:.4f}, {tvec[2][0]:.4f}]")
    print(f"  旋转矩阵 R:\n{R}")

cv2.imshow('ArUco Detection + Pose', display)
print("\n红色=X轴  绿色=Y轴  蓝色=Z轴（指向相机）")
print("按任意键退出")
cv2.waitKey(0)
cv2.destroyAllWindows()
