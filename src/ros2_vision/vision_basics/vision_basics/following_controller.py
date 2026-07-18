#!/usr/bin/env python3
"""03-2 深度跟随: P → PID 跟随控制器（分块教学版）

三步递进，每步可独立运行验证：
  第1步 SimpleFollowingController  — P 比例控制
  第2步 PIDController              — PID 控制（消除稳态误差）
  第3步 ObjectFollowingController  — 多目标处理 + 安全限幅

用法:
  python3 following_controller.py
"""

import numpy as np
import math


# ═══════════════════════ 第1步: P 比例控制 ═══════════════════════

class SimpleFollowingController:
    """比例控制跟随器

    控制律:
      v = Kp_dist * (当前距离 - 期望距离)
      ω = Kp_yaw  * 目标偏航角

    问题: 到达期望距离后 v→0，但有稳态误差
    """

    def __init__(self, desired_distance=1.5,
                 kp_distance=0.5, kp_yaw=2.0,
                 max_linear=0.5, max_angular=1.5):
        self.desired = desired_distance
        self.kp_d = kp_distance
        self.kp_y = kp_yaw
        self.max_v = max_linear
        self.max_w = max_angular

    def compute(self, target_3d):
        """target_3d: [X, Y, Z] — X=左右, Z=前方(m)"""
        if target_3d is None:
            return 0.0, 0.0

        X, _, Z = target_3d
        dist = math.hypot(X, Z)
        yaw = math.atan2(X, Z)

        v = np.clip(self.kp_d * (dist - self.desired), -self.max_v, self.max_v)
        w = np.clip(self.kp_y * yaw, -self.max_w, self.max_w)
        return float(v), float(w)


# ═══════════════════════ 第2步: PID 控制 ═══════════════════════

class PIDController:
    """离散 PID 控制器

    u(t) = Kp·e(t) + Ki·Σe(t)·dt + Kd·(e(t)-e(t-1))/dt
    """

    def __init__(self, kp=1.0, ki=0.0, kd=0.0, max_out=1.0):
        self.kp = kp; self.ki = ki; self.kd = kd
        self.max_out = max_out
        self.reset()

    def reset(self):
        self.prev_err = 0.0
        self.integral = 0.0

    def compute(self, error, dt=0.1):
        self.integral += error * dt
        derivative = (error - self.prev_err) / dt if dt > 0 else 0.0
        self.prev_err = error
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        return np.clip(output, -self.max_out, self.max_out)


class PIDFollowingController:
    """PID 跟随器 — 距离用 PID，偏航用 P

    改进: 用 PID 消除距离稳态误差
    """

    def __init__(self, desired_distance=1.5,
                 kp_dist=0.5, ki_dist=0.1, kd_dist=0.05,
                 kp_yaw=2.0,
                 max_linear=0.5, max_angular=1.5):
        self.desired = desired_distance
        self.pid_dist = PIDController(kp_dist, ki_dist, kd_dist, max_linear)
        self.kp_y = kp_yaw
        self.max_w = max_angular

    def compute(self, target_3d, dt=0.1):
        if target_3d is None:
            self.pid_dist.reset()
            return 0.0, 0.0

        X, _, Z = target_3d
        dist = math.hypot(X, Z)
        yaw = math.atan2(X, Z)

        v = self.pid_dist.compute(dist - self.desired, dt)
        w = np.clip(self.kp_y * yaw, -self.max_w, self.max_w)
        return float(v), float(w)


# ═══════════════════════ 第3步: 多目标 + 安全限幅 ═══════════════════════

