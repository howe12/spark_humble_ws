#!/usr/bin/env python3
"""03-4 AprilTag 实践: 用 apriltag 库检测 tag36h11 标记 + PnP 位姿估计

与 ArUco 的关键区别:
  - 检测 API: apriltag.Detector(families='tag36h11') → detect(gray)
  - 返回对象: Detection(tag_id, center, corners, hamming, decision_margin, homography)
  - AprilTag 鲁棒性更强(旋转/光照), 但需要 pip install apriltag
  - 无内置 draw 函数, 需手动用 cv2 画角点/ID/坐标轴

与 ArUco 相同:
  - 原理: 角点检测 → PnP → 6D 位姿
  - 流程: 生成标记图 → 检测 → 位姿估计 → 可视化
"""

import cv2
import numpy as np
import apriltag

# --- D435 典型内参 (640×480) ---
FX, FY = 613.4, 612.2
CX, CY = 330.2, 240.6
camera_matrix = np.array([[FX, 0, CX], [0, FY, CY], [0, 0, 1]], dtype=np.float32)
dist_coeffs = np.zeros((5, 1))

# --- 加载预生成的 AprilTag 标记图 (tag36h11, ID=0) ---
import sys, os
img_path = os.path.join(os.path.dirname(__file__),
                        '../pictures/apriltag36h11_id0.png')
img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

if img is None:
    # fallback: 用代码生成一个简单的测试图
    print("找不到预生成图片，用代码生成 ArUco 标记替代演示")
    dict_ = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
    img = cv2.aruco.generateImageMarker(dict_, 0, 400)
    img = cv2.copyMakeBorder(img, 80, 80, 80, 80,
                             cv2.BORDER_CONSTANT, value=255)

print(f"图像尺寸: {img.shape}")

# --- 1. 创建 AprilTag 检测器 ---
# 关键区别: 需要指定 families 参数 (如 'tag36h11', 'tag25h9', 'tag16h5')
detector = apriltag.Detector(
    apriltag.DetectorOptions(families='tag36h11')
)

# --- 2. 检测 AprilTag ---
result = detector.detect(img)
print(f"检测到 {len(result)} 个 AprilTag")

display = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

# --- 3. 遍历检测结果, 画角点 + ID + 位姿 ---
TAG_SIZE = 0.05  # 标记实际尺寸 5cm
obj_points = np.array([
    [-TAG_SIZE/2,  TAG_SIZE/2, 0],
    [ TAG_SIZE/2,  TAG_SIZE/2, 0],
    [ TAG_SIZE/2, -TAG_SIZE/2, 0],
    [-TAG_SIZE/2, -TAG_SIZE/2, 0],
], dtype=np.float32)

for r in result:
    # --- 3a. 基本信息 ---
    tag_id = r.tag_id
    center = r.center              # (cx, cy) — 浮点数
    corners = r.corners.astype(np.float32)  # 4×2, [左上, 右上, 右下, 左下]
    hamming = r.hamming            # 汉明距离 (0=完美)
    margin = r.decision_margin     # 决策裕度 (越大越确信)

    print(f"\nTag ID={tag_id}:")
    print(f"  中心: ({center[0]:.1f}, {center[1]:.1f})")
    print(f"  汉明距离: {hamming} (0=完美)")
    print(f"  决策裕度: {margin:.2f} (越大越确信)")

    # --- 3b. 画角点 + ID (手动画, apriltag 无内置 draw) ---
    for pt in corners:
        cv2.circle(display, tuple(pt.astype(int)), 5, (0, 255, 0), -1)
    # 连线
    for i in range(4):
        p1 = tuple(corners[i].astype(int))
        p2 = tuple(corners[(i+1) % 4].astype(int))
        cv2.line(display, p1, p2, (0, 255, 0), 2)

    # ID 文字
    cv2.putText(display, f'ID:{tag_id}',
                (int(center[0])-25, int(center[1])-15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # --- 3c. PnP 位姿估计 ---
    # AprilTag 返回 homography, 但 PnP 需要 2D 角点 + 3D obj_points
    ret, rvec, tvec = cv2.solvePnP(
        obj_points, corners, camera_matrix, dist_coeffs)

    if ret:
        # 画坐标轴 (红=X, 绿=Y, 蓝=Z)
        cv2.drawFrameAxes(display, camera_matrix, dist_coeffs,
                          rvec, tvec, 0.03)

        # 位姿信息
        R, _ = cv2.Rodrigues(rvec)
        dist = np.linalg.norm(tvec)
        print(f"  距离: {dist:.3f}m")
        print(f"  平移 tvec: [{tvec[0][0]:.4f}, {tvec[1][0]:.4f}, "
              f"{tvec[2][0]:.4f}]")

cv2.imshow('AprilTag Detection (apriltag library)', display)
print("\n绿色=角点连线  红色X/绿色Y/蓝色Z=坐标轴")
print("按任意键退出")
cv2.waitKey(0)
cv2.destroyAllWindows()
