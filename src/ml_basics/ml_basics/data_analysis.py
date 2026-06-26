#!/usr/bin/env python3
"""1.2 数据分析 — 传感器数据加载、清洗、可视化

演示机器学习中数据分析的标准流程:
  1. 加载模拟传感器数据 (IMU + 编码器)
  2. 数据清洗 (异常值检测, 缺失值处理)
  3. 特征统计 (均值/方差/分布)
  4. 可视化 (时序图/直方图/相关性热力图)

用法: python3 data_analysis.py
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')  # headless 模式，保存到文件
import matplotlib.pyplot as plt
import os

# ── 1. 生成模拟传感器数据 ──
np.random.seed(42)
N = 500
t = np.arange(N) * 0.02  # 20ms 采样周期

# IMU 角速度 (Z轴为主, 带噪声和零偏)
gyro_bias = 2.424e-5  # 5°/h → rad/s
gyro_noise = 0.001
gyro_z = 0.1 * np.sin(0.02 * t) + gyro_bias + np.random.randn(N) * gyro_noise

# IMU 加速度 (X轴前进方向, 带重力分量)
accel_bias = 9.81e-5
accel_noise = 0.01
accel_x = 0.05 + accel_bias + np.random.randn(N) * accel_noise

# 编码器速度 (带打滑现象)
encoder_v = 0.1 + 0.02 * np.sin(0.05 * t) + np.random.randn(N) * 0.02
# 模拟打滑: 10% 的数据速度接近0
slip_idx = np.random.choice(N, N//10, replace=False)
encoder_v[slip_idx] *= 0.05

print('='*60)
print('📊 传感器数据分析')
print('='*60)

# ── 2. 数据清洗 ──
def detect_outliers(data, threshold=3):
    """Z-score 异常值检测"""
    z = np.abs((data - np.mean(data)) / np.std(data))
    return z > threshold

outliers_gyro = detect_outliers(gyro_z)
outliers_accel = detect_outliers(accel_x)
outliers_enc = detect_outliers(encoder_v)

print(f'\n🔍 异常值检测 (Z-score > 3):')
print(f'  陀螺仪: {outliers_gyro.sum()} 个异常点')
print(f'  加速度: {outliers_accel.sum()} 个异常点')
print(f'  编码器: {outliers_enc.sum()} 个异常点')

# 去偏置 (去除零偏)
gyro_z_corrected = gyro_z - gyro_bias
accel_x_corrected = accel_x - accel_bias

# ── 3. 特征统计 ──
print(f'\n📈 特征统计:')
for name, data in [('陀螺仪Z (rad/s)', gyro_z_corrected),
                     ('加速度X (m/s²)', accel_x_corrected),
                     ('编码器速度 (m/s)', encoder_v)]:
    print(f'  {name}:')
    print(f'    mean={np.mean(data):.4f}  std={np.std(data):.4f}')
    print(f'    min={np.min(data):.4f}  max={np.max(data):.4f}')

# ── 4. 可视化 ──
fig, axes = plt.subplots(3, 2, figsize=(12, 10))
fig.suptitle('传感器数据分析', fontsize=14)

# 时序图
axes[0,0].plot(t, gyro_z_corrected, 'b-', alpha=0.7, linewidth=0.5)
axes[0,0].set_title('陀螺仪Z轴角速度')
axes[0,0].set_ylabel('rad/s')

axes[1,0].plot(t, accel_x_corrected, 'g-', alpha=0.7, linewidth=0.5)
axes[1,0].set_title('加速度计X轴')
axes[1,0].set_ylabel('m/s²')

axes[2,0].plot(t, encoder_v, 'r-', alpha=0.7, linewidth=0.5)
axes[2,0].scatter(t[slip_idx], encoder_v[slip_idx], c='orange', s=5, label='打滑点')
axes[2,0].set_title('编码器速度 (含打滑)')
axes[2,0].set_xlabel('时间 (s)')
axes[2,0].set_ylabel('m/s')
axes[2,0].legend(fontsize=8)

# 直方图
axes[0,1].hist(gyro_z_corrected, bins=30, color='b', alpha=0.7)
axes[0,1].set_title('角速度分布')

axes[1,1].hist(accel_x_corrected, bins=30, color='g', alpha=0.7)
axes[1,1].set_title('加速度分布')

axes[2,1].hist(encoder_v, bins=30, color='r', alpha=0.7)
axes[2,1].set_title('速度分布')
axes[2,1].set_xlabel('m/s')

plt.tight_layout()

# 保存图片
out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pictures')
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, 'data_analysis.png')
plt.savefig(out_path, dpi=100)
print(f'\n📸 图表已保存: {out_path}')
plt.close()

print('✅ 数据分析完成')
