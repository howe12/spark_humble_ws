#!/usr/bin/env python3
"""1.2 数据分析 — ESKF 误差状态卡尔曼滤波 (IMU + 里程计)

Error-State Kalman Filter: 在「误差状态」上运行 KF，而非「全状态」。
- 名义状态 (nominal): 直接积分，可能很大 → [x, y, θ]
- 误差状态 (error):  始终接近零，线性化更准 → [δx, δy, δθ, δb_g]
- 注入 (injection):  每次更新后把误差注入名义状态，误差清零

对比普通 EKF:
  EKF 直接在 [x, y, θ] 上线性化 → 状态偏离时 Jacobian 不准
  ESKF 在 [δx≈0, δy≈0, ...] 上线性化 → 始终在零点展开, 精度更高

窗口显示:
  - 蓝色 = IMU 纯积分 (漂移)
  - 橙色 = 原始里程计
  - 绿色 = EKF 融合 (3D 状态)
  - 红色 = ESKF 融合 (在线估计陀螺仪偏置) ← 更平滑

用法:
  ros2 run ml_basics eskf_localization
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


class ESKFLocalizationNode(Node):
    """ESKF: Error-State Kalman Filter for 2D ground robot

    ┌─────────────────────────────────────────────┐
    │  名义状态 (直接积分):  x, y, θ               │
    │  误差状态 (KF 估计):    δx, δy, δθ, δb_g    │
    │                                                 │
    │  预测: IMU (ω - b_g) → θ, 里程计 v → x,y      │
    │  更新: 里程计位置观测                           │
    │  注入: 每次更新后 μ_nom += δμ, δμ = 0          │
    └─────────────────────────────────────────────┘
    """

    def __init__(self):
        super().__init__('eskf_localization')

        # ── 参数 ──
        self.declare_parameter('gyro_noise', 0.003)        # 陀螺仪噪声 (rad/s/√Hz)
        self.declare_parameter('gyro_bias_noise', 1e-5)    # 陀螺仪偏置游走
        self.declare_parameter('pos_meas_noise', 0.05)     # 里程计位置测量噪声 (m)

        # ── 名义状态: [x, y, θ] ──
        self.nom = np.zeros(3)    # x, y, θ
        self.b_g = 0.0            # 陀螺仪偏置 (由 ESKF 在线估计)

        # ── 误差状态协方差: [δx, δy, δθ, δb_g]  4×4 ──
        self.P = np.eye(4) * 0.01

        # ── 过程噪声 (误差状态空间) ──
        q_gyro = self.get_parameter('gyro_noise').value
        q_bias = self.get_parameter('gyro_bias_noise').value
        self.Q_d = np.diag([q_gyro**2, q_bias**2])   # [ω噪声, 偏置游走]

        # ── 测量噪声 ──
        r_pos = self.get_parameter('pos_meas_noise').value
        self.R = np.diag([r_pos**2, r_pos**2])        # 观测 x, y

        # ── 数据 ──
        self.last_time = None
        self.last_v = 0.0

        # 轨迹
        self.traj_eskf = [(0.0, 0.0)]
        self.traj_ekf  = [(0.0, 0.0)]
        self.traj_odom = [(0.0, 0.0)]
        self.traj_imu  = [(0.0, 0.0)]

        # EKF 对比（与 ekf_localization.py 相同算法）
        self.ekf_mu = np.zeros(3)
        self.ekf_Sigma = np.eye(3) * 0.01
        self.ekf_Q = np.diag([0.01, 0.05])
        self.ekf_R = np.array([[0.02]])

        # IMU 纯积分
        self.theta_imu = 0.0
        self.px_imu = 0.0
        self.py_imu = 0.0

        # ── 订阅 ──
        self.imu_sub = self.create_subscription(
            Imu, '/imu_data', self.imu_callback, 10)
        self.odom_sub = self.create_subscription(
            Odometry, '/odom', self.odom_callback, 10)

        # ── 发布 ──
        self.eskf_path_pub = self.create_publisher(Path, '/eskf_trajectory', 10)

        # ── matplotlib ──
        self.fig, self.ax = plt.subplots(figsize=(10, 10))
        self.fig.canvas.manager.set_window_title('ESKF Localization — Error-State KF')
        self.ax.set_xlabel('X (m)')
        self.ax.set_ylabel('Y (m)')
        self.ax.grid(True, alpha=0.3)
        self.ax.axhline(y=0, color='gray', linewidth=0.5)
        self.ax.axvline(x=0, color='gray', linewidth=0.5)
        self.ax.set_aspect('equal')

        (self.line_imu,)  = self.ax.plot([], [], 'b-',  linewidth=0.5, alpha=0.4, label='IMU dead reckoning')
        (self.line_odom,) = self.ax.plot([], [], 'orange', linewidth=0.7, alpha=0.5, label='Odom raw')
        (self.line_ekf,)  = self.ax.plot([], [], 'g-',  linewidth=1.0, alpha=0.7, label='EKF (3D)')
        (self.line_eskf,) = self.ax.plot([], [], 'r-',  linewidth=1.5, label='ESKF (4D error-state)')

        self.dot_eskf, = self.ax.plot([], [], 'ro', markersize=8)
        self.dot_ekf,  = self.ax.plot([], [], 'go', markersize=5, alpha=0.6)

        self.ax.legend(fontsize=8, loc='upper right')
        self.ax.set_title('ESKF: (0.00, 0.00)  θ: 0.0°  b_g: 0.0e+00')

        plt.ion()
        self.fig.show()
        self.plot_counter = 0
        self.get_logger().info('ESKF 已启动 | 等待 /imu_data + /odom ...')

    # ═══════════════════════════════════════════
    #  ESKF 核心算法
    # ═══════════════════════════════════════════

    def eskf_predict(self, v, w_meas, dt):
        """ESKF 预测步骤

        名义状态 (直接积分):
          θ' = θ + (ω_meas - b_g)·dt
          x' = x + v·cos(θ)·dt
          y' = y + v·sin(θ)·dt

        误差状态转移矩阵 F (4×4):
          δx' = δx - v·sin(θ)·dt·δθ
          δy' = δy + v·cos(θ)·dt·δθ
          δθ' = δθ - dt·δb_g
          δb_g' = δb_g

        即 F = [[1, 0, -v·sin(θ)·dt, 0   ],
                [0, 1,  v·cos(θ)·dt, 0   ],
                [0, 0,  1,           -dt ],
                [0, 0,  0,            1  ]]

        噪声注入矩阵 G (4×2):
          δθ  ← dt·n_gyro     (陀螺仪白噪声)
          δb_g ← dt·n_bias    (偏置随机游走)

        即 G = [[0,        0     ],
                [0,        0     ],
                [dt,       0     ],
                [0,        dt    ]]
        """
        theta = self.nom[2]
        w_corrected = w_meas - self.b_g
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        # 名义状态预测
        self.nom[0] += v * cos_t * dt
        self.nom[1] += v * sin_t * dt
        self.nom[2] += w_corrected * dt

        # ── 误差状态协方差预测 ──
        # F (4×4): 误差状态转移矩阵
        F = np.eye(4)
        F[0, 2] = -v * sin_t * dt
        F[1, 2] =  v * cos_t * dt
        F[2, 3] = -dt

        # G (4×2): 噪声注入矩阵
        G = np.zeros((4, 2))
        G[2, 0] = dt    # gyro noise → δθ
        G[3, 1] = dt    # bias random walk → δb_g

        # 协方差传播: P = F·P·Fᵀ + G·Q·Gᵀ
        self.P = F @ self.P @ F.T + G @ self.Q_d @ G.T

    def eskf_update(self, x_meas, y_meas):
        """ESKF 更新步骤：用里程计位置观测修正

        观测模型: z = [x_nom + δx, y_nom + δy]ᵀ + noise
        观测 Jacobian H (2×4):
          H = [[1, 0, 0, 0],
               [0, 1, 0, 0]]

        创新: y = z_meas - h(x_nom)
        卡尔曼增益: K = P·Hᵀ·(H·P·Hᵀ + R)⁻¹
        误差状态更新: δx_err = K·y
        注入: x_nom += δx_err[:3];  b_g += δx_err[3]
        协方差更新: P = (I - K·H)·P
        """
        H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
        ], dtype=float)

        # 创新 (测量 - 预测)
        innovation = np.array([
            x_meas - self.nom[0],
            y_meas - self.nom[1],
        ])

        # 卡尔曼增益
        S = H @ self.P @ H.T + self.R                         # 2×2
        K = self.P @ H.T @ np.linalg.inv(S)                   # 4×2

        # 误差状态修正
        dx = K @ innovation                                    # 4×1

        # ── 注入 (injection) ──
        self.nom[0] += dx[0]    # x
        self.nom[1] += dx[1]    # y
        self.nom[2] += dx[2]    # θ
        self.b_g    += dx[3]    # 陀螺仪偏置

        # 协方差更新 (Joseph 形式)
        I4 = np.eye(4)
        self.P = (I4 - K @ H) @ self.P @ (I4 - K @ H).T + K @ self.R @ K.T

        # ── 误差状态重置 ── (ESKF 关键步骤!)
        # 误差已注入名义状态，误差均值归零
        # 协方差需相应调整 (这里用简化版本直接保持)

    # ═══════════════════════════════════════════
    #  回调
    # ═══════════════════════════════════════════

    def imu_callback(self, msg: Imu):
        """IMU: 驱动 ESKF 预测 + 纯积分轨迹"""
        now = self.get_clock().now().nanoseconds / 1e9

        if not hasattr(self, '_last_imu_time'):
            self._last_imu_time = now
            self._imu_theta = 0.0
            return

        dt = now - self._last_imu_time
        self._last_imu_time = now
        if dt <= 0 or dt > 0.1:
            return

        w_imu = msg.angular_velocity.z

        # ESKF 预测
        self.eskf_predict(self.last_v, w_imu, dt)

        # EKF 对比预测
        self._ekf_predict(self.last_v, w_imu, dt)

        # IMU 纯积分
        self._imu_theta += (w_imu - 2.424e-5) * dt
        if self.last_v != 0:
            self.px_imu += self.last_v * math.cos(self._imu_theta) * dt
            self.py_imu += self.last_v * math.sin(self._imu_theta) * dt
            self.traj_imu.append((self.px_imu, self.py_imu))

    def odom_callback(self, msg: Odometry):
        """里程计: 提供速度 + ESKF 位置更新"""
        self.last_v = msg.twist.twist.linear.x
        self.last_w = msg.twist.twist.angular.z

        px = msg.pose.pose.position.x
        py = msg.pose.pose.position.y

        # 里程计原始轨迹
        self.traj_odom.append((px, py))

        # ESKF 更新
        self.eskf_update(px, py)

        # EKF 对比更新
        self._ekf_update(self._imu_theta)

        # 记录轨迹
        self.traj_eskf.append((self.nom[0], self.nom[1]))
        self.traj_ekf.append((self.ekf_mu[0], self.ekf_mu[1]))

        # ── 发布 Path ──
        path_msg = Path()
        path_msg.header.stamp = msg.header.stamp
        path_msg.header.frame_id = 'odom'
        for (x, y) in self.traj_eskf[-200:]:
            p = PoseStamped(); p.header = path_msg.header
            p.pose.position.x = float(x); p.pose.position.y = float(y)
            path_msg.poses.append(p)
        self.eskf_path_pub.publish(path_msg)

        # matplotlib
        self.plot_counter += 1
        if self.plot_counter % 3 == 0:
            self._update_plot()

    # ═══════════════════════════════════════════
    #  EKF 对比 (与 ekf_localization.py 相同)
    # ═══════════════════════════════════════════

    def _ekf_predict(self, v, w, dt):
        theta = self.ekf_mu[2]
        self.ekf_mu[0] += v * math.cos(theta) * dt
        self.ekf_mu[1] += v * math.sin(theta) * dt
        self.ekf_mu[2] += (w - 2.424e-5) * dt
        G = np.array([
            [1, 0, -v * math.sin(theta) * dt],
            [0, 1,  v * math.cos(theta) * dt],
            [0, 0,  1],
        ])
        V = np.array([[math.cos(theta)*dt, 0], [math.sin(theta)*dt, 0], [0, dt]])
        self.ekf_Sigma = G @ self.ekf_Sigma @ G.T + V @ self.ekf_Q @ V.T

    def _ekf_update(self, theta_meas):
        H = np.array([[0, 0, 1]])
        innov = theta_meas - self.ekf_mu[2]
        innov = math.atan2(math.sin(innov), math.cos(innov))
        S = H @ self.ekf_Sigma @ H.T + self.ekf_R
        K = self.ekf_Sigma @ H.T @ np.linalg.inv(S)
        self.ekf_mu += (K @ np.array([innov])).flatten()
        I = np.eye(3)
        self.ekf_Sigma = (I - K @ H) @ self.ekf_Sigma @ (I - K @ H).T + K @ self.ekf_R @ K.T

    # ═══════════════════════════════════════════
    #  绘图
    # ═══════════════════════════════════════════

    def _update_plot(self):
        try:
            for line, traj in [
                (self.line_imu,  self.traj_imu),
                (self.line_odom, self.traj_odom),
                (self.line_ekf,  self.traj_ekf),
                (self.line_eskf, self.traj_eskf),
            ]:
                if len(traj) >= 2:
                    arr = np.array(traj)
                    line.set_data(arr[:, 0], arr[:, 1])

            if len(self.traj_eskf) >= 1:
                arr = np.array(self.traj_eskf)
                self.dot_eskf.set_data([arr[-1, 0]], [arr[-1, 1]])
            if len(self.traj_ekf) >= 1:
                arr = np.array(self.traj_ekf)
                self.dot_ekf.set_data([arr[-1, 0]], [arr[-1, 1]])

            all_x, all_y = [], []
            for traj in [self.traj_imu, self.traj_odom, self.traj_ekf, self.traj_eskf]:
                if len(traj) >= 2:
                    arr = np.array(traj)
                    all_x.extend(arr[:, 0]); all_y.extend(arr[:, 1])
            if all_x:
                mx = max(0.5, (max(all_x)-min(all_x))*0.15)
                my = max(0.5, (max(all_y)-min(all_y))*0.15)
                self.ax.set_xlim(min(all_x)-mx, max(all_x)+mx)
                self.ax.set_ylim(min(all_y)-my, max(all_y)+my)

            theta_deg = math.degrees(self.nom[2]) % 360
            self.ax.set_title(
                f'ESKF: ({self.nom[0]:.2f}, {self.nom[1]:.2f})  '
                f'θ: {theta_deg:.1f}°  |  b_g: {self.b_g:.2e}  |  '
                f'σ=±{math.sqrt(self.P[0,0]):.3f}m')

            self.fig.canvas.draw_idle()
            self.fig.canvas.flush_events()
        except Exception:
            pass


def main():
    rclpy.init()
    node = ESKFLocalizationNode()
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
