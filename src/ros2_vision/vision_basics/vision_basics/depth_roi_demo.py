#!/usr/bin/env python3
"""03-2 深度跟随: ROI 获取 + 深度判断 + 运动控制可视化演示

围绕「深度信息滤波」课程, 把点云处理链路完整可视化:
  1. 获取 ROI : 在点云中划定 3D 目标区域 (X左右 / Z前方 / Y高度)
  2. 判断深度 : 对 ROI 内点的深度做统计 (中值/均值, 体现滤波抗噪思想)
  3. 运动控制 : 深度 vs 目标深度 + 横向偏移 → 前进/后退/左转/右转/停止
  4. 可视化   : RGB 图叠加 ROI 投影框 + 质心 + 运动指令箭头

坐标系 (D435 深度相机, 与 realsense points 一致):
  X → 右, Y → 下, Z → 前 (深度, 单位 m)

运行:
  终端1: ros2 launch camera_driver_transfer d435.launch.py
  终端2: ros2 run vision_basics depth_roi_demo
  终端3(可选): ros2 topic echo /cmd_vel
"""

import math
import numpy as np

# ============ ROI 与跟随参数 ============
# 3D ROI 范围 (相机坐标系: X=右, Y=下, Z=前)
ROI_X_MIN, ROI_X_MAX = -0.2, 0.2    # 左右 ±0.2m
ROI_Z_MIN, ROI_Z_MAX = 0.1, 1.5     # 前方深度 0.1~1.5m  ← 深度上限(不是高度!)
ROI_Y_MIN, ROI_Y_MAX = -0.5, 0.5    # 高度: 光轴上下各 0.5m (人体躯干)

GOAL_DEPTH   = 0.7    # 目标跟随距离 (m)
Z_DEADBAND   = 0.05   # 深度死区: |z-goal|<0.05 → 停止 (防抖)
X_DEADBAND   = 0.087  # 横向死区: |cx|<0.087 → 不转向
MIN_POINTS   = 200    # ROI 内最少有效点数 (低于则视为目标丢失)
Z_SCALE      = 1.2    # 线速度比例
X_SCALE      = 5.0    # 角速度比例
MAX_LINEAR   = 0.4    # 最大线速度 (m/s)
MAX_ANGULAR  = 1.0    # 最大角速度 (rad/s)


def remove_outliers(in_xyz, method='zscore', k=2.5):
    """ROI 内点云离群点剔除 (深度信息滤波核心)

    在计算质心/深度前, 先去掉"明显偏移"的点, 提高距离判断鲁棒性。

    支持 4 种方法:
      none       : 不过滤 (原始点云)
      zscore     : 基于深度 z 的 Z-score 滤波,
                   去掉 |z - median| > k × MAD 的点 (默认 k=2.5)
      iqr        : 四分位距法, 去掉 [Q1-1.5×IQR, Q3+1.5×IQR] 之外的点
      percentile : 分位数裁剪, 保留 [k, 100-k] 百分位之间 (k=2 → 2%~98%)

    实现说明 (教学点):
      - 深度相机在边缘/反光/遮挡处会产生错误深度(离群点)
      - 这类点虽然落在 ROI 内, 但会严重拉偏均值 → 必须先剔除
      - zscore 用 median+MAD 而非 mean+std: MAD 本身抗离群,
        不会因为离群点多而被"带跑"
      - 返回剔除后的点云 (保持 N×3 结构)

    Args:
        in_xyz: (N,3) 数组, 已经过 ROI 过滤的点
        method: 滤波方法
        k: zscore 的倍数阈值 / percentile 的裁剪百分比

    Returns:
        (N',3) 数组, 剔除离群点后的点云
    """
    if method == 'none' or len(in_xyz) < 10:
        return in_xyz

    z = in_xyz[:, 2]

    if method == 'zscore':
        # 中位数 + 中位绝对偏差 (MAD) — 抗离群
        med = np.median(z)
        mad = np.median(np.abs(z - med)) + 1e-9
        keep = np.abs(z - med) < k * 1.4826 * mad
        return in_xyz[keep]

    if method == 'iqr':
        q1, q3 = np.percentile(z, [25, 75])
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        return in_xyz[(z >= lo) & (z <= hi)]

    if method == 'percentile':
        lo, hi = np.percentile(z, [k, 100 - k])
        return in_xyz[(z >= lo) & (z <= hi)]

    # 未知方法 → 不过滤
    return in_xyz


