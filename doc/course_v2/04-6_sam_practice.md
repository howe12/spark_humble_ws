# Spark实践版 — 04-6 SAM/SAM2 分割一切

> 基于 Spark `vision_basics` 包，`sam_b.pt` 模型（**358MB**，本课程最大模型）。
> 参考版 7 章涵盖 SAM 原理→实战→SAM2 视频分割→机器人应用。
> 实践版聚焦 **SAM 自动分割** + **SAM 交互式点提示**——这是 SAM 最独特的能力：「点哪切哪」。

---

## 📦 环境准备

> 如果你已完成 04-1/04-3/04-5 的环境配置，只需额外确认步骤 4（sam_b.pt）。

### 1. ultralytics（SAM 通过 ultralytics 加载）

```bash
pip install ultralytics
python3.10 -c "from ultralytics import SAM; print('OK')"
# → OK
```

### 2. OpenCV

```bash
python3.10 -c "import cv2; print(cv2.__version__)"
# → 4.9.0
```

### 3. NumPy（masks 数据处理）

```bash
python3.10 -c "import numpy; print(numpy.__version__)"
# → 1.24.x 或更高
```

### 4. SAM 模型（⚠️ 358MB，最大模型）

```bash
# 方式 1：Python 自动下载（需科学上网 + 耐心等待 ~5 分钟）
cd ~/Music/spark_humble/src/ros2_vision/vision_basics/model/
python3.10 -c "from ultralytics import SAM; SAM('sam_b.pt')"

# 方式 2：wget
wget https://github.com/ultralytics/assets/releases/download/v8.2.0/sam_b.pt

# 方式 3：从老师/同学那里拷贝（推荐——太大了）
scp user@source:/path/to/sam_b.pt .

# 验证
ls -lh sam_b.pt     # → 358MB（375,000,000+ 字节）
python3.10 -c "from ultralytics import SAM; m=SAM('sam_b.pt'); print(m.task)"
# → segment
```

### 5. 编译

```bash
cd ~/Music/spark_humble
source /opt/ros/humble/setup.bash
colcon build --packages-select vision_basics
source install/setup.bash
```

### 6. 验证模型路径

```bash
python3.10 -c "
from ament_index_python.packages import get_package_share_directory
import os
path = os.path.join(get_package_share_directory('vision_basics'), 'model', 'sam_b.pt')
print('路径:', path)
print('存在:', os.path.exists(path))
print('大小:', os.path.getsize(path)/1e6, 'MB')
"
# → 存在: True  大小: 375.0 MB
```

---

## 参考版结构 & 实践版插入点

参考版 7 章。实践版聚焦第 3 章实战部分：

### 第 1~2 章 — 为什么需要 SAM / SAM 原理
参考版内容：分割 vs 检测的区别、Image Encoder + Prompt Encoder + Mask Decoder 三组件架构。
实践版：**保留理论**，不另写。

### 第 3 章 — SAM 实战
参考版内容：Python 加载 SAM → 自动分割 + 点提示分割。
实践版插入：
- `sam_auto.py` → 替换「3.2 自动分割」— 自动分割所有区域 + 随机颜色显示
- `sam_prompt.py` → 替换「3.3 交互式分割」— **鼠标点击分割**（左键=前景，右键=背景）

### 第 4~7 章 — SAM2 / 机器人应用 / 生态
实践版：SAM2 需要 GPU 和视频输入，Spark 的 CPU 上不实际。保留参考版理论，不另写。

> ⚠️ SAM 在 CPU 上很慢（自动分割一张图 10~30 秒），**不适合 ROS2 实时**——所以实践版不提供 ROS2 节点。这是 SAM 和 YOLO 的根本区别：SAM 是「精度优先」的分割工具，不是实时检测器。

---

## 参考版关键问题

- **模型超大（358MB）**：是本课程所有模型中最大的。需要专门的下载教程和耐心等待。
- **SAM 不是 YOLO**：虽然通过 ultralytics 加载（`from ultralytics import SAM`），但 API 不同——用 `SAM()` 而不是 `YOLO()`，结果用 `masks.data` 而不是 `boxes`。
- **CPU 上极慢**：自动分割一帧 10~30 秒，绝对不适合实时应用。这是教学要点——让学生理解「精度 vs 速度」的 tradeoff。
- **sam_b.pt 不在 GitHub**：>100MB 限制，.gitignore 排除。必须单独获取。

---

## SAM vs YOLO 速查

