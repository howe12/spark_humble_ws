#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
意图分类节点 - ROS2 移植版（TF-IDF + 规则匹配）
功能：融合规则匹配 + TF-IDF 进行意图分类
订阅 /text_command，发布 /intent_result + /intent_confidence
"""

import rclpy
import numpy as np
from rclpy.node import Node
from std_msgs.msg import String, Float32
import os
import pickle

from ml_basics.nlp_preprocessor import TextPreprocessor


class IntentClassifierNode(Node):
    """TF-IDF + 规则融合意图分类器（ROS2）"""

    def __init__(self):
        super().__init__('intent_classifier_node')

        # ROS2 params
        self.declare_parameter('model_path', '')
        self.declare_parameter('fusion_rule_weight', 0.4)
        self.declare_parameter('fusion_tfidf_weight', 0.6)

        # 初始化文本预处理器
        self.preprocessor = TextPreprocessor()

        # 意图标签定义
        self.intents = ['forward', 'backward', 'left', 'right', 'stop',
                        'speed_up', 'slow_down', 'turn_around']

        # ============ 规则匹配层 ============
        self.rule_intents = {
            '往前走': 'forward', '往前': 'forward', '前进': 'forward', '向前': 'forward',
            '往后退': 'backward', '后退': 'backward', '倒车': 'backward',
            '左转': 'left', '往左': 'left', '向左': 'left', '左拐': 'left',
            '右转': 'right', '往右': 'right', '向右': 'right', '右拐': 'right',
            '停止': 'stop', '停下': 'stop', '别动': 'stop', '暂停': 'stop',
            '加速': 'speed_up', '提速': 'speed_up',
            '减速': 'slow_down', '慢一点': 'slow_down',
            '掉头': 'turn_around', '原180': 'turn_around'
        }

        # ============ TF-IDF 分类器层 ============
        self.tfidf_vectorizer = None
        self.tfidf_classifier = None
        self._init_tfidf_classifier()

        # ============ 融合权重 ============
        self.fusion_rule_weight = self.get_parameter('fusion_rule_weight').value
        self.fusion_tfidf_weight = self.get_parameter('fusion_tfidf_weight').value

        # 创建订阅者和发布者
        self.subscription = self.create_subscription(
            String, '/text_command', self.command_callback, 10)
        self.intent_pub = self.create_publisher(String, '/intent_result', 10)
        self.confidence_pub = self.create_publisher(Float32, '/intent_confidence', 10)

        self.get_logger().info("意图分类器已启动（ROS2 / TF-IDF + 规则匹配）")

    def _init_tfidf_classifier(self):
        """初始化TF-IDF分类器"""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.svm import SVC

            # 尝试从参数路径加载预训练模型
            model_path = self.get_parameter('model_path').value
            if not model_path:
                model_path = os.path.join(os.path.dirname(__file__), '../models/tfidf_model.pkl')

            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.tfidf_vectorizer = data['vectorizer']
                    self.tfidf_classifier = data['classifier']
                self.get_logger().info(f"已加载TF-IDF预训练模型: {model_path}")
            else:
                # 使用基础训练数据初始化
                self._train_tfidf_classifier()

        except ImportError as e:
            self.get_logger().warn(f"sklearn未安装，TF-IDF分类器不可用: {e}")
            self.tfidf_vectorizer = None
            self.tfidf_classifier = None

    def _train_tfidf_classifier(self):
        """训练TF-IDF分类器"""
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.svm import SVC

        # 训练数据（54个文本 = 54个标签）
        train_texts = [
            "往前走", "往前", "前进", "向前", "往前走一点",
            "往前挪", "向前走", "向前进", "往前开",
            "往后退", "后退", "倒车", "往后", "往后退一点",
            "后退走", "倒车一点",
            "左转", "往左", "向左", "左拐", "左转一下",
            "往左转", "左转弯",
            "右转", "往右", "向右", "右拐", "右转一下",
            "往右转", "右转弯",
            "停止", "停下", "别动", "暂停", "停止运动", "站住",
            "加速", "提速", "快一点", "快点", "加快", "加速前进",
            "减速", "慢一点", "慢速", "减速运动", "慢下来",
            "掉头", "原180", "掉个头", "转180", "回头", "转过来", "掉头转向",
        ]

        train_labels = (
            ['forward'] * 9 + ['backward'] * 7 + ['left'] * 7 +
            ['right'] * 7 + ['stop'] * 6 + ['speed_up'] * 6 +
            ['slow_down'] * 5 + ['turn_around'] * 7
        )

        self.tfidf_vectorizer = TfidfVectorizer(ngram_range=(1, 3), max_features=500)
        X_train = self.tfidf_vectorizer.fit_transform(train_texts)
        self.tfidf_classifier = SVC(probability=True)
        self.tfidf_classifier.fit(X_train, train_labels)

        self.get_logger().info("TF-IDF分类器训练完成（内置训练数据）")

    def _rule_classify(self, text):
        """规则匹配分类"""
        normalized = self.preprocessor.normalize_numbers(text)
        phrases = self.preprocessor.detect_phrases(normalized)

        for phrase in phrases:
            if phrase['type'] == 'phrase' and phrase['text'] in self.rule_intents:
                return self.rule_intents[phrase['text']], 0.9

        return None, 0.0

    def _tfidf_classify(self, text):
        """TF-IDF分类"""
        if self.tfidf_vectorizer is None or self.tfidf_classifier is None:
            return None, 0.0

        try:
            normalized = self.preprocessor.normalize_numbers(text)
            words = self.preprocessor.segment(normalized)
            seg_text = ' '.join(words)

            X = self.tfidf_vectorizer.transform([seg_text])
            intent = self.tfidf_classifier.predict(X)[0]
            prob = self.tfidf_classifier.predict_proba(X)[0]
            confidence = max(prob)

            return intent, confidence

        except Exception as e:
            self.get_logger().warn(f"TF-IDF分类失败: {e}")
            return None, 0.0

    def classify(self, text):
        """
        两层融合分类（规则 + TF-IDF）

        返回:
            (intent, confidence, details)
        """
        rule_intent, rule_conf = self._rule_classify(text)
        tfidf_intent, tfidf_conf = self._tfidf_classify(text)

        # 融合决策
        intent_scores = {}
        for intent in self.intents:
            score = 0.0
            count = 0

            if rule_intent == intent:
                score += self.fusion_rule_weight * rule_conf
                count += 1
            if tfidf_intent == intent:
                score += self.fusion_tfidf_weight * tfidf_conf
                count += 1

            if count > 0:
                intent_scores[intent] = score / count

        if intent_scores:
            final_intent = max(intent_scores, key=intent_scores.get)
            final_confidence = intent_scores[final_intent]
        else:
            final_intent = 'stop'
            final_confidence = 0.5

        details = {
            'rule': {'intent': rule_intent, 'confidence': rule_conf},
            'tfidf': {'intent': tfidf_intent, 'confidence': tfidf_conf},
            'final': {'intent': final_intent, 'confidence': final_confidence}
        }

        return final_intent, final_confidence, details

    def command_callback(self, msg):
        """ROS2回调函数"""
        text = msg.data
        self.get_logger().info(f"接收到指令: {text}")

        intent, confidence, details = self.classify(text)

        # 发布结果
        intent_msg = String()
        intent_msg.data = intent
        self.intent_pub.publish(intent_msg)

        conf_msg = Float32()
        conf_msg.data = float(confidence)
        self.confidence_pub.publish(conf_msg)

        self.get_logger().info(
            f"分类结果: {intent} (置信度: {confidence:.2f})")
        self.get_logger().info(
            f"  - 规则: {details['rule']['intent']} ({details['rule']['confidence']:.2f})")
        self.get_logger().info(
            f"  - TF-IDF: {details['tfidf']['intent']} ({details['tfidf']['confidence']:.2f})")


def main(args=None):
    rclpy.init(args=args)
    node = IntentClassifierNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
