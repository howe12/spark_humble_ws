#!/usr/bin/env python3
"""1.2 数据分析 — IMU 航迹推算 (Dead Reckoning)

基于 IMU 运动方程，用欧拉法从角速度/加速度递推位置和姿态。
对比「纯 IMU」vs「IMU + 编码器融合」的累积误差。

核心公式:
  R_{k+1} = R_k · exp(ω̂_k · dt)
  v_{k+1} = v_k + (R_k · a_k) · dt      (a_k 已是世界系加速度)
  p_{k+1} = p_k + v_k · dt

用法: python3 imu_dead_reckon.py
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os, math

DT = 0.02; DURATION = 10.0; N = int(DURATION / DT)
t = np.arange(N) * DT

# ── 真实轨迹: 绕圈运动 ──
radius = 1.0; angular_speed = 0.6  # rad/s
true_theta = angular_speed * t
true_x = radius * np.sin(true_theta)
true_y = radius * (1 - np.cos(true_theta))
true_omega = angular_speed * np.ones(N)     # 恒定角速度
true_v = radius * angular_speed * np.ones(N) # 线速度 v = ωr

# ── IMU 模拟 ──
gyro_bias_est = 2.424e-5
accel_bias_est = 9.81e-5

# IMU 测量值 (世界系加速度 + 噪声, 已去重力)
gyro_meas = true_omega + gyro_bias_est + np.random.randn(N) * 0.003
# 向心加速度 a = v²/r = ω²r, 方向指向圆心
accel_x_true = -angular_speed**2 * radius * np.sin(true_theta)
accel_y_true = -angular_speed**2 * radius * np.cos(true_theta)
accel_meas_x = accel_x_true + accel_bias_est + np.random.randn(N) * 0.01
accel_meas_y = accel_y_true + accel_bias_est + np.random.randn(N) * 0.01

# ── 编码器 ──
encoder_v = true_v + np.random.randn(N) * 0.02
slip_idx = np.random.choice(N, N//15, replace=False)
encoder_v[slip_idx] *= 0.2

# ═══════════════════════════════════════
# 1. 纯 IMU 航迹推算
# ═══════════════════════════════════════
theta_imu = 0.0; vx_imu = 0.0; vy_imu = 0.0
px_imu = 0.0; py_imu = 0.0
traj_imu = [(0, 0)]

for i in range(N - 1):
    w = gyro_meas[i] - gyro_bias_est
    ax = accel_meas_x[i] - accel_bias_est
    ay = accel_meas_y[i] - accel_bias_est

    theta_imu += w * DT
    vx_imu += ax * DT
    vy_imu += ay * DT
    px_imu += vx_imu * DT
    py_imu += vy_imu * DT
    traj_imu.append((px_imu, py_imu))

traj_imu = np.array(traj_imu)

# ═══════════════════════════════════════
# 2. IMU + 编码器融合 (编码器提供线速度)
# ═══════════════════════════════════════
theta_f = 0.0; px_f = 0.0; py_f = 0.0
traj_fused = [(0, 0)]

for i in range(N - 1):
    w = gyro_meas[i] - gyro_bias_est
    theta_f += w * DT
    px_f += encoder_v[i] * math.cos(theta_f) * DT
    py_f += encoder_v[i] * math.sin(theta_f) * DT
    traj_fused.append((px_f, py_f))

traj_fused = np.array(traj_fused)
traj_true = np.column_stack([true_x, true_y])

# ── 误差 ──
e_imu = np.linalg.norm(traj_imu - traj_true, axis=1)
e_fused = np.linalg.norm(traj_fused - traj_true, axis=1)

print('='*55)
print('IMU 航迹推算 — 误差分析')
print('='*55)
print(f'纯 IMU:          终点误差 {e_imu[-1]:.3f} m')
print(f'IMU+编码器融合:  终点误差 {e_fused[-1]:.3f} m')
print(f'融合改善:        {e_imu[-1]/max(e_fused[-1],1e-6):.1f}x')

# ── 可视化 ──
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
axes[0].plot(traj_true[:,0], traj_true[:,1], 'k--', lw=2, label='True')
axes[0].plot(traj_imu[:,0], traj_imu[:,1], 'r-', lw=0.8, alpha=0.7, label='IMU')
axes[0].plot(traj_fused[:,0], traj_fused[:,1], 'b-', lw=1.5, label='IMU+Encoder')
axes[0].set_xlabel('X (m)'); axes[0].set_ylabel('Y (m)')
axes[0].set_title('Trajectory'); axes[0].legend(); axes[0].axis('equal'); axes[0].grid(alpha=0.3)

axes[1].plot(t, e_imu, 'r-', lw=0.8, alpha=0.7, label='IMU')
axes[1].plot(t, e_fused, 'b-', lw=1.5, label='IMU+Encoder')
axes[1].set_xlabel('Time (s)'); axes[1].set_ylabel('Error (m)')
axes[1].set_title('Error over time'); axes[1].legend(); axes[1].grid(alpha=0.3)

plt.tight_layout()
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pictures', 'imu_trajectory.png')
os.makedirs(os.path.dirname(out), exist_ok=True)
plt.savefig(out, dpi=100); plt.close()
print(f'Chart saved: {out}')
