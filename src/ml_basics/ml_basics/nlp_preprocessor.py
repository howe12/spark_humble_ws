#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
NLP文本预处理模块（ROS2 移植版）
功能：中文分词、短语检测、停用词过滤、数字归一化
核心依赖：jieba分词库

独立运行模块，不依赖ROS，可直接用 /usr/bin/python3 测试。
"""

import jieba
import re
import logging

logger = logging.getLogger(__name__)

# 加载机器人控制领域的专有词典
# 这样Jieba能正确识别"往前走"、"左转"等短语
CUSTOM_DICT = """
往前走 20 n
往后退 20 n
往左转 20 n
往右转 20 n
左转 20 n
右转 20 n
前进 20 n
后退 20 n
掉头 20 n
三米 15 n
五米 15 n
十米 15 n
九十度 15 n
一百八十度 15 n
"""

# 停用词列表（助词、量词等对语义贡献小）
STOPWORDS = set([
    '的', '了', '着', '啊', '吧', '呢', '吗', '呀', '哦', '哈',
    '一下', '一点', '一点', '一会儿', '一些',
    '然后', '接着', '再', '又', '还', '也',
    '请', '帮我', '帮我', '麻烦', '麻烦你',
    '个', '下', '点', '次', '遍'
])


class TextPreprocessor:
    """文本预处理器：整合分词、短语检测、数字归一化"""

    def __init__(self, use_custom_dict=True):
        """
        初始化预处理器

        参数:
            use_custom_dict: 是否加载自定义词典
        """
        if use_custom_dict:
            # 加载自定义词典，增强分词效果
            self._load_custom_dict()

        # N-gram短语词典
        # 机器人控制场景的常见短语
        self.ngram_phrases = {
            # 移动短语
            '往前走': 'forward',
            '往前': 'forward',
            '向前': 'forward',
            '前进': 'forward',
            '向前走': 'forward',

            '往后退': 'backward',
            '后退': 'backward',
            '倒车': 'backward',

            # 转向短语
            '左转': 'left',
            '往左': 'left',
            '向左': 'left',
            '左拐': 'left',

            '右转': 'right',
            '往右': 'right',
            '向右': 'right',
            '右拐': 'right',

            # 控制短语
            '停下': 'stop',
            '停止': 'stop',
            '别动': 'stop',
            '暂停': 'stop',

            '加速': 'speed_up',
            '提速': 'speed_up',

            '减速': 'slow_down',
            '慢一点': 'slow_down',

            '掉头': 'turn_around',
            '原180': 'turn_around',
        }

        # 中文数字到阿拉伯数字的映射
        self.chinese_num_map = {
            '零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
            '百': 100, '千': 1000,
            '点': '.', '度': '', '米': '', '秒': '', '秒': ''
        }

        logger.info("文本预处理器初始化完成")

    def _load_custom_dict(self):
        """加载自定义词典"""
        for line in CUSTOM_DICT.strip().split('\n'):
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    word, freq = parts[0], parts[1]
                    jieba.add_word(word, freq=freq)
        logger.info("已加载自定义词典")

    def segment(self, text):
        """
        分词处理

        参数:
            text: 输入文本

        返回:
            list: 分词结果列表
        """
        # 1. 清洗文本：去除多余空白
        text = text.strip()

        # 2. jieba分词（精确模式）
        words = list(jieba.cut(text, cut_all=False))

        # 3. 停用词过滤
        words = [w for w in words if w not in STOPWORDS and len(w.strip()) > 0]

        return words

    def detect_phrases(self, text):
        """
        N-gram短语检测
        将连续词语组合成有意义的短语

        参数:
            text: 输入文本

        返回:
            list: 短语/词语列表
        """
        # 按长度从长到短匹配（避免短词覆盖长词）
        phrases = []
        remaining = text

        while remaining:
            matched = False

            # 尝试最长匹配
            for phrase_len in range(min(len(remaining), 8), 0, -1):
                candidate = remaining[:phrase_len]
                if candidate in self.ngram_phrases:
                    phrases.append({
                        'text': candidate,
                        'intent': self.ngram_phrases[candidate],
                        'type': 'phrase'
                    })
                    remaining = remaining[phrase_len:]
                    matched = True
                    break

            if not matched:
                # 未匹配，单字处理
                if remaining[0] not in STOPWORDS:
                    phrases.append({
                        'text': remaining[0],
                        'type': 'char'
                    })
                remaining = remaining[1:]

        return phrases

    def normalize_numbers(self, text):
        """
        数字归一化
        将中文数字转换为阿拉伯数字

        例如: "往前走三米左转九十度" → "往前走3米左转90度"

        参数:
            text: 输入文本

        返回:
            str: 归一化后的文本
        """
        def chinese_to_number(cn_str):
            """将中文数字转换为阿拉伯数字"""
            try:
                # 处理纯数字情况
                if cn_str.isdigit():
                    return int(cn_str)

                # 中文数字转换
                result = 0
                temp = 0
                unit = 1

                for char in reversed(cn_str):
                    if char in '零一二三四五六七八九':
                        temp += self.chinese_num_map.get(char, 0)
                    elif char == '十':
                        temp = temp * 10 if temp > 0 else 10
                        result += temp * unit
                        temp = 0
                        unit = 1
                    elif char == '百':
                        temp = temp * 100 if temp > 0 else 100
                        result += temp * unit
                        temp = 0
                        unit = 1
                    elif char == '千':
                        temp = temp * 1000 if temp > 0 else 1000
                        result += temp * unit
                        temp = 0
                        unit = 1

                result += temp * unit
                return result
            except Exception:
                return cn_str

        # 匹配数字模式：中文数字 + 单位
        pattern = r'([零一二三四五百千万百千十]+)(米|度|秒|次|m|s)?'

        def replace_func(match):
            num_str = match.group(1)
            unit = match.group(2) or ''
            try:
                number = chinese_to_number(num_str)
                return f"{number}{unit}"
            except Exception:
                return match.group(0)

        return re.sub(pattern, replace_func, text)

    def preprocess(self, text):
        """
        综合预处理流程

        参数:
            text: 输入文本

        返回:
            dict: 包含分词、短语、数字归一化结果
        """
        # 1. 数字归一化
        normalized_text = self.normalize_numbers(text)

        # 2. 分词
        words = self.segment(normalized_text)

        # 3. 短语检测
        phrases = self.detect_phrases(normalized_text)

        return {
            'original': text,
            'normalized': normalized_text,
            'words': words,
            'phrases': phrases
        }


def test_preprocessor():
    """测试文本预处理器"""
    preprocessor = TextPreprocessor()

    test_cases = [
        "往前走三米",
        "往后退五米然后左转九十度",
        "停止",
        "提速到0.5米每秒",
        "掉头一百八十度"
    ]

    for text in test_cases:
        result = preprocessor.preprocess(text)
        print(f"\n输入: {text}")
        print(f"归一化: {result['normalized']}")
        print(f"分词: {' / '.join(result['words'])}")
        detected = [p['text'] + '→' + p['intent'] for p in result['phrases'] if p['type'] == 'phrase']
        print(f"短语检测: {detected}")


if __name__ == '__main__':
    test_preprocessor()
