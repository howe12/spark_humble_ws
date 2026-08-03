#!/usr/bin/env python3
"""实测: depth 坐标系点云投影到 RGB 的偏移量

方法: 取深度图中心区域一个深度值 z, 用【深度内参】反投影出 3D 点,
      再分别用【深度内参】和【彩色内参】投影回像素, 比较两个像素差。

结论参考:
  - 如果深度相机与彩色相机无外参偏移 → 两个投影像素应一致
  - 实际 D435 有基线 → 近处偏移大, 远处偏移小
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge
import numpy as np


class OffsetCheck(Node):
    def __init__(self):
        super().__init__('offset_check')
        self.b = CvBridge()
        self.depth = None
        self.ci = None
        self.di = None
        self.create_subscription(Image, '/camera/aligned_depth_to_color/image_raw',
                                 self.cb_d, 10)
        self.create_subscription(CameraInfo, '/camera/color/camera_info',
                                 self.cb_ci, 10)
        self.create_subscription(CameraInfo, '/camera/depth/camera_info',
                                 self.cb_di, 10)
        # 用于对比的原始深度 (未对齐, depth 坐标系)
        self.create_subscription(Image, '/camera/depth/image_rect_raw',
                                 self.cb_dr, 10)
        self.raw_depth = None

    def cb_d(self, m):
        self.depth = self.b.imgmsg_to_cv2(m, '32FC1') / 1000.0  # 对齐(米)

    def cb_dr(self, m):
        self.raw_depth = self.b.imgmsg_to_cv2(m, '32FC1') / 1000.0  # 原始(米)

    def cb_ci(self, m):
        self.ci = m.k

    def cb_di(self, m):
        self.di = m.k

    def check(self):
        if (self.depth is None or self.raw_depth is None
                or self.ci is None or self.di is None):
            return
        if getattr(self, '_done', False):
            return
        self._done = True
        print("=" * 64)
        print("深度坐标系点云 → RGB 投影偏移实测")
        print("=" * 64)
        cfx, cfy, ccx, ccy = self.ci[0], self.ci[4], self.ci[2], self.ci[5]
        dfx, dfy, dcx, dcy = self.di[0], self.di[4], self.di[2], self.di[5]
        print(f"彩色内参 fx={cfx:.0f} cx={ccx:.0f} fy={cfy:.0f} cy={ccy:.0f}")
        print(f"深度内参 fx={dfx:.0f} cx={dcx:.0f} fy={dfy:.0f} cy={dcy:.0f}")

        for (u, v) in [(320, 240), (160, 120), (480, 360), (320, 300)]:
            z = self.depth[v, u]
            if z <= 0:
                print(f"({u},{v}) 深度无效, 跳过")
                continue
            # 3D 点 (深度坐标系)
            x3 = (u - dcx) * z / dfx
            y3 = (v - dcy) * z / dfy
            # 用彩色内参投影 (当前代码的做法)
            uc = int(cfx * x3 / z + ccx)
            vc = int(cfy * y3 / z + ccy)
            dx, dy = uc - u, vc - v
            print(f"像素({u},{v}) z={z:.2f}m → "
                  f"点云3D=({x3:.3f},{y3:.3f},{z:.3f}) → "
                  f"RGB投影({uc},{vc}) 偏移=({dx:+d},{dy:+d})px")
        print("=" * 64)
        print("结论: 偏移 (dx,dy) 即当前代码画 ROI 框/质心的误差")
        print("      近处(小z)偏移大, 远处(大z)偏移小")
        rclpy.shutdown()


def main():
    rclpy.init()
    node = OffsetCheck()
    # 数据齐了自动 check 一次
    from rclpy.timer import Timer
    def tick():
        node.check()
    node.create_timer(1.0, tick)
    import threading
    threading.Timer(12.0, rclpy.shutdown).start()
    try:
        rclpy.spin(node)
    except rclpy.executors.ExternalShutdownException:
        pass


if __name__ == '__main__':
    main()
