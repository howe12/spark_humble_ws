#!/usr/bin/env python3
"""1.2 Data Analysis — sensor data loading, cleaning, visualization

Demonstrates standard ML data analysis pipeline:
  1. Load simulated sensor data (IMU + encoder)
  2. Data cleaning (outlier detection, de-biasing)
  3. Feature statistics (mean/variance/distribution)
  4. Visualization (time series/histogram)

Usage: python3 data_analysis.py
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')  # headless mode, save to file
import matplotlib.pyplot as plt
import os

# ── 1. Generate simulated sensor data ──
np.random.seed(42)
N = 500
t = np.arange(N) * 0.02  # 20ms sample period

# IMU gyro (Z-axis, with noise and bias)
gyro_bias = 2.424e-5  # 5 deg/h -> rad/s
gyro_noise = 0.001
gyro_z = 0.1 * np.sin(0.02 * t) + gyro_bias + np.random.randn(N) * gyro_noise

# IMU accelerometer (X-axis forward, with gravity component)
accel_bias = 9.81e-5
accel_noise = 0.01
accel_x = 0.05 + accel_bias + np.random.randn(N) * accel_noise

# Encoder velocity (with wheel slip)
encoder_v = 0.1 + 0.02 * np.sin(0.05 * t) + np.random.randn(N) * 0.02
# Simulate slip: 10% of data points near zero
slip_idx = np.random.choice(N, N // 10, replace=False)
encoder_v[slip_idx] *= 0.05

print('=' * 60)
print('Sensor Data Analysis')
print('=' * 60)

# ── 2. Data cleaning ──
def detect_outliers(data, threshold=3):
    """Z-score outlier detection"""
    z = np.abs((data - np.mean(data)) / np.std(data))
    return z > threshold

outliers_gyro = detect_outliers(gyro_z)
outliers_accel = detect_outliers(accel_x)
outliers_enc = detect_outliers(encoder_v)

print(f'\nOutlier Detection (Z-score > 3):')
print(f'  Gyro:    {outliers_gyro.sum()} outliers')
print(f'  Accel:   {outliers_accel.sum()} outliers')
print(f'  Encoder: {outliers_enc.sum()} outliers')

# De-bias
gyro_z_corrected = gyro_z - gyro_bias
accel_x_corrected = accel_x - accel_bias

# ── 3. Feature statistics ──
print(f'\nFeature Statistics:')
for name, data in [('Gyro Z (rad/s)', gyro_z_corrected),
                    ('Accel X (m/s^2)', accel_x_corrected),
                    ('Encoder Speed (m/s)', encoder_v)]:
    print(f'  {name}:')
    print(f'    mean={np.mean(data):.4f}  std={np.std(data):.4f}')
    print(f'    min={np.min(data):.4f}  max={np.max(data):.4f}')

# ── 4. Visualization ──
fig, axes = plt.subplots(3, 2, figsize=(12, 10))
fig.suptitle('Sensor Data Analysis', fontsize=14)

# Time series
axes[0, 0].plot(t, gyro_z_corrected, 'b-', alpha=0.7, linewidth=0.5)
axes[0, 0].set_title('Gyro Z-axis Angular Velocity')
axes[0, 0].set_ylabel('rad/s')

axes[1, 0].plot(t, accel_x_corrected, 'g-', alpha=0.7, linewidth=0.5)
axes[1, 0].set_title('Accelerometer X-axis')
axes[1, 0].set_ylabel('m/s^2')

axes[2, 0].plot(t, encoder_v, 'r-', alpha=0.7, linewidth=0.5)
axes[2, 0].scatter(t[slip_idx], encoder_v[slip_idx], c='orange', s=5, label='Slip points')
axes[2, 0].set_title('Encoder Velocity (with slip)')
axes[2, 0].set_xlabel('Time (s)')
axes[2, 0].set_ylabel('m/s')
axes[2, 0].legend(fontsize=8)

# Histograms
axes[0, 1].hist(gyro_z_corrected, bins=30, color='b', alpha=0.7)
axes[0, 1].set_title('Gyro Distribution')

axes[1, 1].hist(accel_x_corrected, bins=30, color='g', alpha=0.7)
axes[1, 1].set_title('Accel Distribution')

axes[2, 1].hist(encoder_v, bins=30, color='r', alpha=0.7)
axes[2, 1].set_title('Velocity Distribution')
axes[2, 1].set_xlabel('m/s')

plt.tight_layout()

# Save figure
out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pictures')
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, 'data_analysis.png')
plt.savefig(out_path, dpi=100)
print(f'\nChart saved: {out_path}')
plt.close()

print('Data analysis complete')
