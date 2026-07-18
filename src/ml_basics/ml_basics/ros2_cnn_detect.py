#!/usr/bin/env python3
"""4.4.2 CNN 实时手写数字识别 — ROS2 适配版

加载训练好的 SimpleCNN 模型，订阅相机话题，实时识别画面中的手写数字。

窗口:
  左侧 = 原始彩色画面
  右侧 = 预处理后的 28×28 灰度图 (放大显示)
  标题 = 识别结果 + 置信度

用法:
  ros2 run ml_basics ros2_cnn_detect

"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String, Float32
from cv_bridge import CvBridge
from ament_index_python.packages import get_package_share_directory
import cv2
import numpy as np
import math
import os

# ── matplotlib ──
import os as _os
_os.environ.setdefault('DISPLAY', ':0')
import matplotlib
matplotlib.use('TkAgg')
_os = None
import matplotlib.pyplot as plt

import torch
import torch.nn as nn

# ═══════════════════════ SimpleCNN (与训练时完全一致) ═══════════════════════

class SimpleCNN(nn.Module):
    """与 mnist_nn.py 中的定义完全一致"""

    def __init__(self):
        super(SimpleCNN, self).__init__()
        self.conv1 = nn.Conv2d(1, 16, 3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.conv2 = nn.Conv2d(16, 32, 3, padding=1)
        self.pool2 = nn.MaxPool2d(2, 2)
        self.fc1 = nn.Linear(32 * 7 * 7, 128)
        self.fc2 = nn.Linear(128, 10)

    def forward(self, x):
        x = self.pool(torch.relu(self.conv1(x)))
        x = self.pool2(torch.relu(self.conv2(x)))
        x = x.view(x.size(0), -1)
        x = torch.relu(self.fc1(x))
        x = self.fc2(x)
        return x


# ═══════════════════════ ROS2 节点 ═══════════════════════

class CNNDetectNode(Node):

    def __init__(self):
        super().__init__('cnn_detect')

        self.declare_parameter('image_topic', '/camera/color/image_raw')
        self.declare_parameter('model_file', '')
        self.declare_parameter('confidence_threshold', 0.7)

        # ── 加载模型 ──
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = SimpleCNN().to(self.device)

        model_file = self.get_parameter('model_file').get_parameter_value().string_value
        if not model_file:
            model_file = os.path.join(
                get_package_share_directory('ml_basics'), 'models', 'mnist_cnn.pth')

        if os.path.exists(model_file):
            self.model.load_state_dict(
                torch.load(model_file, map_location=self.device, weights_only=True))
            self.get_logger().info(f'模型已加载: {model_file}')
        else:
            self.get_logger().error(f'模型文件不存在: {model_file}')
            self.get_logger().error('请先运行 python3 mnist_nn.py 训练模型')
            raise FileNotFoundError(model_file)

        self.model.eval()
        self.confidence_threshold = self.get_parameter(
            'confidence_threshold').get_parameter_value().double_value

        # ── 订阅/发布 ──
        self.bridge = CvBridge()
        image_topic = self.get_parameter('image_topic').get_parameter_value().string_value
        self.sub = self.create_subscription(Image, image_topic, self.image_cb, 10)
        self.result_pub = self.create_publisher(String, '/cnn_detect/digit', 10)
        self.conf_pub = self.create_publisher(Float32, '/cnn_detect/confidence', 10)

        # ── matplotlib 窗口 ──
        self.fig, (self.ax_raw, self.ax_digit) = plt.subplots(1, 2, figsize=(10, 5))
        self.fig.canvas.manager.set_window_title('CNN Handwritten Digit Recognition')
        self.ax_raw.set_title('Camera (point a digit at the camera)')
        self.ax_raw.axis('off')
        self.ax_digit.set_title('Preprocessed (28x28)')
        self.ax_digit.axis('off')

        self.im_raw = self.ax_raw.imshow(
            np.zeros((480, 640, 3), dtype=np.uint8))
        self.im_digit = self.ax_digit.imshow(
            np.zeros((28, 28)), cmap='gray', vmin=0, vmax=1)

        self.fig.suptitle('Prediction: ---', fontsize=16, color='gray')
        plt.ion()
        self.fig.show()

        self._frame_count = 0
        self.get_logger().info('CNN 实时检测已启动')

    def image_cb(self, msg: Image):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f'CvBridge error: {e}')
            return

        # ── 预处理: 灰度 → resize 28×28 → 反转(适配MNIST黑底白字) → 归一化 ──
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (28, 28), interpolation=cv2.INTER_AREA)

        # MNIST 是黑底白字(背景0,数字255)，相机拍到的通常是白纸黑字(背景255,数字0)
        # 如果画面以亮色为主(均值>128)，做反转使背景变暗、数字变亮
        if np.mean(resized) > 128:
            resized = 255 - resized

        normalized = resized.astype(np.float32) / 255.0

        # ── 推理 ──
        tensor = torch.from_numpy(normalized).unsqueeze(0).unsqueeze(0).to(self.device)
        with torch.no_grad():
            outputs = self.model(tensor)
            probs = torch.softmax(outputs, dim=1)
            conf, pred = torch.max(probs, 1)
            confidence = conf.item()
            digit = pred.item()

        # ── 发布结果 ──
        if confidence >= self.confidence_threshold:
            msg_out = String()
            msg_out.data = str(digit)
            self.result_pub.publish(msg_out)

            conf_out = Float32()
            conf_out.data = float(confidence)
            self.conf_pub.publish(conf_out)

        # ── 更新 matplotlib (每 3 帧刷新一次) ──
        self._frame_count += 1
        if self._frame_count % 3 == 0:
            self._update_plot(cv_image, normalized, digit, confidence)

    def _update_plot(self, raw_bgr, digit_img, digit, confidence):
        try:
            rgb = cv2.cvtColor(raw_bgr, cv2.COLOR_BGR2RGB)
            self.im_raw.set_data(rgb)
            self.im_digit.set_data(digit_img)

            if confidence >= self.confidence_threshold:
                color = 'green'
                title = f'Prediction: {digit}  (confidence: {confidence:.1%})'
            else:
                color = 'gray'
                title = f'Prediction: ---  (confidence too low: {confidence:.1%})'

            self.fig.suptitle(title, fontsize=16, color=color)
            self.fig.canvas.draw_idle()
            self.fig.canvas.flush_events()
        except Exception:
            pass


def main():
    rclpy.init()
    try:
        node = CNNDetectNode()
    except FileNotFoundError:
        rclpy.shutdown()
        return

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