```python
# YOLO：目标检测，输出边界框
model = YOLO('yolov8n.pt')
results = model('image.jpg')
boxes = results[0].boxes     # [x1,y1,x2,y2] 矩形框
for box in boxes:
    cls, conf = int(box.cls), float(box.conf)
    print(f'{results[0].names[cls]}: {conf:.2f}')

# SAM：分割一切，输出像素级 mask
model = SAM('sam_b.pt')
results = model('image.jpg')
masks = results[0].masks     # (N,H,W) 布尔数组——每个像素属于哪个物体
if masks is not None:
    for i, mask in enumerate(masks.data):
        print(f'物体 {i}: {mask.sum()} 像素')  # 精确到像素！
```

---

## 程序清单

- `sam_auto.py` — 自动分割一切（全图所有区域）
- `sam_prompt.py` 🔴 — **鼠标交互式分割**（点哪切哪——SAM 最独特的卖点）

所有程序在 `vision_basics/vision_basics/` 下。

---

# 程序 1：自动分割一切

`sam_auto.py` 加载 SAM，自动找出图中所有可分割区域，用随机颜色叠加上去。

```python
#!/usr/bin/env python3
"""
SAM 自动分割一切

加载 SAM 模型，自动分割图片中的所有目标，用随机颜色显示。
不需要任何 prompt — 自动找出图中所有可分割区域。

用法：
    python3 sam_auto.py                 # lena.png
    python3 sam_auto.py image.jpg       # 自定义图片

模型：sam_b.pt（约 358MB）
"""

import os, sys
from ament_index_python.packages import get_package_share_directory
import cv2
import numpy as np
from ultralytics import SAM

MODEL_DIR = os.path.join(get_package_share_directory('vision_basics'), 'model')
_base = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.join(_base, '..')


def get_model(name):
    local = os.path.join(MODEL_DIR, name)
    return local if os.path.exists(local) else name


def main():
    model_path = get_model('sam_b.pt')
    print(f'模型: {model_path}')
    m = SAM(model_path)
    print(f'任务: {m.task}')

    img_path = sys.argv[1] if len(sys.argv) > 1 else f'{PROJ_DIR}/pictures/lena.png'
    img = cv2.imread(img_path)
    print(f'图片: {os.path.basename(img_path)} ({img.shape[1]}×{img.shape[0]})')
    print('分割中... (CPU 上约 10-30 秒，请耐心等待)')

    results = m(img, verbose=False)
    r = results[0]

    if r.masks is not None:
        masks = r.masks.data.cpu().numpy()  # (N, H, W)
        n_masks = masks.shape[0]
        print(f'找到 {n_masks} 个区域')

        # 随机颜色叠加
        overlay = np.zeros_like(img)
        for i in range(n_masks):
            color = np.random.randint(50, 255, 3).tolist()
            overlay[masks[i] > 0.5] = color

        display = cv2.addWeighted(img, 0.5, overlay, 0.5, 0)
        cv2.putText(display, f'{n_masks} regions', (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    else:
        display = img
        print('未找到可分割区域')

    cv2.imshow('SAM Auto — 按任意键退出', display)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
```

### 运行

```bash
cd ~/Music/spark_humble && source install/setup.bash
export DISPLAY=:0
python3.10 src/ros2_vision/vision_basics/vision_basics/sam_auto.py
```

### 预期输出

```
模型: .../model/sam_b.pt
任务: segment
图片: lena.png (516×514)
分割中... (CPU 上约 10-30 秒，请耐心等待)
找到 47 个区域
```

---

# 程序 2：交互式点提示分割 🔴

`sam_prompt.py` 实现 SAM 最独特的交互——**鼠标点击 → 实时分割目标**。

操作：
- 🖱️ **左键点击** = 前景点（「我要这个物体」）
- 🖱️ **右键点击** = 背景点（「不要包含这个区域」）
- ⌨️ **按 r** = 运行 SAM 推理
- ⌨️ **按 c** = 清除所有点
- ⌨️ **按 s** = 保存当前 mask 到 `/tmp/sam_mask.png`
- ⌨️ **按 q** = 退出