class ObjectFollowingController:
    """多目标跟随控制器 + 安全策略

    新增:
      - 多目标选最近 (closest-first)
      - 过近停转 (distance < 0.5m → stop)
      - 后退保护 (不后退，离太近比撞上好)
    """

    def __init__(self, desired_distance=1.5,
                 kp_dist=0.5, ki_dist=0.05, kd_dist=0.02,
                 kp_yaw=2.0,
                 min_safe_distance=0.5,
                 max_linear=0.5, max_angular=1.5):
        self.desired = desired_distance
        self.pid_dist = PIDController(kp_dist, ki_dist, kd_dist, max_linear)
        self.kp_y = kp_yaw
        self.min_safe = min_safe_distance
        self.max_v = max_linear
        self.max_w = max_angular

    def compute(self, targets_3d, dt=0.1):
        """
        targets_3d: 多目标列表 [[X,Y,Z], ...] 或单个 [X,Y,Z] 或 None
        返回: (v, w, target_idx)
        """
        if targets_3d is None or len(targets_3d) == 0:
            self.pid_dist.reset()
            return 0.0, 0.0, -1

        # 标准化为列表
        if isinstance(targets_3d, np.ndarray) and targets_3d.ndim == 1:
            targets_3d = [targets_3d]

        # 选最近的目标
        best_idx = 0
        best_dist = float('inf')
        for i, t in enumerate(targets_3d):
            d = math.hypot(t[0], t[2])
            if d < best_dist:
                best_dist = d
                best_idx = i

        X, _, Z = targets_3d[best_idx]
        dist = best_dist
        yaw = math.atan2(X, Z)

        # 安全: 过近停转
        if dist < self.min_safe:
            return 0.0, 0.0, best_idx

        v_raw = self.pid_dist.compute(dist - self.desired, dt)
        # 不准后退
        v = max(0.0, min(v_raw, self.max_v))
        w = np.clip(self.kp_y * yaw, -self.max_w, self.max_w)
        return float(v), float(w), best_idx


# ═══════════════════════ 测试 ═══════════════════════

def demo():
    print("=" * 55)
    print("03-2 跟随控制器: P → PID → 多目标安全跟随")
    print("=" * 55)

    test_targets = [
        ("右前方 2.5m", [0.3, 0.0, 2.5]),
        ("正前方 1.2m", [0.0, 0.0, 1.2]),
        ("左前方 3.0m", [-0.5, 0.0, 3.0]),
        ("过近 0.4m",   [0.2, 0.0, 0.35]),
    ]

    # ── 第1步: P 控制 ──
    print("\n第1步: SimpleFollowingController (P 控制)")
    p_ctrl = SimpleFollowingController(desired_distance=1.5)
    for name, pos in test_targets:
        v, w = p_ctrl.compute(pos)
        d = math.hypot(pos[0], pos[2])
        a = math.degrees(math.atan2(pos[0], pos[2]))
        print(f"  {name:16s} dist={d:.2f}m yaw={a:+.1f}° → v={v:+.3f} w={w:+.3f}")

    # ── 第2步: PID 控制 ──
    print("\n第2步: PIDFollowingController (PID 控制)")
    pid_ctrl = PIDFollowingController(desired_distance=1.5)
    # 连续步骤模拟
    for name, pos in test_targets[:2] * 2:
        v, w = pid_ctrl.compute(pos)
        d = math.hypot(pos[0], pos[2])
        print(f"  {name:16s} dist={d:.2f}m → v={v:+.3f} w={w:+.3f}")

    # ── 第3步: 多目标安全 ──
    print("\n第3步: ObjectFollowingController (多目标+安全)")
    safe_ctrl = ObjectFollowingController(desired_distance=1.5)
    all_targets = [[0.3, 0, 2.5], [0.0, 0, 1.2], [0.2, 0, 0.35]]
    v, w, idx = safe_ctrl.compute(all_targets)
    print(f"  3个目标 → 选最近(idx={idx}) → v={v:+.3f} w={w:+.3f}")
    print(f"  (其中过近目标 0.4m 被安全规则过滤)")

    print("\n✅ 三步完成。将控制器嵌入 ROS2 节点即可驱动机器人。")


if __name__ == '__main__':
    demo()
