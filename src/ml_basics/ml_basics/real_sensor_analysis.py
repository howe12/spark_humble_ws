#!/usr/bin/env python3
"""1.2 数据分析 — 真实传感器采集与分析

订阅 ROS2 传感器话题 → 采集数据 → 清洗 → 统计 → 可视化

与 data_analysis.py（模拟数据版）的区别：
  - 数据来源：真实 /imu_data + /odom 话题，而非 numpy 模拟
  - 运行方式：ros2 run ml_basics real_sensor_analysis（需要 ROS2 环境）
  - 采集 500 个采样点后自动触发分析，然后退出

用法：
  ros2 run ml_basics real_sensor_analysis
  ros2 run ml_basics real_sensor_analysis --ros-args -p max_samples:=1000

依赖的传感器话题（需提前启动机器人驱动）：
  /imu_data → sensor_msgs/Imu     (陀螺仪 + 加速度计)
  /odom  → nav_msgs/Odometry   (轮速里程计)
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from nav_msgs.msg import Odometry
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os


class RealSensorCollector(Node):
    def __init__(self):
        super().__init__('real_sensor_analysis')

        self.declare_parameter('max_samples', 500)
        self.max_samples = self.get_parameter(
            'max_samples').get_parameter_value().integer_value

        # ── 数据缓冲 ──
        self.gyro_z = []
        self.accel_x = []
        self.encoder_v = []
        self.done = False

        # ── 订阅传感器话题 ──
        self.imu_sub = self.create_subscription(
            Imu, '/imu_data', self.imu_callback, 10)
        self.odom_sub = self.create_subscription(
            Odometry, '/odom', self.odom_callback, 10)

        self.get_logger().info(
            f'开始采集传感器数据 (目标 {self.max_samples} 点)...')
        self.get_logger().info('  订阅: /imu_data → gyro_z, accel_x')
        self.get_logger().info('  订阅: /odom → encoder_v')

    def imu_callback(self, msg: Imu):
        if self.done:
            return
        if len(self.gyro_z) >= self.max_samples:
            return

        self.gyro_z.append(msg.angular_velocity.z)
        self.accel_x.append(msg.linear_acceleration.x)
        self._check_done()

    def odom_callback(self, msg: Odometry):
        if self.done:
            return
        if len(self.encoder_v) >= self.max_samples:
            return

        self.encoder_v.append(msg.twist.twist.linear.x)
        self._check_done()

    def _check_done(self):
        if (len(self.gyro_z) >= self.max_samples and
                len(self.encoder_v) >= self.max_samples and
                not self.done):
            self.done = True
            self.get_logger().info(
                f'✅ 采集完成: gyro={len(self.gyro_z)} '
                f'accel={len(self.accel_x)} encoder={len(self.encoder_v)}')
            # 对齐长度（取最短）
            n = min(len(self.gyro_z), len(self.accel_x), len(self.encoder_v))
            self.gyro_z = self.gyro_z[:n]
            self.accel_x = self.accel_x[:n]
            self.encoder_v = self.encoder_v[:n]
            self.process_data()

    # ── 以下与 data_analysis.py 共用同一套分析流水线 ──

    def detect_outliers(self, data, threshold=3):
        """Z-score 异常值检测"""
        if len(data) == 0:
            return np.array([], dtype=bool)
        z = np.abs((data - np.mean(data)) / np.std(data))
        return z > threshold

    def process_data(self):
        gyro = np.array(self.gyro_z)
        accel = np.array(self.accel_x)
        encoder = np.array(self.encoder_v)

        # ── 数据清洗 ──
        outliers_gyro = self.detect_outliers(gyro)
        outliers_accel = self.detect_outliers(accel)
        outliers_enc = self.detect_outliers(encoder)
        slip_idx = np.where(outliers_enc)[0]

        gyro_bias = 2.424e-5   # 5 deg/h → rad/s
        accel_bias = 9.81e-5
        gyro_corrected = gyro - gyro_bias
        accel_corrected = accel - accel_bias

        self.get_logger().info('')
        self.get_logger().info('=' * 50)
        self.get_logger().info('Sensor Data Analysis (Real Sensors)')
        self.get_logger().info('=' * 50)

        self.get_logger().info(f'Outlier Detection (Z-score > 3):')
        self.get_logger().info(f'  Gyro:    {outliers_gyro.sum()} outliers')
        self.get_logger().info(f'  Accel:   {outliers_accel.sum()} outliers')
        self.get_logger().info(f'  Encoder: {outliers_enc.sum()} outliers')

        self.get_logger().info(f'Feature Statistics:')
        for name, data in [
            ('Gyro Z (rad/s)', gyro_corrected),
            ('Accel X (m/s^2)', accel_corrected),
            ('Encoder Speed (m/s)', encoder),
        ]:
            self.get_logger().info(
                f'  {name}: mean={np.mean(data):.4f}  '
                f'std={np.std(data):.4f}  '
                f'min={np.min(data):.4f}  max={np.max(data):.4f}')

        # ── 可视化 ──
        t = np.arange(len(gyro_corrected)) * 0.02  # 假设 50Hz
        fig, axes = plt.subplots(3, 2, figsize=(12, 10))
        fig.suptitle('Sensor Data Analysis (Real Sensors)', fontsize=14)

        # Time series
        axes[0, 0].plot(t, gyro_corrected, 'b-', alpha=0.7, linewidth=0.5)
        axes[0, 0].set_title('Gyro Z-axis Angular Velocity')
        axes[0, 0].set_ylabel('rad/s')

        axes[1, 0].plot(t, accel_corrected, 'g-', alpha=0.7, linewidth=0.5)
        axes[1, 0].set_title('Accelerometer X-axis')
        axes[1, 0].set_ylabel('m/s^2')

        axes[2, 0].plot(t, encoder, 'r-', alpha=0.7, linewidth=0.5)
        if len(slip_idx) > 0:
            axes[2, 0].scatter(t[slip_idx], encoder[slip_idx],
                               c='orange', s=5, label='Outliers')
        axes[2, 0].set_title('Encoder Velocity')
        axes[2, 0].set_xlabel('Time (s)')
        axes[2, 0].set_ylabel('m/s')
        if len(slip_idx) > 0:
            axes[2, 0].legend(fontsize=8)

        # Histograms
        axes[0, 1].hist(gyro_corrected, bins=30, color='b', alpha=0.7)
        axes[0, 1].set_title('Gyro Distribution')

        axes[1, 1].hist(accel_corrected, bins=30, color='g', alpha=0.7)
        axes[1, 1].set_title('Accel Distribution')

        axes[2, 1].hist(encoder, bins=30, color='r', alpha=0.7)
        axes[2, 1].set_title('Velocity Distribution')
        axes[2, 1].set_xlabel('m/s')

        plt.tight_layout()

        # Save
        out_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', 'pictures')
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, 'real_sensor_analysis.png')
        plt.savefig(out_path, dpi=100)
        self.get_logger().info(f'Chart saved: {out_path}')
        plt.close()

        self.get_logger().info('Data analysis complete')


def main():
    rclpy.init()
    node = RealSensorCollector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
