#!/usr/bin/env python3
"""1.2 数据分析 — EKF 传感器融合 v2 (IMU 预测 + 里程计位置更新)

订阅 /imu_data 和 /odom，用扩展卡尔曼滤波融合。

设计改进 (v2):
  - 预测: IMU 陀螺仪 Z → θ  (高频, 100Hz) + 里程计线速度 → x, y
  - 更新: 里程计位置 (x, y)   (低频, 5-10Hz, 但无漂移)
  
  这解决了 v1 中「odom 预测 θ + IMU 累积角度更新」的频率不匹配问题。

窗口:
  - 蓝色 = IMU 纯积分 (漂移)
  - 橙色 = 原始里程计
  - 绿色 = EKF 融合

用法:
  ros2 run ml_basics ekf_localization
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path
import numpy as np
import math

# ── matplotlib ──
import os as _os
_os.environ.setdefault('DISPLAY', ':0')
import matplotlib
matplotlib.use('TkAgg')
_os = None
import matplotlib.pyplot as plt


class EKFLocalizationNode(Node):
    """EKF v2: IMU gyro → heading prediction, odom position → update

    状态: [x, y, θ]
      pred:  IMU ω·dt → θ,  odom v·cos(θ)·dt → x,y
      update: odom (px, py)
    """

    def __init__(self):
        super().__init__('ekf_localization')

        self.declare_parameter('process_noise_v', 0.02)
        self.declare_parameter('process_noise_w', 0.01)
        self.declare_parameter('meas_noise_xy', 0.05)

        # ── EKF 状态 ──
        self.mu = np.zeros(3)
        self.Sigma = np.eye(3) * 0.01

        qv = self.get_parameter('process_noise_v').value
        qw = self.get_parameter('process_noise_w').value
        self.Q = np.diag([qv, qw])

        r_xy = self.get_parameter('meas_noise_xy').value
        self.R = np.diag([r_xy**2, r_xy**2])

        # ── 数据 ──
        self.last_v = 0.0
        self.last_predict_time = None

        self.traj_ekf  = [(0.0, 0.0)]
        self.traj_odom = [(0.0, 0.0)]
        self.traj_imu  = [(0.0, 0.0)]

        # IMU 纯积分
        self._theta_imu = 0.0
        self._px_imu = 0.0
        self._py_imu = 0.0
        self._last_imu_t = None

        # ── 订阅 ──
        self.imu_sub = self.create_subscription(
            Imu, '/imu_data', self.imu_callback, 10)
        self.odom_sub = self.create_subscription(
            Odometry, '/odom', self.odom_callback, 10)

        # ── 发布 ──
        self.ekf_path_pub = self.create_publisher(Path, '/ekf_trajectory', 10)

        # ── matplotlib ──
        self.fig, self.ax = plt.subplots(figsize=(9, 9))
        self.fig.canvas.manager.set_window_title('EKF v2 — IMU predict + Odom update')
        self.ax.set_xlabel('X (m)'); self.ax.set_ylabel('Y (m)')
        self.ax.grid(True, alpha=0.3)
        self.ax.axhline(y=0, color='gray', linewidth=0.5)
        self.ax.axvline(x=0, color='gray', linewidth=0.5)
        self.ax.set_aspect('equal')

        (self.line_imu,)  = self.ax.plot([], [], 'b-', linewidth=0.6, alpha=0.5, label='IMU dead reckoning')
        (self.line_odom,) = self.ax.plot([], [], 'orange', linewidth=0.8, alpha=0.6, label='Odom raw')
        (self.line_ekf,)  = self.ax.plot([], [], 'g-', linewidth=1.2, label='EKF fused')
        (self.dot_ekf,)   = self.ax.plot([], [], 'go', markersize=7)
        (self.dot_odom,)  = self.ax.plot([], [], 'o', color='orange', markersize=4, alpha=0.5)

        self.ax.legend(fontsize=8, loc='upper right')
        self.ax.set_title('EKF v2: (0.00, 0.00)  θ: 0.0°')

        plt.ion()
        self.fig.show()

        self._plot_cnt = 0
        self._odom_cnt = 0
        self._imu_cnt = 0
        self.diag_timer = self.create_timer(1.0, self._diag)

        self.get_logger().info('EKF v2 已启动 | IMU→θ预测 + Odom位置→更新')

    # ═══════════════════════ EKF ═══════════════════════

    def ekf_predict(self, v, w, dt):
        """预测: IMU ω → θ, odom v → x,y"""
        theta = self.mu[2]
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        self.mu[0] += v * cos_t * dt
        self.mu[1] += v * sin_t * dt
        self.mu[2] += w * dt

        # Jacobian G = ∂f/∂μ
        G = np.array([
            [1, 0, -v * sin_t * dt],
            [0, 1,  v * cos_t * dt],
            [0, 0,  1],
        ])
        # Control Jacobian V = ∂f/∂u
        V = np.array([
            [cos_t * dt, 0],
            [sin_t * dt, 0],
            [0,          dt],
        ])
        self.Sigma = G @ self.Sigma @ G.T + V @ self.Q @ V.T

    def ekf_update(self, x_meas, y_meas):
        """更新: 里程计位置观测 → 修正 x, y"""
        H = np.array([
            [1, 0, 0],
            [0, 1, 0],
        ], dtype=float)

        innovation = np.array([x_meas - self.mu[0], y_meas - self.mu[1]])
        S = H @ self.Sigma @ H.T + self.R
        K = self.Sigma @ H.T @ np.linalg.inv(S)
        self.mu += (K @ innovation).flatten()

        I3 = np.eye(3)
        self.Sigma = (I3 - K @ H) @ self.Sigma @ (I3 - K @ H).T + K @ self.R @ K.T

    # ═══════════════════════ 回调 ═══════════════════════

    def imu_callback(self, msg: Imu):
        """IMU: 驱动 θ 预测 (高频) + 纯积分轨迹"""
        now = self.get_clock().now().nanoseconds / 1e9
        if self._last_imu_t is None:
            self._last_imu_t = now
            return

        dt = now - self._last_imu_t
        self._last_imu_t = now
        if dt <= 0 or dt > 0.2:
            return

        w = msg.angular_velocity.z - 2.424e-5
        self._imu_cnt += 1

        # EKF 预测: 只用 IMU 角速度 + odom 线速度
        if self.last_predict_time is not None:
            self.ekf_predict(self.last_v, w, dt)
            self.last_predict_time = now

        # IMU 纯积分 (对比)
        self._theta_imu += w * dt
        self._px_imu += self.last_v * math.cos(self._theta_imu) * dt
        self._py_imu += self.last_v * math.sin(self._theta_imu) * dt
        self.traj_imu.append((self._px_imu, self._py_imu))

    def odom_callback(self, msg: Odometry):
        """里程计: 提供线速度 + 位置更新"""
        self.last_v = msg.twist.twist.linear.x
        self.last_predict_time = self.get_clock().now().nanoseconds / 1e9
        self._odom_cnt += 1

        # 里程计原始轨迹
        px = msg.pose.pose.position.x
        py = msg.pose.pose.position.y
        self.traj_odom.append((px, py))

        # EKF 更新: 用里程计位置
        self.ekf_update(px, py)

        # 记录 EKF 轨迹
        if (len(self.traj_ekf) == 0 or
            math.hypot(self.mu[0] - self.traj_ekf[-1][0],
                       self.mu[1] - self.traj_ekf[-1][1]) > 0.005):
            self.traj_ekf.append((self.mu[0], self.mu[1]))

        # 发布 Path
        path_msg = Path()
        path_msg.header.stamp = msg.header.stamp
        path_msg.header.frame_id = 'odom'
        for (x, y) in self.traj_ekf[-200:]:
            p = PoseStamped(); p.header = path_msg.header
            p.pose.position.x = float(x); p.pose.position.y = float(y)
            path_msg.poses.append(p)
        self.ekf_path_pub.publish(path_msg)

        # matplotlib
        self._plot_cnt += 1
        if self._plot_cnt % 2 == 0:
            self._update_plot()

    # ═══════════════════════ 诊断 ═══════════════════════

    def _diag(self):
        theta_deg = math.degrees(self.mu[2]) % 360
        self.get_logger().info(
            f'[DIAG] odom={self._odom_cnt}Hz imu={self._imu_cnt}Hz | '
            f'v={self.last_v:.3f} | '
            f'EKF=({self.mu[0]:.3f},{self.mu[1]:.3f}) θ={theta_deg:.1f}° | '
            f'Σ_pos=±{math.sqrt(self.Sigma[0,0]):.4f}m')
        self._odom_cnt = 0
        self._imu_cnt = 0

    # ═══════════════════════ 绘图 ═══════════════════════

    def _update_plot(self):
        try:
            for line, traj in [(self.line_imu, self.traj_imu),
                               (self.line_odom, self.traj_odom),
                               (self.line_ekf, self.traj_ekf)]:
                if len(traj) >= 2:
                    arr = np.array(traj)
                    line.set_data(arr[:, 0], arr[:, 1])

            if self.traj_ekf:
                arr = np.array(self.traj_ekf)
                self.dot_ekf.set_data([arr[-1, 0]], [arr[-1, 1]])
            if self.traj_odom:
                arr = np.array(self.traj_odom)
                self.dot_odom.set_data([arr[-1, 0]], [arr[-1, 1]])

            all_x, all_y = [], []
            for t in [self.traj_imu, self.traj_odom, self.traj_ekf]:
                if len(t) >= 2:
                    a = np.array(t)
                    all_x.extend(a[:, 0]); all_y.extend(a[:, 1])
            if all_x:
                mx = max(0.5, (max(all_x)-min(all_x))*0.15)
                my = max(0.5, (max(all_y)-min(all_y))*0.15)
                self.ax.set_xlim(min(all_x)-mx, max(all_x)+mx)
                self.ax.set_ylim(min(all_y)-my, max(all_y)+my)

            theta_deg = math.degrees(self.mu[2]) % 360
            self.ax.set_title(
                f'EKF v2: ({self.mu[0]:.2f},{self.mu[1]:.2f})  '
                f'θ={theta_deg:.1f}°  Σ=±{math.sqrt(self.Sigma[0,0]):.3f}m')
            self.fig.canvas.draw_idle()
            self.fig.canvas.flush_events()
        except Exception:
            pass


def main():
    rclpy.init()
    node = EKFLocalizationNode()
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
