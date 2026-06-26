# Spark实践版 — 04-4 YOLOv9/v10/v11/v12 演进

适配说明：`leo_vision` → `vision_basics`，代码路径 `src/ros2_vision/vision_basics/`
参考文档 token：`O49zdveDBoBlK4xzf2ycbkIRnDd`

---

## 📦 环境准备

1. **安装 ultralytics**（需要 ≥8.2.0 才支持 YOLO11/YOLO12）
   ```bash
   pip3 install --upgrade ultralytics
   python3.10 -c "from ultralytics import YOLO; print(YOLO('yolov8n.pt').task)"
   ```

2. **确认 PyTorch**
   ```bash
   python3.10 -c "import torch; print(torch.__version__)"
   ```

3. **确认 ROS2 环境**
   ```bash
   sudo apt install ros-humble-cv-bridge ros-humble-ament-index-python
   ```

4. **下载模型**（v9c/v10n/v11n/v12n 均 ~5-25MB，GFW 可能阻断）
   ```bash
   # 方式 A：Python 自动下载（推荐，但需翻墙）
   python3.10 -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"
   # 方式 B：wget GitHub releases
   wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt \
     -O src/ros2_vision/vision_basics/model/yolo11n.pt
   wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov10n.pt \
     -O src/ros2_vision/vision_basics/model/yolov10n.pt
   # 方式 C：从其他机器 scp
   # ⚠️ yolov9c.pt 和 yolo12n.pt 可能不在 ultralytics assets 中，需从官方 repo 获取
   ```

5. **编译 vision_basics**
   ```bash
   cd /home/spark/Music/spark_humble
   colcon build --packages-select vision_basics
   ```

6. **确认模型路径**
   ```bash
   source install/setup.bash
   python3.10 src/ros2_vision/vision_basics/vision_basics/yolo_model_info.py
   ```

7. **ROS2 冒烟测试**（04-4 无 ROS2 节点，跳过此步）

---

## 参考版结构 & 实践版插入点

参考版共 7 章。这是一门**纯理论对比课**——代码量极少，重点是理解架构创新。

### 第 1 章 — 为什么 YOLO 还在演进？
参考版内容：04-1 回顾、v8 三大局限（信息瓶颈/NMS延迟/特征提取）、4 大演进方向。
实践版插入：
- `yolo_model_info.py` — 插入到第 1 章末尾，作为「1.X 实践：看看你有哪些模型」

### 第 2 章 — YOLOv9 深度解析
参考版内容：PGI（可编程梯度信息）、GELAN 架构、实验对比。
实践版插入：无（理论章节）

### 第 3 章 — YOLOv10 端到端实时检测
参考版内容：NMS-free 设计、一致性匹配。
实践版插入：无（理论章节）

### 第 4 章 — YOLO11 Ultralytics 2024
参考版内容：C3k2 主干、新任务支持、v8→v11 迁移指南。
实践版插入：无（理论章节）

### 第 5 章 — YOLO12 注意力机制回归
参考版内容：Area Attention、精度速度权衡。
实践版插入：无（理论章节）

### 第 6 章 — 选型决策树与实战
参考版内容：5 版本横向对比表、决策树、一键迁移脚本。
实践版插入：
- `yolo_version_compare.py` — 插入到第 6 章末尾，作为「6.X 实践：本地版本横向对比」

### 第 7 章 — 综合实验
参考版内容：v8 vs v9 vs v11 在自定义数据集上对比（需要 04-9 训练基础）。
实践版插入：无（04-9 尚未完成，自定义数据集训练暂不可用）

---

## 参考版关键问题

- **ultralytics 版本要求**：YOLO11 和 YOLO12 需要 ultralytics ≥8.2.0。旧版本会报 `ModuleNotFoundError` 或 `Unknown model`。实践版在环境准备中强调升级。
- **模型下载受阻（GFW）**：v9c/v10n/v11n/v12n 在国内网络下自动下载大概率失败。实践版 `yolo_version_compare.py` 做了容错处理——本地有的跑，没有的跳过并打印原因。课程提供 3 种下载方式。
- **v9 和 v12 模型获取困难**：yolov9c.pt 和 yolo12n.pt 不在 ultralytics 标准 assets 发布中，需从各自官方 GitHub repo 下载。实际对比以 v8n + v10n + v11n 为主。
- **`model.info()` 返回值问题**：ultralytics 的 `model.info()` 打印到 stdout 但不返回 dict。实践版用 `sum(p.numel())` 从 PyTorch 提取参数数量，更可靠。
- **纯理论课无 ROS2 节点**：04-4 是版本演进对比，不需要实时相机。这与 04-5（RT-DETR 有 ROS2 节点）不同。
- **依赖 04-9**：参考版第 7 章（自定义数据集对比）依赖 04-9 自定义训练。实践版标注为「04-9 完成后可补」。

