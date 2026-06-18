#!/usr/bin/env python3
"""03-7 ORB-SLAM3: SLAM 位姿订阅与轨迹记录

订阅任意 SLAM 系统发布的 PoseStamped 话题,
记录轨迹到 numpy 数组, 实时绘制俯视轨迹图。

适用于 ORB-SLAM3 (/orb_slam3/camera_pose) 或
任何发布 geometry_msgs/PoseStamped 的 SLAM 系统。
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
import numpy as np
import cv2


class SlamTracker(Node):
    def __init__(self):
        super().__init__('slam_tracker')
        self.trajectory = []  # [(x, y, z), ...]

        self.sub = self.create_subscription(
            PoseStamped, '/orb_slam3/camera_pose',
            self.pose_cb, 10)
        self.get_logger().info('等待 SLAM 位姿... (/orb_slam3/camera_pose)')

    def pose_cb(self, msg):
        x = msg.pose.position.x
        y = msg.pose.position.y
        z = msg.pose.position.z
        self.trajectory.append((x, y, z))

        if len(self.trajectory) % 30 == 0:
            self.get_logger().info(
                f'轨迹点数: {len(self.trajectory)} | '
                f'当前位置: ({x:.3f}, {y:.3f}, {z:.3f})')

        # 绘制轨迹 (俯视图: x-z 平面)
        self.draw_trajectory()

    def draw_trajectory(self):
        if len(self.trajectory) < 2:
            return

        canvas = np.ones((400, 500, 3), dtype=np.uint8) * 30
        pts = np.array(self.trajectory)

        # 归一化到画布
        x_min, x_max = pts[:, 0].min(), pts[:, 0].max()
        z_min, z_max = pts[:, 2].min(), pts[:, 2].max()
        span_x = max(x_max - x_min, 0.5)
        span_z = max(z_max - z_min, 0.5)

        # 映射到画布坐标
        px = ((pts[:, 0] - x_min) / span_x * 400 + 50).astype(int)
        py = ((pts[:, 2] - z_min) / span_z * 300 + 50).astype(int)

        # 画线（颜色从绿到红表示时间流逝）
        for i in range(1, len(px)):
            ratio = i / len(px)
            color = (0, int(255*(1-ratio)), int(255*ratio))  # G→R
            cv2.line(canvas, (px[i-1], py[i-1]), (px[i], py[i]),
                     color, 2)

        # 起点绿点, 终点红点
        cv2.circle(canvas, (px[0], py[0]), 5, (0, 255, 0), -1)
        cv2.circle(canvas, (px[-1], py[-1]), 5, (0, 0, 255), -1)
        cv2.putText(canvas, 'START', (px[0]+5, py[0]-5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        cv2.putText(canvas, f' pts:{len(pts)}', (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        cv2.imshow('SLAM Trajectory (top-down x-z)', canvas)
        cv2.waitKey(1)


def main():
    rclpy.init()
    node = SlamTracker()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        if node.trajectory:
            np.save('/tmp/slam_trajectory.npy',
                    np.array(node.trajectory))
            node.get_logger().info(
                f'轨迹已保存: /tmp/slam_trajectory.npy '
                f'({len(node.trajectory)} 点)')
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
