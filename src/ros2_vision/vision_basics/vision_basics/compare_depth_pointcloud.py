#!/usr/bin/env python3
"""实测对比: 深度图值 vs 点云值 (同一帧数据)"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo, PointCloud2
import sensor_msgs_py.point_cloud2 as pc2
from cv_bridge import CvBridge
import numpy as np


class CompareNode(Node):
    def __init__(self):
        super().__init__('compare_depth_pc')
        self.bridge = CvBridge()
        self.depth = None
        self.cloud = None
        self.fx = self.fy = 0.0
        self.cx = self.cy = 0.0

        self.sub_d = self.create_subscription(
            Image, '/camera/aligned_depth_to_color/image_raw', self.cb_d, 10)
        self.sub_c = self.create_subscription(
            PointCloud2, '/camera/depth/color/points', self.cb_c, 10)
        self.sub_i = self.create_subscription(
            CameraInfo, '/camera/color/camera_info', self.cb_i, 10)
        # 用深度 camera_info (点云坐标系)
        self.sub_di = self.create_subscription(
            CameraInfo, '/camera/depth/camera_info', self.cb_di, 10)
        self.depth_info = None

    def cb_i(self, msg):
        self.fx, self.fy = msg.k[0], msg.k[4]
        self.cx, self.cy = msg.k[2], msg.k[5]

    def cb_di(self, msg):
        self.depth_info = msg.k

    def cb_d(self, msg):
        self.depth = self.bridge.imgmsg_to_cv2(msg, '32FC1')

    def cb_c(self, msg):
        self.cloud = pc2.read_points_numpy(
            msg, field_names=('x', 'y', 'z'), skip_nans=True)
        self.get_logger().info(
            f'收到点云 {len(self.cloud)} 点, depth={self.depth is not None}, '
            f'fx={self.fx:.0f}, depth_info={self.depth_info is not None}')
        if self.depth is None or self.cloud is None or self.fx == 0:
            return

        print("=" * 62)
        print("深度图 vs 点云 — 同一帧数据对比")
        print("=" * 62)
        h, w = self.depth.shape
        print(f"深度图尺寸: {w}x{h}  类型: {self.depth.dtype}")
        print(f"点云点数: {len(self.cloud)}")

        # 1. 深度图数值范围
        z_valid = self.depth[self.depth > 0]
        print(f"\n[深度图] 有效像素 {len(z_valid)}/{h*w}")
        print(f"  深度值范围: {z_valid.min():.3f} ~ {z_valid.max():.3f} m")
        print(f"  中央像素(320,240) 深度 = {self.depth[240, 320]:.3f} m")

        # 2. 点云数值范围
        print(f"\n[点云]   {len(self.cloud)} 点")
        print(f"  x 范围: {self.cloud[:,0].min():.3f} ~ {self.cloud[:,0].max():.3f} m")
        print(f"  y 范围: {self.cloud[:,1].min():.3f} ~ {self.cloud[:,1].max():.3f} m")
        print(f"  z 范围: {self.cloud[:,2].min():.3f} ~ {self.cloud[:,2].max():.3f} m")

        # 3. 深度图 z 值分布 vs 点云 z 值分布
        print(f"\n[数值对比]")
        print(f"  深度图 z: mean={z_valid.mean():.3f}  median={np.median(z_valid):.3f} m")
        print(f"  点云   z: mean={self.cloud[:,2].mean():.3f}  median={np.median(self.cloud[:,2]):.3f} m")
        print(f"  → 同一传感器, z 值应该接近 (深度图稠密, 点云稠密但跳过了无效点)")

        # 4. 反投影验证: 深度图中心像素 → 3D 坐标, 与点云对比
        u, v = 320, 240
        z = self.depth[v, u]
        if z > 0 and self.depth_info:
            dfx, dfy = self.depth_info[0], self.depth_info[4]
            dcx, dcy = self.depth_info[2], self.depth_info[5]
            x = (u - dcx) * z / dfx
            y = (v - dcy) * z / dfy
            print(f"\n[反投影验证] 深度图像素({u},{v}) z={z:.3f}m")
            print(f"  用深度内参反投影 → ({x:.3f}, {y:.3f}, {z:.3f})")
            # 找点云里最近的 3D 点
            d2 = np.sum((self.cloud - np.array([x, y, z]))**2, axis=1)
            near = np.argmin(d2)
            print(f"  点云最近点 → ({self.cloud[near,0]:.3f}, "
                  f"{self.cloud[near,1]:.3f}, {self.cloud[near,2]:.3f})")
            print(f"  距离差: {np.sqrt(d2[near]):.4f} m")

        print("=" * 62)
        print("结论: 深度图存【z 距离】, 点云存【完整 3D 坐标(x,y,z)】")
        print("      深度图 + 内参 反投影 = 点云 (同一个数据)")
        rclpy.shutdown()  # 完成对比, 干净退出


def main():
    rclpy.init()
    node = CompareNode()
    # 拿到一次完整数据就退出
    import threading
    def stop():
        node.get_logger().info('数据对比完成, 退出')
        rclpy.shutdown()
    threading.Timer(12.0, stop).start()
    try:
        rclpy.spin(node)
    except rclpy.executors.ExternalShutdownException:
        pass
    finally:
        node.destroy_node()


if __name__ == '__main__':
    main()