---

## 程序清单

### 本地程序

- `yolo_model_info.py` — 扫描本地模型目录，打印每个模型的文件名/任务类型/大小/参数量。纯信息查询，不做推理。插入到「第 1 章」末尾。
- `yolo_version_compare.py` — 在同一张图上运行多个 YOLO 版本（v8n/v9c/v10n/v11n/v12n），对比检测框数、推理时间、模型大小、参数量，并排可视化。插入到「第 6 章」末尾。

---

## 1. yolo_model_info.py — 本地模型速查

### 插入位置
参考版「第 1 章 为什么 YOLO 还在演进？」末尾，作为「1.X 实践：看看你有哪些模型」

### 参考版描述
参考版第 1 章回顾 YOLO 演进时间线（v1→v8→v9→v10→v11→v12），纯文字叙述。

### 参考版审查
- ✅ 演进时间线清晰
- ⚠️ 缺少「学员当前有什么模型」的落地——看完时间线不知道本地装了哪些

### 设计原因
在第 1 章讲完「为什么 YOLO 还在演进」之后，让学员**亲眼看到自己本地有哪些模型**。这是「从理论到实践」的第一步——知道 v8n 在本地、v11n 没有，自然产生「我要下载新版本试试」的动机。

程序不做推理，只读模型头（任务类型 + 参数量），秒级完成。包含下载新模型的提示。

### 完整代码

```python
#!/usr/bin/env python3
"""
YOLO 模型信息速查

打印本地所有可用 YOLO 模型的元信息：大小、参数、任务类型。
不运行推理，只读模型头。

用法：
    python3 yolo_model_info.py
"""

import os
from ament_index_python.packages import get_package_share_directory
from ultralytics import YOLO

MODEL_DIR = os.path.join(get_package_share_directory('vision_basics'), 'model')


def main():
    if not os.path.isdir(MODEL_DIR):
        print(f'模型目录不存在: {MODEL_DIR}')
        return

    pts = sorted([f for f in os.listdir(MODEL_DIR) if f.endswith('.pt')])

    if not pts:
        print('模型目录为空')
        return

    print(f'模型目录: {MODEL_DIR}')
    print(f'共 {len(pts)} 个模型\n')
    print(f'{"文件":<22} {"任务":<10} {"大小MB":<8} {"参数M":<8}')
    print('-' * 50)

    total_mb = 0
    for pt in pts:
        path = os.path.join(MODEL_DIR, pt)
        size_mb = os.path.getsize(path) / 1e6
        total_mb += size_mb

        try:
            model = YOLO(path)
            task = model.task
            try:
                import torch
                params_m = sum(p.numel() for p in model.model.parameters()) / 1e6
            except Exception:
                params_m = 0
        except Exception:
            task = '?'
            params_m = 0

        print(f'{pt:<22} {task:<10} {size_mb:<8.1f} {params_m:<8.1f}')

    print('-' * 50)
    print(f'总计: {total_mb:.1f} MB')

    print('\n💡 要下载新模型（如 YOLO11n）：')
    print('   from ultralytics import YOLO; YOLO("yolo11n.pt")  # 自动下载')


if __name__ == '__main__':
    main()
```

### 执行流程

1. 读取 `get_package_share_directory('vision_basics')/model/` 目录
2. 遍历所有 `.pt` 文件
3. 逐个调用 `YOLO(path)` 加载 → 读取 `model.task`（detect/segment/pose）
4. 用 `sum(p.numel() for p in model.model.parameters())` 统计参数量
5. 打印表格：文件名 | 任务 | 大小MB | 参数M
6. 底部提示如何下载新模型

---

## 2. yolo_version_compare.py — 多版本横向对比

### 插入位置
参考版「第 6 章 选型决策树与实战」末尾，作为「6.X 实践：本地版本横向对比」

### 参考版描述
参考版第 6 章提供了 5 版本横向对比表（mAP/FPS/Params/FLOPs）和决策树，但数据来自 COCO 论文——不是学员自己机器上的实测数据。

### 参考版审查
- ✅ 对比维度全面（mAP + FPS + 参数 + FLOPs）
- ⚠️ 对比数据来自论文，不是本地实测——学员不知道「在我的机器上哪个快」
- ⚠️ 无并排可视化——纯表格看不出检测效果差异

