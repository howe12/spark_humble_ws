#!/usr/bin/env python3
"""
md2feishu.py — Markdown → 飞书 Docx Block 转换器

支持的 Markdown 语法:
  # ## ###        → 标题 (heading1/2/3)
  **粗体**        → 粗体内联
  *斜体*          → 斜体内联
  `行内代码`      → 行内代码
  ~~删除线~~      → 删除线
  [文字](url)     → 超链接
  - 无序列表      → bullet list
  1. 有序列表     → ordered list
  ---             → 分割线
  ```代码块```    → 代码块
  > 引用          → 引用块

用法:
  python3 md2feishu.py input.md
  → 输出 JSON blocks 数组到 stdout

作为 library:
  from md2feishu import md_to_blocks
  blocks = md_to_blocks(markdown_string)
"""

import re
import json
import sys


# ── 内联解析 ──
INLINE_RE = re.compile(
    r'(\*\*(.+?)\*\*)|'           # **bold**
    r'(\*(.+?)\*)|'               # *italic*
    r'(~~(.+?)~~)|'               # ~~strikethrough~~
    r'(`(.+?)`)|'                 # `inline code`
    r'(\[(.+?)\]\((.+?)\))'       # [text](url)
)


def parse_inline(text):
    """将一行 Markdown 文本解析为飞书 text_run 元素列表。
    
    例: "用 `YOLO()` **自动**下载"
    → [
        {"text_run": {"content": "用 "}},
        {"text_run": {"content": "YOLO()", "text_element_style": {"inline_code": True}}},
        {"text_run": {"content": " "}},
        {"text_run": {"content": "自动", "text_element_style": {"bold": True}}},
        {"text_run": {"content": "下载"}},
    ]
    """
    elements = []
    pos = 0

    for m in INLINE_RE.finditer(text):
        start, end = m.start(), m.end()

        # 匹配前的纯文本
        if pos < start:
            elements.append({"text_run": {"content": text[pos:start]}})

        if m.group(1):   # **bold**
            content = m.group(2)
            elements.append({"text_run": {
                "content": content,
                "text_element_style": {"bold": True}
            }})
        elif m.group(3):  # *italic*
            content = m.group(4)
            elements.append({"text_run": {
                "content": content,
                "text_element_style": {"italic": True}
            }})
        elif m.group(5):  # ~~strikethrough~~
            content = m.group(6)
            elements.append({"text_run": {
                "content": content,
                "text_element_style": {"strikethrough": True}
            }})
        elif m.group(7):  # `inline code`
            content = m.group(8)
            elements.append({"text_run": {
                "content": content,
                "text_element_style": {"inline_code": True}
            }})
        elif m.group(9):  # [text](url)
            link_text = m.group(10)
            link_url = m.group(11)
            elements.append({"text_run": {
                "content": link_text,
                "text_element_style": {"link": {"url": link_url}}
            }})

        pos = end

    # 剩余纯文本
    if pos < len(text):
        elements.append({"text_run": {"content": text[pos:]}})

    return elements if elements else [{"text_run": {"content": text}}]


def parse_inline_text(text):
    """解析文本，返回带换行的 elements 列表。每行末尾附加 \n"""
    elements = []
    lines = text.split('\n')
    for line in lines:
        elements.extend(parse_inline(line))
        elements.append({"text_run": {"content": "\n"}})
    return elements


# ── 块级解析 ──

LANG_MAP = {
    'python': 21, 'py': 21,
    'bash': 2, 'sh': 2, 'shell': 2,
    'yaml': 11, 'yml': 11,
    'json': 17,
    'cpp': 16, 'c': 16,
    'javascript': 6, 'js': 6,
    '': 1,   # plain text
}


def detect_lang(info_string):
    """从 ```python 中提取语言 ID"""
    lang = info_string.strip().lower().split()[0] if info_string else ''
    return LANG_MAP.get(lang, 1)