def analyze_roi(points_xyz, roi=None, filter_method='none'):
    """从点云提取 ROI 并计算质心与深度统计 (核心算法, 可独立测试)

    处理链路:
      原始点云 → 3D ROI 过滤 → 离群点剔除(可选) → 质心/深度统计

    Args:
        points_xyz: numpy 数组 shape=(N,3), 列 = (x, y, z)
        roi: (x_min,x_max, y_min,y_max, z_min,z_max), 默认用全局参数
        filter_method: 离群点剔除方法, none/zscore/iqr/percentile

    Returns:
        dict: {n, n_raw, cx, cz, depth_median, depth_mean, depth_min, in_roi}
          n           剔除离群点后的点数
          n_raw       ROI 原始点数 (剔除前)
          cx           质心横向偏移 (m, 右为正)
          cz           质心深度 (m, 前方)
          depth_median ROI 深度中值 (抗噪, 推荐用于控制)
          depth_mean   ROI 深度均值 (易受离群点影响, 用于对比)
          depth_min   ROI 最近点深度
          in_roi       目标是否在 ROI 内 (n >= MIN_POINTS)
    """
    if roi is None:
        roi = (ROI_X_MIN, ROI_X_MAX, ROI_Y_MIN, ROI_Y_MAX,
               ROI_Z_MIN, ROI_Z_MAX)
    x_min, x_max, y_min, y_max, z_min, z_max = roi

    if points_xyz is None or len(points_xyz) < MIN_POINTS:
        return dict(n=0, n_raw=0, cx=0.0, cz=0.0,
                    depth_median=0.0, depth_mean=0.0,
                    depth_min=0.0, in_roi=False)

    x, y, z = points_xyz[:, 0], points_xyz[:, 1], points_xyz[:, 2]

    # ---- 1. 3D ROI 过滤 (矢量运算, 快) ----
    # 注意: 前方距离用 z(深度), 高度用 y, 左右用 x —— 各司其职
    mask = ((x > x_min) & (x < x_max) &
            (y > y_min) & (y < y_max) &
            (z > z_min) & (z < z_max))
    in_xyz = points_xyz[mask]
    n_raw = int(len(in_xyz))

    if n_raw < MIN_POINTS:
        return dict(n=n_raw, n_raw=n_raw, cx=0.0, cz=0.0,
                    depth_median=0.0, depth_mean=0.0,
                    depth_min=0.0, in_roi=False)

    # ---- 2. 离群点剔除 (可选, 深度信息滤波) ----
    in_xyz = remove_outliers(in_xyz, method=filter_method)
    n = int(len(in_xyz))

    if n < MIN_POINTS:
        return dict(n=n, n_raw=n_raw, cx=0.0, cz=0.0,
                    depth_median=0.0, depth_mean=0.0,
                    depth_min=0.0, in_roi=False)

    # ---- 3. 质心 + 深度统计 (剔除后) ----
    cx = float(in_xyz[:, 0].mean())          # 质心横向偏移
    cz = float(in_xyz[:, 2].mean())          # 质心深度(均值)
    depth_median = float(np.median(in_xyz[:, 2]))  # 深度中值(滤波)
    depth_mean = float(in_xyz[:, 2].mean())        # 深度均值
    depth_min = float(in_xyz[:, 2].min())          # 最近点深度

    return dict(n=n, n_raw=n_raw, cx=cx, cz=cz,
                depth_median=depth_median, depth_mean=depth_mean,
                depth_min=depth_min, in_roi=True)


def decide_motion(cx, cz, goal_depth=GOAL_DEPTH, in_roi=True):
    """深度判断 → 运动控制指令 (带死区 + 限幅)

    Args:
        cx: 质心横向偏移 (m, 右为正)
        cz: 控制用深度 (m, 前方) — 由调用方选择 mean/median/min
        goal_depth: 目标跟随距离 (m)
        in_roi: 目标是否在 ROI 内 (False → 目标丢失, 停止)

    Returns:
        (linear_x, angular_z, action_str)
          linear_x: 线速度 (正=前进)
          angular_z: 角速度 (正=左转, ROS 约定逆时针为正)
          action_str: 中文动作描述, 用于可视化
    """
    # 目标丢失 → 立即停止
    if not in_roi:
        return 0.0, 0.0, "STOP 目标丢失"

    linear_x = (cz - goal_depth) * Z_SCALE
    # 角速度: 目标在右(cx>0) → 应右转(angular_z<0), 与 C++ 原版 pubCmd(-x, z) 一致
    angular_z = -math.asin(max(-1.0, min(1.0, cx / max(cz, 1e-6)))) * X_SCALE

    # 死区: 接近目标距离 → 不前后动; 对准质心 → 不转向 (防抖)
    if abs(cz - goal_depth) < Z_DEADBAND:
        linear_x = 0.0
    if abs(cx) < X_DEADBAND:
        angular_z = 0.0

    # 限幅
    linear_x = max(-MAX_LINEAR, min(MAX_LINEAR, linear_x))
    angular_z = max(-MAX_ANGULAR, min(MAX_ANGULAR, angular_z))

    # 动作描述 (用于画面叠加)
    if abs(linear_x) < 1e-6 and abs(angular_z) < 1e-6:
        action = "STOP 保持"
    else:
        parts = []
        parts.append("前进" if linear_x > 0 else ("后退" if linear_x < 0 else ""))
        parts.append("左转" if angular_z > 0 else ("右转" if angular_z < 0 else ""))
        action = " ".join(p for p in parts if p)

    return linear_x, angular_z, action


