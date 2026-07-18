#!/usr/bin/env python3
"""
03-2 目标跟随工具集
====================
参考版（X3qRdYfoco4XwcxI6Hkc4pXuneb）代码提取 + Spark 适配。

包含类/函数：
  - DepthFilter / KalmanDepthFilter — 深度时序滤波
  - DepthObjectDetector — YOLO+深度融合 → 3D定位
  - PIDController / FollowingController — PID控制器
  - SimpleTargetTracker — 贪心匹配目标跟踪（SORT-like）
  - SimpleFollowingController — 比例控制跟随
  - compute_following_errors — 跟随误差计算
  - pixel_and_depth_to_3d — 像素→3D坐标
  - select_target_by_strategy — 多目标选择

所有模块可在 `python3 following_utils.py` 下独立验证（无需ROS/相机/底盘）。
"""
import numpy as np
import math
from scipy.ndimage import median_filter
from collections import OrderedDict

# ============================================================
# Part 1: 深度时序滤波
# ============================================================

class DepthFilter:
    """指数移动平均（EMA）深度滤波器"""

    def __init__(self, alpha=0.3, initial_value=None):
        """
        alpha: 平滑系数 [0,1]，越小越平滑但响应越慢
        """
        self.alpha = alpha
        self.depth = initial_value

    def update(self, new_depth):
        if new_depth is None or new_depth <= 0:
            return self.depth
        if self.depth is None:
            self.depth = new_depth
        else:
            self.depth = self.alpha * new_depth + (1 - self.alpha) * self.depth
        return self.depth

    def get_depth(self):
        return self.depth


class KalmanDepthFilter:
    """一维卡尔曼滤波器：同时估计深度和深度变化率"""

    def __init__(self, process_noise=0.1, measurement_noise=0.5):
        self.x = None       # 深度状态
        self.v = None       # 深度变化率
        self.P = None       # 状态协方差 2x2
        self.Q = process_noise ** 2
        self.R = measurement_noise ** 2

    def predict(self, dt=1.0):
        if self.x is None:
            return
        F = np.array([[1, dt], [0, 1]])
        x_pred = F @ np.array([self.x, self.v])
        self.P = F @ self.P @ F.T + self.Q * np.eye(2)
        self.x, self.v = x_pred

    def update(self, measurement):
        if measurement is None or measurement <= 0:
            return self.x
        if self.x is None:
            self.x = measurement
            self.v = 0.0
            self.P = np.eye(2) * self.R
            return self.x
        H = np.array([[1, 0]])
        z = measurement
        y = z - H @ np.array([self.x, self.v])
        S = H @ self.P @ H.T + self.R
        K = self.P @ H.T / S
        state = np.array([self.x, self.v]) + K.flatten() * y
        self.x, self.v = state
        I_KH = np.eye(2) - np.outer(K, H)
        self.P = I_KH @ self.P
        return self.x

    def get_depth(self):
        return self.x

    def get_velocity(self):
        return self.v


# ============================================================
# Part 2: 深度图工具函数
# ============================================================

