#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
参数解析节点 - ROS2 移植版
功能：从文本命令中提取参数（距离、角度、速度、时间）
订阅 /intent_result + /text_command，发布 /cmd_params
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import re

from ml_basics.nlp_preprocessor import TextPreprocessor


class ParamParserNode(Node):
    """参数解析器（ROS2）"""

    def __init__(self):
        super().__init__('param_parser_node')

        # 初始化文本预处理器
        self.preprocessor = TextPreprocessor()

        # 正则模式：提取带单位的参数值
        self.patterns = {
            'distance': r'(\d+\.?\d*)\s*(?:米|m\b)',
            'angle':    r'(\d+\.?\d*)\s*(?:度|°)',
            'speed':    r'(\d+\.?\d*)\s*(?:m/s|km/h)',
            'time':     r'(\d+\.?\d*)\s*(?:秒|s\b)'
        }

        # 相对量词映射
        self.relative_markers = {
            '一点': 0.5, '一点点': 0.3, '稍微': 0.3,
            '稍微一点': 0.3, '很多': 1.5, '非常': 1.5
        }

        # 意图-参数映射表
        self.intent_param_map = {
            'forward':     ['distance'],
            'backward':    ['distance'],
            'left':        ['distance'],
            'right':       ['distance'],
            'rotate':      ['angle'],
            'turn':        ['angle'],
            'spin':        ['angle'],
            'turn_around': ['angle'],
            'speed':       ['speed'],
            'set_speed':   ['speed'],
            'speed_up':    [],
            'slow_down':   [],
            'wait':        ['time'],
            'delay':       ['time'],
            'stop':        []
        }

        # 存储当前状态
        self.current_intent = 'stop'
        self.current_text = ''
        self.current_params = {}

        # 创建订阅者和发布者
        self.intent_sub = self.create_subscription(
            String, '/intent_result', self.intent_callback, 10)
        self.text_sub = self.create_subscription(
            String, '/text_command', self.text_callback, 10)
        self.cmd_pub = self.create_publisher(String, '/cmd_params', 10)

        self.get_logger().info("参数解析器已启动（ROS2）")

    def intent_callback(self, msg):
        """
        处理意图结果（从意图分类器订阅）
        """
        self.current_intent = str(msg.data)
        self.get_logger().info(f"接收到意图: {self.current_intent}")

        if self.current_text:
            self._parse_and_publish()

    def text_callback(self, msg):
        """
        处理原始文本（从用户输入订阅）
        """
        self.current_text = str(msg.data)
        self.get_logger().info(f"接收到文本: {self.current_text}")

        # 提取参数
        self._extract_params()

        # 如果意图已就绪，则发布命令
        if self.current_intent:
            self._parse_and_publish()

    def _extract_params(self):
        """
        从文本中提取参数
        """
        self.current_params = {}
        text = self.preprocessor.normalize_numbers(self.current_text)

        # 相对量词检测
        relative_scale = 1.0
        for marker, scale in self.relative_markers.items():
            if marker in self.current_text:
                relative_scale = scale
                self.get_logger().info(f"检测到相对量词: {marker} → 比例 {scale}")
                break

        # 逐个参数用正则提取
        for param_name, pattern in self.patterns.items():
            match = re.search(pattern, text)
            if match:
                value = float(match.group(1)) * relative_scale
                self.current_params[param_name] = value
                self.get_logger().info(f"提取到{param_name}: {value}")

    def _parse_and_publish(self):
        """
        根据意图类型过滤参数，然后发布命令
        """
        cmd = self.current_intent
        params_str = ""

        # 从映射表获取该意图允许的参数类型
        allowed_params = self.intent_param_map.get(cmd, [])

        for key in allowed_params:
            if key in self.current_params:
                params_str += f",{key}={self.current_params[key]}"

        full_cmd = cmd + params_str if params_str else cmd
        self.get_logger().info(f"发布命令: {full_cmd}")

        msg = String()
        msg.data = full_cmd
        self.cmd_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = ParamParserNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
