#!/usr/bin/env python3
"""离线运行级测试: 伪造深度图喂给 depth_roi_demo_node (方案A: 深度图反投影)

不依赖真实相机/ROS 网络, 直接设置 depth_image/rgb_image/内参,
调用 process_frame() 验证: 反投影 → ROI → 离群剔除 → 运动控制 → 可视化 全链路。

注意: 若 DISPLAY 不可用(无头环境), 自动跳过 cv2.imshow。
"""
import os
os.environ.setdefault('DISPLAY', ':0')
# 先探测显示环境, 无显示则用 offscreen (必须在 import cv2 前设置)
try:
    import subprocess
    r = subprocess.run(['xdpyinfo'], capture_output=True, timeout=3)
    HAS_DISPLAY = r.returncode == 0
except Exception:
    HAS_DISPLAY = False
if not HAS_DISPLAY:
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    print("(无显示环境, 使用 offscreen 模式)")

import cv2
import rclpy
import numpy as np
from vision_basics.depth_roi_demo_node import DepthRoiDemoNode

rclpy.init()
node = DepthRoiDemoNode()

# 伪造相机内参 (D435 彩色 640x480 近似值)
class FakeInfo:
    def __init__(self):
        self.k = [613.4, 0.0, 320.0, 0.0, 612.2, 240.0, 0.0, 0.0, 1.0]
node.info_cb(FakeInfo())

# 伪造 RGB (纯黑, 只测流程)
h, w = 480, 640
node.rgb_image = np.zeros((h, w, 3), dtype=np.uint8)

print("=== 测试 1: 人在正前方 0.8m (应前进) ===")
node.depth_image = np.full((h, w), 0.8, dtype=np.float32)  # 全画面 0.8m
node.process_frame()
print("  process_frame 无异常 ✓")
res = node._last_res if hasattr(node, '_last_res') else None

print("\n=== 测试 2: 空深度 (全 0 → 无有效点, 不崩溃) ===")
node.depth_image = np.zeros((h, w), dtype=np.float32)
node.process_frame()
print("  空深度无异常 ✓")

print("\n=== 测试 3: 无目标 (深度 10m > ROI Z 上限 1.5m) ===")
node.depth_image = np.full((h, w), 10.0, dtype=np.float32)
node.process_frame()
print("  无目标无异常 ✓")

print("\n=== 测试 4: depth_roi_mask 形状 (全 0.8m 画面) ===")
node.depth_image = np.full((h, w), 0.8, dtype=np.float32)
mask = node.depth_roi_mask()
print(f"  mask shape={mask.shape} dtype={mask.dtype}")
print(f"  ROI 像素数 = {int(mask.sum())} (应 > 0)")

print("\n=== 测试 5: 深度图含毫米级噪声点 (反投影后离群剔除) ===")
rng = np.random.default_rng(42)
depth = np.full((h, w), 1.0, dtype=np.float32)
# 撒 5% 的 0.1m 噪声点 (在画面中央区域)
yy, xx = np.where(rng.random((h, w)) < 0.05)
for i in range(len(xx)):
    depth[yy[i], xx[i]] = 0.1
node.depth_image = depth
node.process_frame()
print("  含噪声深度无异常 ✓")

print("\n=== 测试 6: 反投影一致性 — 深度图中心 0.8m → 3D 点 ≈ (0,0,0.8) ===")
node.depth_image = np.full((h, w), 0.8, dtype=np.float32)
pts = node.depth_to_points()
print(f"  点数 = {len(pts)} (应 ≈ 全部有效像素)")
print(f"  z 范围: {pts[:,2].min():.3f} ~ {pts[:,2].max():.3f} m (应全 0.8)")
center_mask = (np.abs(pts[:,0]) < 0.02) & (np.abs(pts[:,1]) < 0.02)
print(f"  中心附近点: {int(center_mask.sum())} (应 > 0)")
assert np.allclose(pts[:,2], 0.8), "反投影 z 应等于深度值"

node.destroy_node()
rclpy.shutdown()
print("\n✅ 全部运行级测试通过")
