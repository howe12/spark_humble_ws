#!/usr/bin/env python3
"""03-2 深度跟随: ROS2 可视化演示节点 — RGB+深度双画面 + ROI + 运动控制显示

数据源: aligned 深度图反投影 (方案 A — 与 RGB 像素完美对齐)
  /camera/aligned_depth_to_color/image_raw 是 16UC1 毫米,
  除以 1000 转米, 用【彩色内参】反投影得到彩色坐标系 3D 点 (x,y,z),
  这样质心/ROI/深度统计 与 RGB 图像像素一一对应, 无投影偏移。

  (对比: 点云 /camera/depth/color/points 是 depth 坐标系,
   直接套彩色内参投影会偏移 100+px —— 已弃用)

流程:
  1. 深度图 → 3D 点 (彩色坐标系) → ROI 过滤 → 离群剔除 → 质心/深度统计
  2. 左侧画面 : RGB + ROI 3D 框 + 质心红点 + 运动控制箭头
  3. 右侧画面 : 深度热力图 + ROI 像素高亮
  4. 底部控制栏: 动作指令 + cmd_vel 数值
  5. 仅显示, 不发布 cmd_vel (教学演示, 不驱动底盘)

运行:
  终端1: ros2 launch camera_driver_transfer d435.launch.py
  终端2: ros2 run vision_basics depth_roi_demo_node
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge
import cv2
import numpy as np

from vision_basics.depth_roi_demo import (analyze_roi, decide_motion,
                                          ROI_X_MIN, ROI_X_MAX,
                                          ROI_Z_MIN, ROI_Z_MAX,
                                          ROI_Y_MIN, ROI_Y_MAX,
                                          GOAL_DEPTH, MIN_POINTS)

# 深度显示范围 (m)
DEPTH_CLIP = 3.0


class DepthRoiDemoNode(Node):
    def __init__(self):
        super().__init__('depth_roi_demo_node')

        self.bridge = CvBridge()
        self.rgb_image = None
        self.depth_image = None   # 米, 32FC1 (已 /1000)
        self.fx = self.fy = 0.0   # 彩色内参
        self.cx = self.cy = 0.0

        # ── 话题名 (可参数覆盖; 默认匹配实测单层 /camera/...) ──
        self.declare_parameter('rgb_topic', '/camera/color/image_raw')
        self.declare_parameter('depth_topic',
                               '/camera/aligned_depth_to_color/image_raw')
        self.declare_parameter('info_topic', '/camera/color/camera_info')
        # ── 深度判断模式: mean(均值/质心) / median(中值, 默认) / min(最近点) ──
        self.declare_parameter('depth_mode', 'median')
        # ── 离群点剔除: none / zscore(默认) / iqr / percentile ──
        self.declare_parameter('filter_method', 'zscore')

        # ── 订阅者 (仅订阅, 无发布) ──
        self.rgb_sub = self.create_subscription(
            Image,
            self.get_parameter('rgb_topic').value,
            self.rgb_cb, 10)
        self.depth_sub = self.create_subscription(
            Image,
            self.get_parameter('depth_topic').value,
            self.depth_cb, 10)
        self.info_sub = self.create_subscription(
            CameraInfo,
            self.get_parameter('info_topic').value,
            self.info_cb, 10)

        self.get_logger().info(
            f'深度跟随可视化启动(方案A:深度图反投影): goal={GOAL_DEPTH}m '
            f'ROI X∈[{ROI_X_MIN},{ROI_X_MAX}] '
            f'Z∈[{ROI_Z_MIN},{ROI_Z_MAX}] Y∈[{ROI_Y_MIN},{ROI_Y_MAX}]')
        self.get_logger().info(
            f'订阅: {self.get_parameter("rgb_topic").value} | '
            f'{self.get_parameter("depth_topic").value}')

    def info_cb(self, msg):
        self.fx, self.fy = msg.k[0], msg.k[4]
        self.cx, self.cy = msg.k[2], msg.k[5]

    def rgb_cb(self, msg):
        self.rgb_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

    def depth_cb(self, msg):
        # 注意: aligned_depth_to_color 是 16UC1 毫米 → 转米
        # (不除以 1000 会导致: clip(0,3) 后全红, ROI 掩码全失效)
        self.depth_image = self.bridge.imgmsg_to_cv2(msg, '32FC1') / 1000.0
        self.process_frame()

    # ================= 核心处理 =================

    def depth_to_points(self):
        """aligned 深度图 → 3D 点数组 (彩色坐标系, 米)

        反投影公式 (教学点):
          点云.x = (u - cx) × z / fx
          点云.y = (v - cy) × z / fy
          点云.z = z                     (深度图存的 z)

        返回: (N,3) float32, 已过滤无效深度 (z<=0.05 或 NaN)
        """
        z = self.depth_image
        h, w = z.shape
        u = np.arange(w)
        v = np.arange(h)
        U, V = np.meshgrid(u, v)  # (h, w)

        X = (U - self.cx) * z / self.fx
        Y = (V - self.cy) * z / self.fy

        valid = (z > 0.05) & (z < DEPTH_CLIP) & np.isfinite(z)
        pts = np.stack([X, Y, z], axis=-1)  # (h,w,3)
        return pts[valid].astype(np.float32)

    def process_frame(self):
        """深度图 → 点 → ROI 统计 → 运动控制 → 可视化 (测试可直接调用)"""
        if (self.depth_image is None or self.rgb_image is None
                or self.fx == 0):
            return

        # ── 1. 深度图 → 3D 点 (彩色坐标系) ──
        points = self.depth_to_points()
        if len(points) == 0:
            return

        # ── 2. 3D ROI 提取 + 离群点剔除 + 深度统计 ──
        filter_method = self.get_parameter('filter_method').value
        res = analyze_roi(points, filter_method=filter_method)

        # ── 3. 按模式选控制深度 ──
        mode = self.get_parameter('depth_mode').value
        depth_control = {
            'mean': res['depth_mean'],
            'median': res['depth_median'],
            'min': res['depth_min'],
        }.get(mode, res['depth_median'])

        # 运动控制 (仅用于显示, 不发布)
        lx, az, action = decide_motion(
            res['cx'], depth_control, in_roi=res['in_roi'])

        # ── 4. 可视化 ──
        self.draw_overlay(res, lx, az, action, mode, depth_control,
                          filter_method)

        self.get_logger().info(
            f'n={res["n"]}/{res["n_raw"]} 滤波={filter_method} '
            f'模式={mode} 控制深度={depth_control:.2f}m '
            f'(mean={res["depth_mean"]:.2f} '
            f'median={res["depth_median"]:.2f} min={res["depth_min"]:.2f}) '
            f'cmd=(lx={lx:.2f},az={az:.2f}) {action}',
            throttle_duration_sec=0.5)

    # ================= 可视化 =================

    def depth_roi_mask(self):
        """深度图 → ROI 像素掩码 (反投影到 3D 判断是否在 ROI 内)

        体现「深度信息滤波」思想: 只保留 ROI 区域内的有效深度像素。
        """
        z = self.depth_image  # 米, 32FC1
        h, w = z.shape
        u = np.arange(w)
        v = np.arange(h)
        U, V = np.meshgrid(u, v)  # (h, w)

        # 反投影: 像素(u,v)+深度z → 相机3D (x,y,z)
        X = (U - self.cx) * z / self.fx
        Y = (V - self.cy) * z / self.fy

        valid = (z > 0.05) & (z < DEPTH_CLIP) & np.isfinite(z)
        mask = (valid &
                (X > ROI_X_MIN) & (X < ROI_X_MAX) &
                (Y > ROI_Y_MIN) & (Y < ROI_Y_MAX) &
                (z > ROI_Z_MIN) & (z < ROI_Z_MAX))
        return mask

    def draw_overlay(self, res, lx, az, action, mode='median',
                     depth_control=0.0, filter_method='none'):
        """双画面: 左 RGB + 右深度热力图, 底部控制栏"""
        rgb = self.rgb_image.copy()
        h, w = rgb.shape[:2]

        # ── ROI 掩码 (深度图) ──
        roi_mask = self.depth_roi_mask()

        # ═══ 左侧: RGB + ROI 3D 框 + 质心 ═══
        # 3D ROI 8 角点 → 像素 (方案A: 深度图已对齐彩色, 直接彩色内参投影)
        corners3d = [
            (ROI_X_MIN, ROI_Y_MIN, ROI_Z_MIN), (ROI_X_MAX, ROI_Y_MIN, ROI_Z_MIN),
            (ROI_X_MAX, ROI_Y_MAX, ROI_Z_MIN), (ROI_X_MIN, ROI_Y_MAX, ROI_Z_MIN),
            (ROI_X_MIN, ROI_Y_MIN, ROI_Z_MAX), (ROI_X_MAX, ROI_Y_MIN, ROI_Z_MAX),
            (ROI_X_MAX, ROI_Y_MAX, ROI_Z_MAX), (ROI_X_MIN, ROI_Y_MAX, ROI_Z_MAX),
        ]
        pts2d = []
        for x3, y3, z3 in corners3d:
            u = int(self.fx * x3 / z3 + self.cx)
            v = int(self.fy * y3 / z3 + self.cy)
            pts2d.append((u, v))

        if len(pts2d) == 8:
            near, far = pts2d[:4], pts2d[4:]
            cv2.polylines(rgb, [np.array(near)], True, (0, 200, 255), 2)
            cv2.polylines(rgb, [np.array(far)], True, (0, 255, 200), 2)
            for pn, pf in zip(near, far):
                cv2.line(rgb, pn, pf, (0, 200, 255), 1)

        # 质心红点 (方案A: 质心在彩色坐标系, 直接用彩色内参投影, 零偏移)
        if res['in_roi']:
            uc = int(self.fx * res['cx'] / max(res['cz'], 1e-3) + self.cx)
            vc = int(self.cy)
            cv2.circle(rgb, (uc, vc), 8, (0, 0, 255), -1)
            cv2.putText(rgb, f"({res['cx']:.2f},{res['cz']:.2f})m",
                        (uc + 12, vc), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (0, 0, 255), 2)

        # 运动控制箭头 (RGB 画面左下角)
        ax0, ay0 = 90, h - 70
        if abs(lx) > 1e-6:
            end = (ax0, ay0 - int(lx * 120))
            cv2.arrowedLine(rgb, (ax0, ay0), end, (0, 255, 0), 6,
                            tipLength=0.35)
        if abs(az) > 1e-6:
            end = (ax0 + int(az * 80), ay0)
            cv2.arrowedLine(rgb, (ax0, ay0), end, (255, 0, 0), 6,
                            tipLength=0.35)
        if abs(lx) < 1e-6 and abs(az) < 1e-6:
            cv2.circle(rgb, (ax0, ay0), 12, (0, 0, 255), 3)

        # ═══ 右侧: 深度热力图 + ROI 高亮 ═══
        depth_clip = np.clip(self.depth_image, 0, DEPTH_CLIP)
        depth_vis = (depth_clip / DEPTH_CLIP * 255).astype(np.uint8)
        depth_heat = cv2.applyColorMap(depth_vis, cv2.COLORMAP_JET)

        # ROI 像素高亮 (绿色半透明)
        overlay = depth_heat.copy()
        overlay[roi_mask] = (0, 255, 0)
        depth_heat = cv2.addWeighted(overlay, 0.45, depth_heat, 0.55, 0)

        # 同样画 ROI 角点框 (深度图与 RGB 对齐, 像素坐标相同)
        if len(pts2d) == 8:
            cv2.polylines(depth_heat, [np.array(near)], True, (0, 200, 255), 2)
            cv2.polylines(depth_heat, [np.array(far)], True, (0, 255, 200), 2)

        # 深度统计文字 (右侧顶部) — 三种滤波值对比, 高亮当前模式
        if res['in_roi']:
            cv2.putText(depth_heat,
                        f"control[{mode}]={depth_control:.2f}m",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (0, 255, 255), 2)
            cv2.putText(depth_heat,
                        f"mean={res['depth_mean']:.2f} "
                        f"median={res['depth_median']:.2f} "
                        f"min={res['depth_min']:.2f}",
                        (10, 55), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (255, 255, 255), 1)
            cv2.putText(depth_heat,
                        f"filter[{filter_method}] "
                        f"n={res['n']}/{res['n_raw']}",
                        (10, 80), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (0, 255, 255), 1)
        else:
            cv2.putText(depth_heat, "NO TARGET in ROI",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 0, 255), 2)

        # ═══ 并排显示 ═══
        combined = np.hstack([rgb, depth_heat]).copy()

        # ═══ 底部控制栏 (28px) ═══
        bar = np.zeros((28, combined.shape[1], 3), dtype=np.uint8)
        bar[:] = (20, 20, 20)
        cv2.putText(bar, f"ACTION: {action}",
                    (10, 20), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 255, 255), 2)
        cv2.putText(bar,
                    f"cmd_vel  linear={lx:+.2f} m/s   angular={az:+.2f} rad/s"
                    f"   | goal={GOAL_DEPTH}m  mode={mode}  n={res['n']}",
                    (w // 2 + 20, 20), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (255, 255, 255), 1)

        final = np.vstack([combined, bar]).copy()
        cv2.imshow('Depth ROI Demo (RGB | Depth)', final)
        if cv2.waitKey(1) & 0xFF == 27:
            raise KeyboardInterrupt


def main():
    rclpy.init()
    node = DepthRoiDemoNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
