#!/usr/bin/env python3
"""03-4 AprilTag 实践: ROS2 实时 AprilTag 检测 + PnP 位姿 + TF 广播

订阅彩色相机 → apriltag.Detector 检测 tag36h11 → PnP 6D 位姿
→ 发布 TF (tag_N → camera) → 画角点 + ID + 距离

与 ros2_tag_detect.py (ArUco 版) 的区别:
  - 用 apriltag.Detector() 替代 cv2.aruco.ArucoDetector()
  - 返回 Detection 对象, 不是 (corners, ids)
  - 手动用 cv2 画可视化 (无内置 drawDetectedMarkers)
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge
from geometry_msgs.msg import TransformStamped
import tf2_ros
import cv2
import numpy as np
import apriltag


class AprilTagDetectNode(Node):
    def __init__(self):
        super().__init__('apriltag_detect_node')
        self.bridge = CvBridge()
        self.rgb_image = None

        # D435 默认内参
        self.fx, self.fy = 613.4, 612.2
        self.cx, self.cy = 330.2, 240.6
        self.camera_matrix = np.array(
            [[self.fx, 0, self.cx], [0, self.fy, self.cy], [0, 0, 1]],
            dtype=np.float32)
        self.dist_coeffs = np.zeros((5, 1))

        # AprilTag 检测器 (tag36h11 族)
        self.detector = apriltag.Detector(
            apriltag.DetectorOptions(families='tag36h11'))

        # 标记实际尺寸 5cm, PnP 3D 点
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
        self.get_logger().info('AprilTag (apriltag) 检测节点启动')

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
        tf_msg.child_frame_id = f'apriltag_{tag_id}'
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

        # AprilTag 检测需要灰度图
        gray = cv2.cvtColor(self.rgb_image, cv2.COLOR_BGR2GRAY)
        result = self.detector.detect(gray)
        display = self.rgb_image.copy()

        if result:
            for r in result:
                corners = r.corners.astype(np.float32)

                # 画角点 + 连线
                for pt in corners:
                    cv2.circle(display, tuple(pt.astype(int)), 5,
                              (0, 255, 0), -1)
                for i in range(4):
                    p1 = tuple(corners[i].astype(int))
                    p2 = tuple(corners[(i+1) % 4].astype(int))
                    cv2.line(display, p1, p2, (0, 255, 0), 2)

                # ID + HUD
                cx, cy = int(r.center[0]), int(r.center[1])
                cv2.putText(display, f'ID:{r.tag_id}',
                            (cx-25, cy-15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                            (0, 255, 0), 2)

                # 决策裕度 (质量指标)
                cv2.putText(display,
                            f'margin={r.decision_margin:.1f}',
                            (cx-40, cy+20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                            (255, 255, 0), 1)

                # PnP 位姿估计
                ret, rvec, tvec = cv2.solvePnP(
                    self.obj_points, corners,
                    self.camera_matrix, self.dist_coeffs)
                if ret:
                    cv2.drawFrameAxes(display, self.camera_matrix,
                                      self.dist_coeffs, rvec, tvec, 0.03)
                    dist = np.linalg.norm(tvec)
                    cv2.putText(display, f'd={dist:.2f}m',
                                (cx-25, cy-35),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                (255, 0, 0), 2)
                    self.publish_tag_tf(r.tag_id, rvec, tvec)

        cv2.putText(display,
                    f'AprilTag: {len(result)} tags  (tag36h11)',
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.imshow('AprilTag Detection (ROS2)', display)
        if cv2.waitKey(1) & 0xFF == 27:
            raise KeyboardInterrupt


def main():
    rclpy.init()
    node = AprilTagDetectNode()
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