```python
#!/usr/bin/env python3
"""
SAM 交互式点提示分割

用鼠标点击目标 → SAM 自动分割该目标。

模型：sam_b.pt（约 358MB）
"""

import os, sys
from ament_index_python.packages import get_package_share_directory
import cv2
import numpy as np
from ultralytics import SAM

MODEL_DIR = os.path.join(get_package_share_directory('vision_basics'), 'model')
_base = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.join(_base, '..')

GREEN = (0, 255, 0)      # 前景点颜色
RED = (0, 0, 255)        # 背景点颜色
YELLOW = (0, 255, 255)   # mask 叠加颜色


def get_model(name):
    local = os.path.join(MODEL_DIR, name)
    return local if os.path.exists(local) else name


def mouse_cb(event, x, y, flags, param):
    """收集鼠标点击"""
    points, labels = param
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append([x, y])
        labels.append(1)  # 前景
        print(f'  前景点: ({x}, {y})')
    elif event == cv2.EVENT_RBUTTONDOWN:
        points.append([x, y])
        labels.append(0)  # 背景
        print(f'  背景点: ({x}, {y})')


def main():
    model_path = get_model('sam_b.pt')
    print(f'模型: {model_path}')
    m = SAM(model_path)

    img_path = sys.argv[1] if len(sys.argv) > 1 else f'{PROJ_DIR}/pictures/lena.png'
    img = cv2.imread(img_path)
    print(f'图片: {os.path.basename(img_path)} ({img.shape[1]}×{img.shape[0]})')
    print('\n操作: 左键=前景  右键=背景  r=推理  c=清除  s=保存  q=退出\n')

    points = []   # [[x,y], ...]
    labels = []   # [1/0, ...]

    cv2.namedWindow('SAM Point Prompt')
    cv2.setMouseCallback('SAM Point Prompt', mouse_cb, (points, labels))

    display = img.copy()
    mask_overlay = None

    while True:
        display = img.copy()

        for (px, py), lb in zip(points, labels):
            color = GREEN if lb == 1 else RED
            cv2.circle(display, (int(px), int(py)), 5, color, -1)
            cv2.circle(display, (int(px), int(py)), 7, color, 2)

        if mask_overlay is not None:
            display[mask_overlay] = (display[mask_overlay] * 0.5
                                     + np.array(YELLOW) * 0.5).astype(np.uint8)

        cv2.imshow('SAM Point Prompt', display)
        key = cv2.waitKey(20) & 0xFF

        if key == ord('q'):
            break
        elif key == ord('c'):
            points.clear(); labels.clear(); mask_overlay = None
            print('已清除所有点')
        elif key == ord('r'):
            if not points:
                print('请先点选至少一个点')
                continue
            print(f'推理中... ({len(points)} 个提示点)')
            results = m(img, points=points, labels=labels, verbose=False)
            if results[0].masks is not None:
                m_data = results[0].masks.data.cpu().numpy()
                best_idx = np.argmax(results[0].masks.conf.cpu().numpy()
                                     if hasattr(results[0].masks, 'conf')
                                     else [1])
                mask_overlay = m_data[best_idx] > 0.5
                print(f'  完成! mask 面积: {mask_overlay.sum()}px')
            else:
                print('  未生成 mask，尝试加更多点')
        elif key == ord('s') and mask_overlay is not None:
            cv2.imwrite('/tmp/sam_mask.png',
                        (mask_overlay * 255).astype(np.uint8))
            print('已保存 /tmp/sam_mask.png')

    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
```

### 运行

```bash
python3.10 src/ros2_vision/vision_basics/vision_basics/sam_prompt.py

# 自定义图片
python3.10 src/ros2_vision/vision_basics/vision_basings/sam_prompt.py ~/Pictures/cat.jpg
```

### 体验步骤

1. 在目标上**左键点击一下**（出现绿点）
2. 在不想包含的区域**右键点击一下**（出现红点）
3. 按 **r** 键 → 等 2~5 秒
4. 黄色区域就是分割结果！
5. 按 **c** 清空，换个目标再试

> 🎮 这是 SAM 最迷人的特性：**零样本分割**——不需要训练、不需要类别标签，点一下就能切出任何物体。

---

# ⚠️ 常见坑

🕳️ **模型太大，下载失败（358MB）**
- GitHub 对大文件下载不友好 + GFW = 极高失败率。
- 强烈建议从同学 U 盘拷贝，或科学上网后用下载工具。

🕳️ **CPU 推理很慢**
- 自动分割（`sam_auto`）：10~30 秒/张
- 交互式（`sam_prompt`）：2~5 秒/次
- 这是正常的！SAM 是重量级分割模型，不是实时检测器。
- GPU（CUDA）上可到 0.1 秒，但在 Spark 的 CPU 上就得等。

🕳️ **内存不足**
- SAM 加载时占用 ~1.5GB 内存。
- 确认 Spark 至少有 4GB 可用内存（`free -h`）。

🕳️ **`from ultralytics import SAM` 找不到**
- 需要 ultralytics >= 8.0.160
- `pip install --upgrade ultralytics`