def md_to_blocks(md_text):
    """Markdown 文本 → 飞书 Block JSON 数组
    
    Args:
        md_text: Markdown 字符串
        
    Returns:
        list[dict]: 飞书 Block 对象数组，可直接作为 children 参数
    """
    lines = md_text.split('\n')
    blocks = []
    
    # 状态
    in_code_block = False
    code_lang = ''
    code_lines = []
    
    in_bullet_list = False
    bullet_items = []
    
    in_ordered_list = False
    ordered_items = []
    
    in_blockquote = False
    quote_lines = []
    
    text_buf = []  # 普通文本缓冲
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # ── 代码块 ──
        if stripped.startswith('```'):
            if in_code_block:
                # 结束代码块
                els = []
                for cl in code_lines:
                    els.extend(parse_inline(cl))
                    els.append({"text_run": {"content": "\n"}})
                blocks.append({
                    "block_type": 14,
                    "code": {
                        "elements": els,
                        "style": {"language": detect_lang(code_lang)}
                    }
                })
                code_lines = []
                in_code_block = False
                code_lang = ''
            else:
                # 开始代码块
                if text_buf:
                    blocks.append(_flush_text(text_buf))
                    text_buf = []
                code_lang = stripped[3:].strip()
                in_code_block = True
            i += 1
            continue
        
        if in_code_block:
            code_lines.append(line)
            i += 1
            continue
        
        # ── 引用块 ──
        if stripped.startswith('> '):
            if text_buf:
                blocks.append(_flush_text(text_buf))
                text_buf = []
            quote_lines.append(stripped[2:])
            # 检查下一行是否还是引用
            if i + 1 < len(lines) and lines[i + 1].strip().startswith('> '):
                i += 1
                continue
            else:
                # 结束引用
                text = ' '.join(quote_lines)
                blocks.append({
                    "block_type": 34,
                    "quote": {"elements": parse_inline(text)}
                })
                quote_lines = []
                i += 1
                continue
        
        # ── 分割线 ──
        if stripped == '---':
            if text_buf:
                blocks.append(_flush_text(text_buf))
                text_buf = []
            blocks.append({"block_type": 42, "divider": {}})
            i += 1
            continue
        
        # ── 标题 ──
        heading_match = re.match(r'^(#{1,3})\s+(.+)', stripped)
        if heading_match:
            if text_buf:
                blocks.append(_flush_text(text_buf))
                text_buf = []
            level = len(heading_match.group(1))
            content = heading_match.group(2)
            key = ['', 'heading1', 'heading2', 'heading3'][level]
            blocks.append({
                "block_type": 2 + level,
                key: {
                    "elements": parse_inline(content),
                    "style": {}
                }
            })
            i += 1
            continue
        
        # ── 无序列表 ──
        bullet_match = re.match(r'^(\s*)-\s+(.+)', stripped)
        if bullet_match:
            if text_buf:
                blocks.append(_flush_text(text_buf))
                text_buf = []
            indent = len(bullet_match.group(1))
            content = bullet_match.group(2)
            bullet_items.append((indent, content))
            # 检查下一行
            if i + 1 < len(lines) and re.match(r'^(\s*)-\s+', lines[i + 1].strip()):
                i += 1
                continue
            else:
                # 结束列表
                for ind, cont in bullet_items:
                    blocks.append({
                        "block_type": 12,
                        "bullet": {
                            "elements": parse_inline(cont.rstrip()),
                            "style": {"indent_level": ind // 2}
                        }
                    })
                bullet_items = []
                i += 1
                continue
        
        # ── 有序列表 ──
        ordered_match = re.match(r'^(\s*)\d+\.\s+(.+)', stripped)
        if ordered_match:
            if text_buf:
                blocks.append(_flush_text(text_buf))
                text_buf = []
            indent = len(ordered_match.group(1))
            content = ordered_match.group(2)
            ordered_items.append((indent, content))
            if i + 1 < len(lines) and re.match(r'^(\s*)\d+\.\s+', lines[i + 1].strip()):
                i += 1
                continue
            else:
                for ind, cont in ordered_items:
                    blocks.append({
                        "block_type": 13,
                        "ordered": {
                            "elements": parse_inline(cont.rstrip()),
                            "style": {"indent_level": ind // 2}
                        }
                    })
                ordered_items = []
                i += 1
                continue
        
        # ── 空行：刷新文本缓冲 ──
        if stripped == '':
            if text_buf:
                text_buf.append('')
            else:
                blocks.append({"block_type": 2, "text": {
                    "elements": [{"text_run": {"content": " "}}],
                    "style": {}
                }})
            i += 1
            continue
        
        # ── 普通文本 ──
        text_buf.append(line)
        i += 1
    
    # 刷新剩余
    if text_buf:
        blocks.append(_flush_text(text_buf))
    if bullet_items:
        for ind, cont in bullet_items:
            blocks.append({
                "block_type": 12,
                "bullet": {"elements": parse_inline(cont.rstrip()), "style": {"indent_level": ind // 2}}
            })
    if ordered_items:
        for ind, cont in ordered_items:
            blocks.append({
                "block_type": 13,
                "ordered": {"elements": parse_inline(cont.rstrip()), "style": {"indent_level": ind // 2}}
            })
    
    return blocks


def _flush_text(lines):
    """将文本缓冲刷新为一个 text block"""
    text = '\n'.join(lines)
    if not text.strip():
        return {"block_type": 2, "text": {
            "elements": [{"text_run": {"content": " "}}],
            "style": {}
        }}
    elements = parse_inline_text(text)
    return {"block_type": 2, "text": {"elements": elements, "style": {}}}


# ── CLI ──

def main():
    if len(sys.argv) < 2:
        print("用法: python3 md2feishu.py input.md [output.json]", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        md_text = f.read()

    blocks = md_to_blocks(md_text)

    if len(sys.argv) > 2:
        with open(sys.argv[2], 'w', encoding='utf-8') as f:
            json.dump({"children": blocks}, f, ensure_ascii=False, indent=2)
        print(f"✅ {len(blocks)} blocks → {sys.argv[2]}", file=sys.stderr)
    else:
        print(json.dumps({"children": blocks}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