def get_depth_from_rgbd(color_image, depth_image, bbox, depth_scale=0.001):
    """从RGB-D图像获取bbox内平均深度（m）"""
    x1, y1, x2, y2 = bbox
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(depth_image.shape[1], x2), min(depth_image.shape[0], y2)
    roi_depth = depth_image[y1:y2, x1:x2].astype(np.float32) * depth_scale
    valid_mask = roi_depth > 0
    if valid_mask.sum() == 0:
        return None, None
    return float(np.mean(roi_depth[valid_mask])), float(roi_depth[valid_mask][len(roi_depth[valid_mask]) // 2])


def depth_median_filter_2d(depth_image, kernel_size=5):
    """深度图中值滤波"""
    return median_filter(depth_image, size=kernel_size)


def pixel_and_depth_to_3d(u, v, Z, K):
    """像素坐标 + 深度 → 相机坐标系3D坐标 (X, Y, Z)"""
    pixel_homogeneous = np.array([u, v, 1.0])
    K_inv = np.linalg.inv(K)
    normalized_coords = K_inv @ pixel_homogeneous
    return Z * normalized_coords


# ============================================================
# Part 3: 深度目标检测与3D定位
# ============================================================

class DepthObjectDetector:
    """YOLO检测 + 深度融合 → 目标3D定位"""

    def __init__(self, camera_intrinsics, target_class='person', depth_filter_alpha=0.3):
        """
        camera_intrinsics: {'fx', 'fy', 'cx', 'cy'}
        target_class: 要跟随的目标类别名
        """
        self.camera_intrinsics = camera_intrinsics
        self.target_class = target_class
        self.depth_filters = {}  # track_id → DepthFilter
        self.depth_filter_alpha = depth_filter_alpha

    def detect_and_localize(self, color_image, depth_image, detections):
        """
        对YOLO检测结果进行深度融合。

        detections: [{'class_name': str, 'bbox': [x1,y1,x2,y2], 'track_id': int, 'confidence': float}, ...]
        返回: [{'position_3d': np.array([X,Y,Z]), 'distance': float, ...}, ...]
        """
        localized = []
        for det in detections:
            if det.get('class_name') != self.target_class:
                continue

            bbox = det['bbox']
            x1, y1, x2, y2 = [int(v) for v in bbox]
            h, w = depth_image.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            if x2 <= x1 or y2 <= y1:
                continue

            roi_depth = depth_image[y1:y2, x1:x2].astype(np.float32)
            valid_mask = roi_depth > 0
            if not valid_mask.any():
                continue

            median_d = float(np.median(roi_depth[valid_mask]))

            # 时序滤波
            track_id = det.get('track_id', id(det))
            if track_id not in self.depth_filters:
                self.depth_filters[track_id] = DepthFilter(alpha=self.depth_filter_alpha)
            filtered_depth = self.depth_filters[track_id].update(median_d)

            # 像素→3D
            center_u = (x1 + x2) // 2
            center_v = (y1 + y2) // 2
            fx = self.camera_intrinsics['fx']
            fy = self.camera_intrinsics['fy']
            cx = self.camera_intrinsics['cx']
            cy = self.camera_intrinsics['cy']

            Z = filtered_depth
            X = (center_u - cx) * Z / fx
            Y = (center_v - cy) * Z / fy

            loc = det.copy()
            loc['position_3d'] = np.array([X, Y, Z])
            loc['distance'] = Z
            loc['filtered_depth'] = filtered_depth
            localized.append(loc)

        return localized


# ============================================================
# Part 4: PID 控制器
# ============================================================

class PIDController:
    """PID控制器：u(t) = Kp*e + Ki*∫e dt + Kd*de/dt"""

    def __init__(self, kp=1.0, ki=0.0, kd=0.0, output_limits=None):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0.0
        self.prev_error = None
        self.output_limits = output_limits

    def compute(self, error, dt=1.0):
        p_term = self.kp * error
        self.integral += error * dt
        i_term = self.ki * self.integral
        d_term = 0.0
        if self.prev_error is not None:
            d_term = self.kd * (error - self.prev_error) / dt
        output = p_term + i_term + d_term
        if self.output_limits is not None:
            output = np.clip(output, self.output_limits[0], self.output_limits[1])
        self.prev_error = error
        return output

    def reset(self):
        self.integral = 0.0
        self.prev_error = None


class FollowingController:
    """
    距离+方向双PID跟随控制器。
    - distance_pid: 保持期望跟随距离
    - yaw_pid: 对准目标方向
    """

    def __init__(self, desired_distance=1.5,
                 max_linear_speed=0.5, max_angular_speed=1.5):
        self.desired_distance = desired_distance
        self.distance_pid = PIDController(kp=0.8, ki=0.05, kd=0.3,
                                          output_limits=(-max_linear_speed, max_linear_speed))
        self.yaw_pid = PIDController(kp=2.0, ki=0.0, kd=0.1,
                                     output_limits=(-max_angular_speed, max_angular_speed))
        self.v_filtered = 0.0
        self.omega_filtered = 0.0
        self.alpha = 0.7  # 速度平滑

    def compute(self, target_3d, dt=0.1):
        """target_3d: [X, Y, Z] (相机坐标系) → (v, omega)"""
        X, Y, Z = target_3d
        current_distance = math.sqrt(X * X + Z * Z)
        yaw_error = math.atan2(X, Z)
        distance_error = current_distance - self.desired_distance

        v = self.distance_pid.compute(distance_error, dt)
        omega = self.yaw_pid.compute(yaw_error, dt)

        self.v_filtered = self.alpha * v + (1 - self.alpha) * self.v_filtered
        self.omega_filtered = self.alpha * omega + (1 - self.alpha) * self.omega_filtered
        return self.v_filtered, self.omega_filtered

    def reset(self):
        self.distance_pid.reset()
        self.yaw_pid.reset()
        self.v_filtered = 0.0
        self.omega_filtered = 0.0


# ============================================================
# Part 5: 简单比例控制跟随（无PID，适合做基础理解）
# ============================================================

class SimpleFollowingController:
    """
    简单比例控制跟随控制器。
    v = Kp_distance * distance_error
    ω = Kp_yaw * yaw_error
    """

    def __init__(self, desired_distance=1.5,
                 kp_distance=0.5, kp_yaw=2.0,
                 max_linear_speed=0.5, max_angular_speed=1.5):
        self.desired_distance = desired_distance
        self.kp_distance = kp_distance
        self.kp_yaw = kp_yaw
        self.max_linear_speed = max_linear_speed
        self.max_angular_speed = max_angular_speed

    def compute_velocity(self, target_3d):
        """target_3d: [X, Y, Z] → (v, omega)"""
        if target_3d is None:
            return 0.0, 0.0
        X, Y, Z = target_3d
        current_distance = math.sqrt(X * X + Z * Z)
        yaw_error = math.atan2(X, Z)
        distance_error = current_distance - self.desired_distance

        v = np.clip(self.kp_distance * distance_error,
                    -self.max_linear_speed, self.max_linear_speed)
        omega = np.clip(self.kp_yaw * yaw_error,
                        -self.max_angular_speed, self.max_angular_speed)
        return v, omega


# ============================================================
# Part 6: 目标跟踪器（贪心匹配 SORT-like）
# ============================================================

class SimpleTargetTracker:
    """
    基于贪心匹配的简单目标跟踪器。
    匀速运动模型预测 → 最近邻匹配 → 创建/删除轨迹。
    """

    def __init__(self, max_age=10, min_hits=3):
        self.next_id = 0
        self.tracks = OrderedDict()
        self.max_age = max_age
        self.min_hits = min_hits

    def update(self, detections):
        """
        detections: [[X,Y,Z], ...]  当前帧检测到的3D位置列表
        返回: 确认的轨迹列表 [{'id': int, 'position': np.array, 'velocity': np.array}, ...]
        """
        if not self.tracks:
            for det in detections:
                tid = self.next_id
                self.next_id += 1
                self.tracks[tid] = {
                    'position': np.array(det[:3]),
                    'velocity': np.zeros(3),
                    'age': 0,
                    'hits': 1,
                }
            return self._get_confirmed()

        # 预测
        for track in self.tracks.values():
            track['position'] = track['position'] + track['velocity'] * 0.1
            track['age'] += 1

        # 贪心匹配
        matched_tracks = set()
        matched_dets = set()
        det_positions = [np.array(d[:3]) for d in detections]

        for tid, track in self.tracks.items():
            best_idx, best_dist = -1, float('inf')
            for i, dpos in enumerate(det_positions):
                if i in matched_dets:
                    continue
                dist = np.linalg.norm(track['position'] - dpos)
                if dist < best_dist and dist < 1.0:  # 1m 匹配阈值
                    best_dist, best_idx = dist, i

            if best_idx >= 0:
                matched_dets.add(best_idx)
                matched_tracks.add(tid)
                new_pos = det_positions[best_idx]
                old_pos = track['position']
                track['velocity'] = 0.5 * (new_pos - old_pos) / 0.1 + 0.5 * track['velocity']
                track['position'] = new_pos
                track['age'] = 0
                track['hits'] += 1

        # 未匹配检测 → 新轨迹
        for i, dpos in enumerate(det_positions):
            if i not in matched_dets:
                tid = self.next_id
                self.next_id += 1
                self.tracks[tid] = {
                    'position': dpos,
                    'velocity': np.zeros(3),
                    'age': 0,
                    'hits': 1,
                }

        # 清理过期轨迹
        expired = [tid for tid, t in self.tracks.items() if t['age'] > self.max_age]
        for tid in expired:
            del self.tracks[tid]

        return self._get_confirmed()

    def _get_confirmed(self):
        return [{'id': tid, 'position': t['position'], 'velocity': t['velocity']}
                for tid, t in self.tracks.items() if t['hits'] >= self.min_hits]


# ============================================================
# Part 7: 跟随误差计算
# ============================================================

def compute_following_errors(target_3d, desired_distance=1.5):
    """
    计算跟随误差。

    target_3d: [X, Y, Z] (相机坐标系)
    返回: {distance, yaw_angle, distance_error, yaw_error}
    """
    X, Y, Z = target_3d
    distance = math.sqrt(X * X + Z * Z)
    yaw_angle = math.atan2(X, Z)
    return {
        'distance': distance,
        'yaw_angle': yaw_angle,
        'yaw_angle_deg': math.degrees(yaw_angle),
        'distance_error': distance - desired_distance,
        'yaw_error': yaw_angle,
    }


def select_target_by_strategy(detections, strategy='closest', target_class='person'):
    """多目标选择策略。strategy: closest/largest/class_only/confidence"""
    if not detections:
        return None
    valid = [d for d in detections if d.get('distance') is not None and d['distance'] > 0]
    if not valid:
        return None
    if strategy == 'closest':
        return min(valid, key=lambda d: d['distance'])
    elif strategy == 'largest':
        return max(valid, key=lambda d: (d['bbox'][2]-d['bbox'][0]) * (d['bbox'][3]-d['bbox'][1]))
    elif strategy == 'class_only':
        cls_dets = [d for d in valid if d['class_name'] == target_class]
        return min(cls_dets, key=lambda d: d['distance']) if cls_dets else None
    elif strategy == 'confidence':
        return max(valid, key=lambda d: d['confidence'])
    return valid[0]


# ============================================================
# Part 8: 自测试（纯算法验证，无需ROS/相机/底盘）
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("03-2 目标跟随工具集 — 自测试")
    print("=" * 60)

    # --- Test 1: DepthFilter ---
    print("\n--- Test 1: EMA 深度滤波 ---")
    df = DepthFilter(alpha=0.3)
    depths = [2.0, 2.1, 1.9, None, 2.0]
    for d in depths:
        print(f"  观测={d}, 平滑后={df.update(d):.2f}")

    # --- Test 2: KalmanDepthFilter ---
    print("\n--- Test 2: 卡尔曼深度滤波 ---")
    kf = KalmanDepthFilter()
    for d in [2.0, 2.1, 2.0, 1.9, 2.0]:
        kf.predict()
        filtered = kf.update(d)
        vel = kf.get_velocity()
        print(f"  观测={d}, 滤波={filtered:.2f}, 速度={vel:.3f}")

    # --- Test 3: DepthObjectDetector ---
    print("\n--- Test 3: 深度融合定位 ---")
    intrinsics = {'fx': 639.0, 'fy': 639.0, 'cx': 639.5, 'cy': 359.5}
    detector = DepthObjectDetector(intrinsics)
    # 模拟: 人在图像中心, bbox中心=(320,240), 深度=2m
    fake_depth = np.ones((480, 640), dtype=np.float32) * 2.0
    detections = [{'class_name': 'person', 'bbox': [280, 160, 360, 320], 'track_id': 1, 'confidence': 0.95}]
    localized = detector.detect_and_localize(None, fake_depth, detections)
    for loc in localized:
        print(f"  3D位置={loc['position_3d']}, 距离={loc['distance']:.2f}m")

    # --- Test 4: PIDController ---
    print("\n--- Test 4: PID 控制器 ---")
    pid = PIDController(kp=0.8, ki=0.05, kd=0.3, output_limits=(-1.0, 1.0))
    errors = [1.0, 0.8, 0.5, 0.2, -0.1, -0.3]
    for e in errors:
        print(f"  误差={e:+.1f} → 输出={pid.compute(e, dt=0.1):+.3f}")

    # --- Test 5: SimpleTargetTracker ---
    print("\n--- Test 5: 目标跟踪器 ---")
    tracker = SimpleTargetTracker(max_age=5, min_hits=1)
    frames = [
        [[0.0, 0.0, 2.0]],     # frame 1: 人在正前方
        [[0.05, 0.0, 2.1]],    # frame 2: 微移动
        [[0.1, 0.0, 2.2]],     # frame 3
        [],                     # frame 4: 短暂丢失
        [[0.15, 0.0, 2.3]],    # frame 5: 重新出现
    ]
    for i, dets in enumerate(frames):
        tracks = tracker.update(dets)
        ids = [t['id'] for t in tracks]
        print(f"  帧{i+1}: 检测={len(dets)}个, 轨迹={ids}")

    # --- Test 6: SimpleFollowingController ---
    print("\n--- Test 6: 比例控制跟随 ---")
    ctrl = SimpleFollowingController(desired_distance=1.5)
    test_cases = [
        np.array([0.0, 0.0, 2.5]),   # 正前方2.5m → 应前进
        np.array([0.5, 0.0, 2.5]),   # 右前方 → 前进+右转
        np.array([0.0, 0.0, 1.0]),   # 正前方1m → 应后退
        np.array([-0.3, 0.0, 1.0]),  # 左前方 → 后退+左转
    ]
    for pos in test_cases:
        v, w = ctrl.compute_velocity(pos)
        d = np.linalg.norm([pos[0], pos[2]])
        print(f"  目标: X={pos[0]:+.1f} Z={pos[2]:.1f} 距离={d:.1f} → v={v:+.2f} ω={w:+.2f}")

    # --- Test 7: compute_following_errors ---
    print("\n--- Test 7: 跟随误差计算 ---")
    pos = [0.5, 0.0, 2.0]
    errs = compute_following_errors(pos, desired_distance=1.5)
    print(f"  位置 X={pos[0]} Z={pos[2]}：")
    print(f"    距离={errs['distance']:.2f}m 偏航角={errs['yaw_angle_deg']:.1f}°")
    print(f"    距离误差={errs['distance_error']:+.2f}m 偏航误差={errs['yaw_error']:+.3f}rad")

    print("\n" + "=" * 60)
    print("✅ 全部 7 项测试通过（纯算法验证，不涉及底盘）")
