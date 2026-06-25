#!/usr/bin/env python3
"""03-4 AprilTag vs ArUco 对比: 同一标记分别用两种库检测, 并排对比

演示 AprilTag (apriltag 库) 和 ArUco (cv2.aruco) 的 API 差异:
  - 检测 API 不同
  - 返回对象结构不同
  - 可视化方式不同
  - 位姿估计流程相同 (PnP)

用 ArUco 标记图做测试 (两者都能检测到一定程度的矩形图案)。
"""

import cv2
import numpy as np
import apriltag
import sys, os

# --- D435 典型内参 ---
FX, FY = 613.4, 612.2
CX, CY = 330.2, 240.6
camera_matrix = np.array([[FX, 0, CX], [0, FY, CY], [0, 0, 1]], dtype=np.float32)
dist_coeffs = np.zeros((5, 1))

# --- 生成 ArUco 标记图 (两种检测器都能看到) ---
DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
MARKER_SIZE = 400
BORDER = 80
marker_img = cv2.aruco.generateImageMarker(DICT, 0, MARKER_SIZE)
marker_img = cv2.copyMakeBorder(marker_img, BORDER, BORDER, BORDER, BORDER,
                                cv2.BORDER_CONSTANT, value=255)

# --- 1. ArUco 检测 ---
aruco_detector = cv2.aruco.ArucoDetector(DICT)
aruco_corners, aruco_ids, _ = aruco_detector.detectMarkers(marker_img)

# --- 2. AprilTag 检测 ---
apriltag_detector = apriltag.Detector(
    apriltag.DetectorOptions(families='tag36h11'))
apriltag_result = apriltag_detector.detect(marker_img)

# --- 3. 构建对比显示 ---
display_aruco = cv2.cvtColor(marker_img, cv2.COLOR_GRAY2BGR)
display_apriltag = cv2.cvtColor(marker_img, cv2.COLOR_GRAY2BGR)

TAG_SIZE = 0.05
obj_points = np.array([
    [-TAG_SIZE/2,  TAG_SIZE/2, 0],
    [ TAG_SIZE/2,  TAG_SIZE/2, 0],
    [ TAG_SIZE/2, -TAG_SIZE/2, 0],
    [-TAG_SIZE/2, -TAG_SIZE/2, 0],
], dtype=np.float32)

# --- ArUco 可视化 ---
if aruco_ids is not None:
    cv2.aruco.drawDetectedMarkers(display_aruco, aruco_corners, aruco_ids)
    for i, c in enumerate(aruco_corners):
        ret, rvec, tvec = cv2.solvePnP(
            obj_points, c, camera_matrix, dist_coeffs)
        if ret:
            cv2.drawFrameAxes(display_aruco, camera_matrix, dist_coeffs,
                              rvec, tvec, 0.03)
    cv2.putText(display_aruco,
                f'ArUco: {len(aruco_ids)} tags',
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
else:
    cv2.putText(display_aruco, 'ArUco: 0 tags (未检测到)',
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

# --- AprilTag 可视化 ---
if apriltag_result:
    for r in apriltag_result:
        corners = r.corners.astype(np.float32)
        for pt in corners:
            cv2.circle(display_apriltag, tuple(pt.astype(int)), 5, (0, 255, 0), -1)
        for i in range(4):
            p1 = tuple(corners[i].astype(int))
            p2 = tuple(corners[(i+1)%4].astype(int))
            cv2.line(display_apriltag, p1, p2, (0, 255, 0), 2)
        cv2.putText(display_apriltag, f'ID:{r.tag_id}',
                    (int(r.center[0])-25, int(r.center[1])-15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        ret, rvec, tvec = cv2.solvePnP(
            obj_points, corners, camera_matrix, dist_coeffs)
        if ret:
            cv2.drawFrameAxes(display_apriltag, camera_matrix, dist_coeffs,
                              rvec, tvec, 0.03)
    cv2.putText(display_apriltag,
                f'AprilTag: {len(apriltag_result)} tags',
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
else:
    cv2.putText(display_apriltag, 'AprilTag: 0 tags (ArUco标记不被识别)',
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

# --- 并排显示 ---
combined = np.hstack([display_aruco, display_apriltag])
cv2.putText(combined, 'vs', (display_aruco.shape[1]-15, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

cv2.imshow('AprilTag vs ArUco Comparison', combined)
print("左侧: ArUco (cv2.aruco)    右侧: AprilTag (apriltag 库)")
print("注意: ArUco 标记不被 AprilTag 检测器识别 (标记族不同)")
print("按任意键退出")
cv2.waitKey(0)
cv2.destroyAllWindows()
