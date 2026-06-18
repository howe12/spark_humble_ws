#!/usr/bin/env python3
"""03-1 点云与深度相机: PointCloud2 订阅解析

订阅 D435 点云话题，解析消息结构并打印:
  - 消息头 (时间戳、坐标系)
  - 点云维度 (width × height, 有组织/无组织)
  - 字段信息 (field name / offset / datatype)
  - 前 5 个点的 (x, y, z) 坐标
  - 总点数 + 计算耗时
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
import numpy as np
import time


DATATYPE_NAMES = {1: 'INT8', 2: 'UINT8', 3: 'INT16', 4: 'UINT16',
                  5: 'INT32', 6: 'UINT32', 7: 'FLOAT32', 8: 'FLOAT64'}


class PCDSubscriber(Node):
    def __init__(self):
        super().__init__('pcd_subscriber')
        self.count = 0
        self.sub = self.create_subscription(
            PointCloud2, '/camera/camera/depth/color/points',
            self.callback, 10)

    def callback(self, msg):
        self.count += 1
        t0 = time.time()

        # --- 消息头 ---
        self.get_logger().info(
            f'=== 第 {self.count} 帧 | '
            f'timestamp: {msg.header.stamp.sec}.{msg.header.stamp.nanosec:09d} | '
            f'frame: {msg.header.frame_id}')

        # --- 点云维度 ---
        organized = msg.height > 1
        self.get_logger().info(
            f'Shape: {msg.width} × {msg.height} '
            f'({"有组织" if organized else "无组织"}) | '
            f'point_step={msg.point_step}B | is_dense={msg.is_dense}')

        # --- 字段信息 ---
        field_str = ' | '.join(
            f'{f.name}({DATATYPE_NAMES.get(f.datatype, f"UNK")}, offset={f.offset})'
            for f in msg.fields)
        self.get_logger().info(f'Fields: {field_str}')

        # --- 解析为 numpy ---
        points = np.array(list(point_cloud2.read_points(
            msg, field_names=('x', 'y', 'z'), skip_nans=True)))
        elapsed = (time.time() - t0) * 1000

        if len(points) == 0:
            self.get_logger().warn('点云为空！相机是否正对着物体？')
            return

        # --- 前 5 个点 ---
        self.get_logger().info(
            f'前 5 个点 (x, y, z):\n{points[:5]}')
        self.get_logger().info(
            f'总点数: {len(points)} | 解析耗时: {elapsed:.1f}ms')


def main():
    rclpy.init()
    node = PCDSubscriber()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
