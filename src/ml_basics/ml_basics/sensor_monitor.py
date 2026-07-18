#!/usr/bin/env python3
"""1.2 数据分析 — 实时传感器监控 (matplotlib 版)

订阅 /imu_data 和 /odom，在 matplotlib 窗口中实时绘制 3 条曲线：
  - 陀螺仪 Z 轴角速度 (去偏置)
  - 加速度计 X 轴 (去偏置)
  - 编码器线速度

异常值用红色散点标出。关闭窗口即退出。

用法:
  ros2 run ml_basics sensor_monitor

依赖: export DISPLAY=:0  (GUI 环境)
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from nav_msgs.msg import Odometry
import numpy as np
from collections import deque
import matplotlib
# 自动检测 GUI 环境
import os as _os
_os.environ.setdefault('DISPLAY', ':0')
matplotlib.use('TkAgg')
_os = None
import matplotlib.pyplot as plt


class SensorMonitorNode(Node):
    def __init__(self):
        super().__init__('sensor_monitor')

        self.declare_parameter('gyro_bias', 2.424e-5)
        self.declare_parameter('accel_bias', 9.81e-5)
        self.declare_parameter('outlier_threshold', 3.0)
        self.declare_parameter('history', 300)  # 显示最近 N 个点

        self.gyro_bias = self.get_parameter('gyro_bias').value
        self.accel_bias = self.get_parameter('accel_bias').value
        self.outlier_threshold = self.get_parameter('outlier_threshold').value
        self.history = self.get_parameter('history').value

        # ── 数据缓冲 ──
        self.t_data = deque(maxlen=self.history)
        self.gyro_data = deque(maxlen=self.history)
        self.accel_data = deque(maxlen=self.history)
        self.speed_data = deque(maxlen=self.history)

        # 异常值索引
        self.gyro_outliers = set()
        self.accel_outliers = set()
        self.speed_outliers = set()

        self.gyro_window = deque(maxlen=100)
        self.accel_window = deque(maxlen=100)
        self.speed_window = deque(maxlen=100)

        self.counter = 0

        # ── 订阅 ──
        self.imu_sub = self.create_subscription(Imu, '/imu_data', self.imu_callback, 10)
        self.odom_sub = self.create_subscription(Odometry, '/odom', self.odom_callback, 10)

        # ── matplotlib 窗口 ──
        self.fig, (self.ax1, self.ax2, self.ax3) = plt.subplots(3, 1, figsize=(10, 8))
        self.fig.canvas.manager.set_window_title('Sensor Monitor')
        self.fig.suptitle('Real-time Sensor Data', fontsize=13)

        self.line_gyro, = self.ax1.plot([], [], 'b-', linewidth=0.8, label='Gyro Z')
        self.scat_gyro, = self.ax1.plot([], [], 'ro', markersize=4, label='Outlier')
        self.ax1.set_ylabel('Gyro Z (rad/s)')
        self.ax1.legend(fontsize=7, loc='upper right')
        self.ax1.grid(True, alpha=0.3)

        self.line_accel, = self.ax2.plot([], [], 'g-', linewidth=0.8, label='Accel X')
        self.scat_accel, = self.ax2.plot([], [], 'ro', markersize=4, label='Outlier')
        self.ax2.set_ylabel('Accel X (m/s²)')
        self.ax2.legend(fontsize=7, loc='upper right')
        self.ax2.grid(True, alpha=0.3)

        self.line_speed, = self.ax3.plot([], [], 'orange', linewidth=0.8, label='Speed')
        self.scat_speed, = self.ax3.plot([], [], 'ro', markersize=4, label='Outlier')
        self.ax3.set_xlabel('Sample #')
        self.ax3.set_ylabel('Speed (m/s)')
        self.ax3.legend(fontsize=7, loc='upper right')
        self.ax3.grid(True, alpha=0.3)

        plt.ion()
        self.fig.show()

        self.get_logger().info('matplotlib 实时监控已启动，关闭窗口即退出')

    # ── 回调 ──

    def imu_callback(self, msg: Imu):
        gyro = msg.angular_velocity.z - self.gyro_bias
        accel = msg.linear_acceleration.x - self.accel_bias
        self.t_data.append(self.counter)
        self.gyro_data.append(gyro)
        self.accel_data.append(accel)
        self.gyro_window.append(gyro)
        self.accel_window.append(accel)

    def odom_callback(self, msg: Odometry):
        speed = msg.twist.twist.linear.x
        self.speed_data.append(speed)
        self.speed_window.append(speed)
        self.counter += 1
        self._update_plot()

    # ── 更新图表 ──

    def _update_plot(self):
        if len(self.t_data) < 2:
            return
        t = list(self.t_data)

        # Gyro
        gy = list(self.gyro_data)
        self.line_gyro.set_data(t[:len(gy)], gy)
        outliers = self._detect_outliers(self.gyro_window, gy[-1] if gy else 0)
        if outliers:
            idx = [t[i] for i in range(len(gy)) if i in outliers]
            vals = [gy[i] for i in range(len(gy)) if i in outliers]
            self.scat_gyro.set_data(idx, vals)
        else:
            self.scat_gyro.set_data([], [])

        # Accel
        ax = list(self.accel_data)
        self.line_accel.set_data(t[:len(ax)], ax)
        outliers = self._detect_outliers(self.accel_window, ax[-1] if ax else 0)
        if outliers:
            idx = [t[i] for i in range(len(ax)) if i in outliers]
            vals = [ax[i] for i in range(len(ax)) if i in outliers]
            self.scat_accel.set_data(idx, vals)
        else:
            self.scat_accel.set_data([], [])

        # Speed
        sp = list(self.speed_data)
        self.line_speed.set_data(t[:len(sp)], sp)
        outliers = self._detect_outliers(self.speed_window, sp[-1] if sp else 0)
        if outliers:
            idx = [t[i] for i in range(len(sp)) if i in outliers]
            vals = [sp[i] for i in range(len(sp)) if i in outliers]
            self.scat_speed.set_data(idx, vals)
        else:
            self.scat_speed.set_data([], [])

        # 自适应 Y 轴范围
        for ax, data in [(self.ax1, gy), (self.ax2, ax), (self.ax3, sp)]:
            if data:
                margin = max(0.001, (max(data) - min(data)) * 0.1)
                ax.set_ylim(min(data) - margin, max(data) + margin)
            ax.set_xlim(max(0, self.counter - self.history), self.counter + 10)

        try:
            self.fig.canvas.draw_idle()
            self.fig.canvas.flush_events()
        except Exception:
            pass

    def _detect_outliers(self, window, value):
        """返回当前窗口中被标记为异常值的索引集合"""
        if len(window) < 10 or self.outlier_threshold <= 0:
            return set()
        arr = np.array(window)
        mean = np.mean(arr)
        std = np.std(arr)
        if std < 1e-12:
            return set()
        z = np.abs((arr - mean) / std)
        return set(np.where(z > self.outlier_threshold)[0])


def main():
    rclpy.init()
    node = SensorMonitorNode()
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.01)
            plt.pause(0.01)
            if not plt.fignum_exists(node.fig.number):
                break
    except KeyboardInterrupt:
        pass
    finally:
        plt.close('all')
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
