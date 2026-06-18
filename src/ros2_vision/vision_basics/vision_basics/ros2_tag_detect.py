#!/usr/bin/env python3
"""03-4 视觉标签: ROS2 实时 ArUco 检测 + PnP 位姿 + TF 广播

订阅彩色相机 → cv2.aruco 检测标记 → PnP 估计 6D 位姿
→ 发布 TF (tag_N → camera) → 画坐标轴 + ID + 距离

与 AprilTag 流程完全一致: 检测角点 → PnP → TF
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge
from geometry_msgs.msg import TransformStamped
import tf2_ros
import cv2
import numpy as np


class TagDetectNode(Node):
    def __init__(self):
        super().__init__('tag_detect_node')
        self.bridge = CvBridge()
        self.rgb_image = None

        # D435 默认内参
        self.fx, self.fy = 613.4, 612.2
        self.cx, self.cy = 330.2, 240.6
        self.camera_matrix = np.array(
            [[self.fx, 0, self.cx], [0, self.fy, self.cy], [0, 0, 1]],
            dtype=np.float32)
        self.dist_coeffs = np.zeros((5, 1))

        # ArUco 检测器
        self.dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.detector = cv2.aruco.ArucoDetector(self.dict)

        # 标记实际尺寸 5cm
        self.tag_size = 0.05
        self.obj_points = np.array([
            [-self.tag_size/2,  self.tag_size/2, 0],
            [ self.tag_size/2,  self.tag_size/2, 0],
            [ self.tag_size/2, -self.tag_size/2, 0],
            [-self.tag_size/2, -self.tag_size/2, 0],
        ], dtype=np.float32)

        # 订阅
        self.rgb_sub = self.create_subscription(
            Image, '/camera/camera/color/image_raw', self.rgb_cb, 10)
        self.camera_info_sub = self.create_subscription(
            CameraInfo, '/camera/camera/color/camera_info',
            self.camera_info_cb, 10)

        # TF 广播
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)
        self.get_logger().info('ArUco 检测节点启动')

    def camera_info_cb(self, msg):
        self.fx, self.fy = msg.k[0], msg.k[4]
        self.cx, self.cy = msg.k[2], msg.k[5]
        self.camera_matrix = np.array(
            [[self.fx, 0, self.cx], [0, self.fy, self.cy], [0, 0, 1]],
            dtype=np.float32)
        self.destroy_subscription(self.camera_info_sub)

    def rgb_cb(self, msg):
        self.rgb_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

    def publish_tag_tf(self, tag_id, rvec, tvec):
        R, _ = cv2.Rodrigues(rvec)
        # 旋转矩阵 → 四元数
        trace = np.trace(R)
        if trace > 0:
            s = np.sqrt(trace + 1.0) * 2
            qw = 0.25 * s
            qx = (R[2, 1] - R[1, 2]) / s
            qy = (R[0, 2] - R[2, 0]) / s
            qz = (R[1, 0] - R[0, 1]) / s
        else:
            qw = qx = qy = qz = 0.0

        tf_msg = TransformStamped()
        tf_msg.header.stamp = self.get_clock().now().to_msg()
        tf_msg.header.frame_id = 'camera_color_optical_frame'
        tf_msg.child_frame_id = f'tag_{tag_id}'
        tf_msg.transform.translation.x = float(tvec[0])
        tf_msg.transform.translation.y = float(tvec[1])
        tf_msg.transform.translation.z = float(tvec[2])
        tf_msg.transform.rotation.x = qx
        tf_msg.transform.rotation.y = qy
        tf_msg.transform.rotation.z = qz
        tf_msg.transform.rotation.w = qw
        self.tf_broadcaster.sendTransform(tf_msg)

    def spin_once(self):
        rclpy.spin_once(self, timeout_sec=0.05)
        if self.rgb_image is None:
            return

        gray = cv2.cvtColor(self.rgb_image, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self.detector.detectMarkers(gray)
        display = self.rgb_image.copy()

        if ids is not None:
            cv2.aruco.drawDetectedMarkers(display, corners, ids)
            for i, c in enumerate(corners):
                ret, rvec, tvec = cv2.solvePnP(
                    self.obj_points, c,
                    self.camera_matrix, self.dist_coeffs)
                if ret:
                    cv2.drawFrameAxes(display, self.camera_matrix,
                                      self.dist_coeffs, rvec, tvec, 0.03)
                    # HUD
                    cx, cy = int(c[0][:, 0].mean()), int(c[0][:, 1].mean())
                    dist = np.linalg.norm(tvec)
                    cv2.putText(display, f'ID:{ids[i][0]} d:{dist:.2f}m',
                                (cx-30, cy-15),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                (0, 255, 0), 2)
                    self.publish_tag_tf(ids[i][0], rvec, tvec)

        cv2.imshow('ArUco Tag Detection', display)
        if cv2.waitKey(1) & 0xFF == 27:
            raise KeyboardInterrupt


def main():
    rclpy.init()
    node = TagDetectNode()
    try:
        while rclpy.ok():
            node.spin_once()
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