### 设计原因
在学完 5 个版本的理论差异后，让学员**在自己的机器上实测**各版本的表现。核心价值：

1. **真实速度**：论文的 FPS 是 V100 GPU，学员的可能是 CPU/低端 GPU——实测才知道真相
2. **并排可视化**：同一张图 5 个版本并排显示，一目了然看出检测效果的差异
3. **容错设计**：本地没有的模型自动跳过（标记「❌失败」），不会中断整体流程
4. **选型启发**：实测数据 + 可视化 → 学员自己做出选型判断

程序先预热一次（消除首次加载开销），再计时推理，确保对比公平。

### 完整代码

```python
#!/usr/bin/env python3
"""
YOLO 版本横向对比

在同一张图上运行多个 YOLO 模型，对比：
  - 检测框数量
  - 推理时间（ms）
  - 模型大小（MB）
  - 参数数量（M）

模型优先从本地加载，本地没有则尝试自动下载。

用法：
    python3 yolo_version_compare.py               # 用 lena.png
    python3 yolo_version_compare.py image.jpg     # 自定义图片
"""

import os, sys, time
from ament_index_python.packages import get_package_share_directory
import cv2
import numpy as np
from ultralytics import YOLO

MODEL_DIR = os.path.join(get_package_share_directory('vision_basics'), 'model')
_base = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.join(_base, '..')

# ── 候选模型列表（名称, 展示名, 任务类型）──
CANDIDATES = [
    ('yolov8n.pt',       'YOLOv8n (2023)',       'detect'),
    ('yolov9c.pt',       'YOLOv9c (2024.2)',     'detect'),
    ('yolov10n.pt',      'YOLOv10n (2024.5)',    'detect'),
    ('yolo11n.pt',       'YOLO11n (2024.9)',     'detect'),
    ('yolo12n.pt',       'YOLO12n (2025.2)',     'detect'),
]


def get_model_path(name):
    """本地路径优先"""
    local = os.path.join(MODEL_DIR, name)
    return local if os.path.exists(local) else name


def truncate_model_info(model):
    """提取模型元信息"""
    try:
        import torch
        params_m = sum(p.numel() for p in model.model.parameters()) / 1e6
        flops_b = 0  # GFLOPs not reliably available
        return params_m, flops_b
    except Exception:
        return 0, 0


def main():
    img_path = sys.argv[1] if len(sys.argv) > 1 else f'{PROJ_DIR}/pictures/lena.png'
    if not os.path.exists(img_path):
        print(f'图片不存在: {img_path}')
        return

    img = cv2.imread(img_path)
    print(f'测试图片: {os.path.basename(img_path)} ({img.shape[1]}×{img.shape[0]})')
    print()
    print(f'{"模型":<28} {"状态":<8} {"框数":<6} {"时间ms":<8} {"大小MB":<8} {"参数M":<8}')
    print('-' * 72)

    results_data = []

    for fname, label, task in CANDIDATES:
        path = get_model_path(fname)
        status = '本地' if path != fname else '下载'

        try:
            model = YOLO(path)
            size_mb = os.path.getsize(path) / 1e6 if os.path.exists(path) else 0
            params_m, flops_b = truncate_model_info(model)

            # 预热一次
            _ = model(img, verbose=False)

            # 计时推理
            t0 = time.time()
            results = model(img, conf=0.25, verbose=False)
            elapsed = (time.time() - t0) * 1000

            r = results[0]
            n_boxes = len(r.boxes) if r.boxes is not None else 0
            annotated = r.plot()

            results_data.append((label, annotated, n_boxes, elapsed, size_mb, params_m))

            print(f'{label:<28} {status:<8} {n_boxes:<6} {elapsed:<8.1f} {size_mb:<8.1f} {params_m:<8.1f}')

        except Exception as e:
            short = str(e).split('\n')[0][:60]
            print(f'{label:<28} {"❌失败":<8} {"-":<6} {"-":<8} {"-":<8} {"-":<8}')
            print(f'  原因: {short}')

    # ── 并排对比图 ──
    if len(results_data) >= 1:
        panels = []
        for label, annotated, n, t, sz, p in results_data:
            h, w = annotated.shape[:2]
            cv2.putText(annotated, f'{label} | {n}框 {t:.0f}ms',
                        (5, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            panels.append(annotated)

        # 拼成一行（最多 3 列）
        max_h = max(p.shape[0] for p in panels)
        rows = []
        for i in range(0, len(panels), 3):
            row = panels[i:i+3]
            row_resized = []
            for p in row:
                scale = max_h / p.shape[0]
                rw = int(p.shape[1] * scale)
                row_resized.append(cv2.resize(p, (rw, max_h)))
            rows.append(np.hstack(row_resized))

        comparison = np.vstack(rows)
        cv2.imshow('YOLO 版本对比 — 按任意键退出', comparison)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    print()
    print('窗口显示对比结果，按任意键关闭。')


if __name__ == '__main__':
    main()
```