# ============ 模拟测试 (无硬件可运行) ============
if __name__ == '__main__':
    print("=" * 64)
    print("03-2 深度跟随 — ROI 获取 + 深度判断 + 运动控制演示")
    print("=" * 64)
    print(f"ROI: X∈[{ROI_X_MIN},{ROI_X_MAX}]  "
          f"Z∈[{ROI_Z_MIN},{ROI_Z_MAX}]  Y∈[{ROI_Y_MIN},{ROI_Y_MAX}]")
    print(f"目标距离: {GOAL_DEPTH}m  最少点数: {MIN_POINTS}")
    print()

    # --- 测试 1: 人在正前方 0.8m (应前进) ---
    print("--- 测试 1: 人在正前方 0.8m (cz>goal → 应前进) ---")
    rng = np.random.default_rng(42)
    pts = np.column_stack([
        rng.normal(0.0, 0.05, 3000),      # x: 居中
        rng.normal(0.0, 0.05, 3000),      # y: 光轴附近 (高度合理)
        rng.normal(0.8, 0.1, 3000),       # z: 前方 0.8m
    ])
    res = analyze_roi(pts)
    lx, az, act = decide_motion(res['cx'], res['cz'])
    print(f"  点数={res['n']} 质心=({res['cx']:.3f},{res['cz']:.3f})m "
          f"深度中值={res['depth_median']:.2f}m")
    print(f"  cmd_vel: linear_x={lx:+.2f} angular_z={az:+.2f} → {act}")
    assert lx > 0, "cz=0.8>goal=0.7 应前进" if False else "cz=0.8>0.7 → 接近目标? 应后退"  # noqa
    print()

    # --- 测试 2: 人在右前方 0.5m (偏右+近了 → 应右转+后退) ---
    print("--- 测试 2: 人在右前方 0.5m (偏右+近了 → 应右转+后退) ---")
    pts = np.column_stack([
        rng.normal(0.12, 0.03, 3000),     # x: 偏右
        rng.normal(0.0, 0.05, 3000),      # y: 光轴附近
        rng.normal(0.5, 0.05, 3000),      # z: 前方 0.5m
    ])
    res = analyze_roi(pts)
    lx, az, act = decide_motion(res['cx'], res['cz'])
    print(f"  点数={res['n']} 质心=({res['cx']:.3f},{res['cz']:.3f})m "
          f"深度中值={res['depth_median']:.2f}m")
    print(f"  cmd_vel: linear_x={lx:+.2f} angular_z={az:+.2f} → {act}")
    assert az < 0, "cx>0 偏右 → 应右转 (angular_z<0)"
    print()

    # --- 测试 3: 目标丢失 (ROI 内点数不足) ---
    print("--- 测试 3: 目标丢失 (ROI 内点数不足) ---")
    pts = np.full((100, 3), (0.0, 0.0, 10.0))  # 全在 ROI 外
    res = analyze_roi(pts)
    lx, az, act = decide_motion(res['cx'], res['cz'], in_roi=res['in_roi'])
    print(f"  点数={res['n']} in_roi={res['in_roi']} → {act}")
    assert act == "STOP 目标丢失", f"应停止, 实际: {act}"
    print()

    # --- 测试 4: 死区验证 (正好在目标距离, 横向很小) ---
    print("--- 测试 4: 死区 (目标 0.7m 正中, 应 STOP) ---")
    pts = np.column_stack([
        rng.normal(0.0, 0.01, 3000),
        rng.normal(0.0, 0.05, 3000),
        rng.normal(0.7, 0.02, 3000),
    ])
    res = analyze_roi(pts)
    lx, az, act = decide_motion(res['cx'], res['cz'])
    print(f"  点数={res['n']} 质心=({res['cx']:.3f},{res['cz']:.3f})m "
          f"cmd=(lx={lx:+.2f}, az={az:+.2f}) → {act}")
    assert act == "STOP 保持", f"应停止, 实际: {act}"
    print()

    # --- 测试 5: 模式对比 — 人 1.2m + 地面背景 0.5m (均值被污染) ---
    print("--- 测试 5: 模式对比 — 人 1.2m + 背景 0.5m (均值被污染) ---")
    person = np.column_stack([
        rng.normal(0.0, 0.05, 2500),   # 人: 2500 点
        rng.normal(0.0, 0.05, 2500),
        rng.normal(1.2, 0.05, 2500),   # 实际深度 1.2m
    ])
    ground = np.column_stack([
        rng.normal(0.1, 0.05, 800),    # 地面/前景: 800 点
        rng.normal(0.4, 0.02, 800),
        rng.normal(0.5, 0.05, 800),    # 0.5m 混入 ROI
    ])
    pts = np.vstack([person, ground])
    res = analyze_roi(pts)
    print(f"  点数={res['n']} 真实深度=1.2m")
    print(f"  mean  ={res['depth_mean']:.2f}m  (被背景拉近 ❌)")
    print(f"  median={res['depth_median']:.2f}m  (稳健 ✅)")
    print(f"  min   ={res['depth_min']:.2f}m  (最近表面)")
    # 用 median 判断: 1.2m > goal 0.7m → 前进
    lx_m, _, act_m = decide_motion(0.0, res['depth_median'])
    lx_a, _, act_a = decide_motion(0.0, res['depth_mean'])
    print(f"  median → {act_m} (lx={lx_m:+.2f})  [应前进]")
    print(f"  mean   → {act_a} (lx={lx_a:+.2f})  [可能错误停止/后退]")
    assert act_m == "前进", f"median 应前进, 实际: {act_m}"
    print()

    # --- 测试 6: 离群点剔除 — 人 1.0m + 少量错误深度点 (0.1m 反光点) ---
    print("--- 测试 6: 离群点剔除 — 人 1.0m + 5% 错误深度点(0.1m) ---")
    person = np.column_stack([
        rng.normal(0.0, 0.05, 3000),
        rng.normal(0.0, 0.05, 3000),
        rng.normal(1.0, 0.05, 3000),   # 真实人 1.0m
    ])
    noise = np.column_stack([
        rng.normal(0.0, 0.05, 150),
        rng.normal(0.0, 0.05, 150),
        rng.uniform(0.05, 0.15, 150),  # 错误深度: 反光/边缘噪声 0.1m
    ])
    pts = np.vstack([person, noise])
    res_none = analyze_roi(pts, filter_method='none')
    res_z = analyze_roi(pts, filter_method='zscore')
    res_iqr = analyze_roi(pts, filter_method='iqr')
    print(f"  真实深度=1.0m, 错误点比例=5%")
    print(f"  [none]      n={res_none['n']} mean={res_none['depth_mean']:.3f}m "
          f"(被拉到 {res_none['depth_mean']:.2f}m ❌)")
    print(f"  [zscore]    n={res_z['n']} mean={res_z['depth_mean']:.3f}m "
          f"median={res_z['depth_median']:.3f}m ✅")
    print(f"  [iqr]       n={res_iqr['n']} mean={res_iqr['depth_mean']:.3f}m "
          f"median={res_iqr['depth_median']:.3f}m ✅")
    # 验证: 剔除后 mean 更接近真实 1.0m
    err_none = abs(res_none['depth_mean'] - 1.0)
    err_z = abs(res_z['depth_mean'] - 1.0)
    assert err_z < err_none, f"zscore 应比 none 更准: {err_z} vs {err_none}"
    print(f"  mean 误差: none={err_none:.3f}m → zscore={err_z:.3f}m "
          f"(改善 {err_none/err_z:.1f}×)")
    print()

    print("=" * 64)
    print("关键公式:")
    print("  linear_x = (cz - goal) × Z_SCALE        # 深度差 → 前后")
    print("  angular_z = asin(cx / cz) × X_SCALE     # 横向偏移 → 转向")
    print("  (注意: cx>0 偏右 → angular_z<0 → 右转, 与 C++ 的 -x 一致)")
    print("  |cz-goal| < 0.05 → linear=0  |cx| < 0.087 → angular=0")
    print("  ROI 点数 < 200 → 目标丢失, 停止")
    print("  深度模式: mean(均值)易被背景污染 / median(中值)稳健 / min(最近点)")
    print("  离群点剔除: zscore(MAD) / iqr / percentile — 先剔除再计算")
    print("=" * 64)
