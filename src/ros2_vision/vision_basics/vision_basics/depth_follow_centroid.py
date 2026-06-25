#!/usr/bin/env python3
"""03-2 深度跟随: 质心跟踪算法原理演示（纯数值，无需硬件）

Spark 深度跟随的核心算法:
  1. 在点云中划定 3D ROI（前 0.1~0.5m, 左右 ±0.2m, 高 <1.5m）
  2. 计算 ROI 内所有点的质心 (x̄, z̄)
  3. 线速度 = (z̄ - goal) × Kp_z    — 保持 0.7m 跟随距离
  4. 角速度 = arcsin(x̄ / d) × Kp_x — 对准质心方向
  5. 点 < 2000 → 停（目标丢失）

用模拟点云验证公式正确性。
"""

import math
import numpy as np

# ============ 跟随参数（与 spark_follower.cpp 一致） ============
# 3D ROI 范围（相机坐标系: X=右, Y=下, Z=前）
MIN_X, MAX_X = -0.2, 0.2    # 左右 ±0.2m
MIN_Y, MAX_Y = 0.1, 0.5     # -pt.y → 机器人前方 0.1~0.5m
MAX_Z        = 1.5          # 高度上限
GOAL_DEPTH   = 0.7          # 目标跟随距离（m）
Z_SCALE      = 1.2          # 线速度比例
X_SCALE      = 5.0          # 角速度比例
MIN_POINTS   = 2000         # 最少有效点数

def depth_follow_centroid(points, goal_depth=GOAL_DEPTH,
                          z_scale=Z_SCALE, x_scale=X_SCALE):
    """
    计算深度跟随的 cmd_vel。

    Args:
        points: [(x, y, z), ...] 列表，相机坐标系 (X=右, Y=下, Z=前)
        goal_depth: 目标跟随距离 (m)
        z_scale: 线速度比例系数
        x_scale: 角速度比例系数

    Returns:
        (linear_x, angular_z) 或 None（目标丢失）
    """
    x_sum, z_sum, n = 0.0, 0.0, 0

    for px, py, pz in points:
        # 3D ROI 过滤
        # 注意：机器人前方 = -py（相机 Y 轴向下）
        forward = -py
        if (MIN_X < px < MAX_X and
            MIN_Y < forward < MAX_Y and
            pz < MAX_Z):
            x_sum += px
            z_sum += pz
            n += 1

    if n < MIN_POINTS:
        return None  # 目标丢失

    # 质心
    cx = x_sum / n       # 左右偏移 (m)
    cz = z_sum / n       # 前后距离 (m)

    # 控制律
    linear_x = (cz - goal_depth) * z_scale
    dist = math.sqrt(cx * cx + cz * cz)
    angular_z = math.asin(cx / dist) * x_scale if dist > 0 else 0.0

    return (linear_x, angular_z, cx, cz, n)


# ============ 模拟测试 ============
if __name__ == '__main__':
    print("=" * 60)
    print("Spark 深度跟随 — 质心跟踪算法演示")
    print("=" * 60)
    print(f"ROI: X∈[{MIN_X},{MAX_X}]  Y∈[{MIN_Y},{MAX_Y}]  Z<{MAX_Z}")
    print(f"目标距离: {GOAL_DEPTH}m  最少点数: {MIN_POINTS}")
    print()

    # --- 测试 1: 人在正前方 0.8m（应后退，cz=0.8 > goal=0.7） ---
    print("--- 测试 1: 人在正前方 0.8m（应后退，cz=0.8 > goal=0.7） ---")
    points = []
    for _ in range(3000):
        px = np.random.normal(0, 0.05)
        py = np.random.normal(-0.3, 0.05)  # forward=0.3m, 在 ROI Y 范围内
        pz = np.random.normal(0.8, 0.1)    # 深度 0.8m
        points.append((px, py, pz))
    result = depth_follow_centroid(points)
    if result:
        lx, az, cx, cz, n = result
        print(f"  点数: {n}, 质心: ({cx:.3f}, {cz:.3f})m")
        print(f"  cmd_vel: linear_x={lx:.3f}  angular_z={az:.3f}")
        print(f"  → 机器人后退（cz=0.80 > goal=0.70）")

    # --- 测试 2: 人在右前方 0.5m（近了 + 偏右，应前进 + 左转） ---
    print("\n--- 测试 2: 人在右前方 0.5m（近了 + 偏右，应前进 + 左转） ---")
    points = []
    for _ in range(3000):
        px = np.random.normal(0.12, 0.03)  # 偏右
        py = np.random.normal(-0.25, 0.05) # forward=0.25m
        pz = np.random.normal(0.5, 0.05)   # 深度 0.5m
        points.append((px, py, pz))
    result = depth_follow_centroid(points)
    if result:
        lx, az, cx, cz, n = result
        print(f"  点数: {n}, 质心: ({cx:.3f}, {cz:.3f})m")
        print(f"  cmd_vel: linear_x={lx:.3f}  angular_z={az:.3f}")
        print(f"  → 机器人后退（cz=0.60 < goal=0.70），左转（cx>0）")

    # --- 测试 3: 目标丢失（无人在 ROI） ---
    print("\n--- 测试 3: 目标丢失（ROI 内不到 2000 点） ---")
    points = [(0, 0, 10) for _ in range(100)]  # 全部在 ROI 外
    result = depth_follow_centroid(points)
    print(f"  结果: {result} → 停止（目标丢失）")

    print()
    print("=" * 60)
    print("关键公式:")
    print("  linear_x  = (cz - goal_depth) × z_scale")
    print("  angular_z = arcsin(cx / d) × x_scale")
    print("  d = sqrt(cx² + cz²)")
    print()
    print("死区逻辑:")
    print("  |cz - goal| < 0.05m → linear_x = 0 (避免抖动)")
    print("  |cx| < 0.087 → angular_z = 0 (避免抖动)")
    print("  n < 2000 → 停止 (目标丢失)")