### 执行流程

1. 遍历 CANDIDATES 列表（v8n → v9c → v10n → v11n → v12n）
2. 对每个模型：
   - 检查本地是否存在 → 存在用本地，不存在用 ultralytics 自动下载
   - 加载模型 → 提取参数量 → 记录文件大小
   - 预热推理 1 次（消除首次加载开销）
   - 正式推理 + 计时
   - 获取检测框数量
   - `result.plot()` 生成标注图
3. 终端打印对比表格
4. 将所有标注图拼成并排对比大图（最多 3 列）
5. cv2.imshow 显示 → 按任意键退出

---

## 运行步骤

### yolo_model_info.py

```bash
cd /home/spark/Music/spark_humble && source install/setup.bash
python3.10 src/ros2_vision/vision_basics/vision_basics/yolo_model_info.py
```

预期输出：
```
模型目录: .../install/vision_basics/share/vision_basics/model
共 6 个模型

文件                     任务         大小MB     参数M
--------------------------------------------------
...
yolov8n.pt             detect     6.5      3.2
yolov8n-seg.pt         segment    7.1      3.4
...
--------------------------------------------------
总计: 445.2 MB
```

### yolo_version_compare.py

```bash
cd /home/spark/Music/spark_humble && source install/setup.bash
export DISPLAY=:0

# 使用默认 lena.png
python3.10 src/ros2_vision/vision_basics/vision_basics/yolo_version_compare.py

# 或指定图片
python3.10 src/ros2_vision/vision_basics/vision_basics/yolo_version_compare.py /path/to/image.jpg
```

预期输出：
- 终端打印对比表格（v8n 有数据，v9c/v10n/v11n/v12n 可能因未下载而标记「❌失败」）
- 弹出窗口 "YOLO 版本对比"，并排显示各版本的检测结果
- 每个面板左下角标注：模型名 | N框 | Xms
- 按任意键关闭

### 下载新模型（可选）

```bash
cd /home/spark/Music/spark_humble
# 推荐从 yolo11n 开始（Ultralytics 官方主推，最易下载）
python3.10 -c "
from ultralytics import YOLO
import shutil, os
# 自动下载到当前目录
m = YOLO('yolo11n.pt')
# 移动到模型目录
shutil.move('yolo11n.pt', 'src/ros2_vision/vision_basics/model/yolo11n.pt')
print('✅ yolo11n.pt 已下载')
"
# 重新编译
colcon build --packages-select vision_basics
# 再次运行对比
source install/setup.bash
python3.10 src/ros2_vision/vision_basics/vision_basics/yolo_version_compare.py
```

### 编译

```bash
cd /home/spark/Music/spark_humble
colcon build --packages-select vision_basics
# 预期：Summary: 1 package finished
```

---

## ⚠️ 常见坑

### v9/v10/v11/v12 模型下载失败

**症状**：运行对比脚本时 v9c/v10n/v11n/v12n 全部显示「❌失败」
**原因**：GFW 阻断 GitHub，ultralytics 自动下载走 GitHub releases
**解决**：
- 找一台能翻墙的机器下载 → scp 到 Spark
- 或使用 wget 直连（可能也受阻）
- 至少保留 v8n 做基准对比，先学版本间差异理论

### `model.info()` 不返回参数

**症状**：调用 `model.info()` 后终端打印参数信息但返回 `None`
**原因**：ultralytics 的 `info()` 设计为打印到 stdout，返回值不稳定
**解决**：实践版用 `sum(p.numel() for p in model.model.parameters()) / 1e6` 直接统计

### ultralytics 版本太旧

**症状**：加载 yolo11n.pt 时报 `Unknown model` 或 `ModuleNotFoundError`
**原因**：ultralytics < 8.2.0 不支持 YOLO11/YOLO12
**解决**：`pip3 install --upgrade ultralytics`

### SAM 模型显示 task=?

**症状**：`yolo_model_info.py` 中 sam_b.pt 的任务类型显示为 `?`
**原因**：SAM 不是标准 YOLO 模型，`model.task` 可能为 None
**解决**：这是正常的——SAM 是 `from ultralytics import SAM` 加载的独立模型类
