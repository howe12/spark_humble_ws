# Spark实践版 — 04-1 YOLO 目标检测

> 基于 Spark `vision_basics` 包，`yolov8n.pt` 模型（6.3MB）。
> 这是学生接触的**第一个深度学习模型**——参考版缺失的「模型从哪来」这一步，实践版补全。
> 参考版 9 章，实践版聚焦第 4/6/8/9 章实战部分，4 个可运行程序。

---

## 📦 新手第一课：模型从哪来？

> ⚠️ 这是参考版**完全缺失**的关键一步。学生在 04-1 第一次接触 .pt 模型文件，如果没人告诉他们模型怎么获取，课程直接跑不起来。

### 模型是什么？

- `.pt` 文件 = PyTorch 保存的训练好的神经网络权重
- 相当于「已经学会识别物体的脑子」，你给它图片，它输出检测结果
- 不需要重新训练，直接加载就能用

### 模型存在哪？

```
vision_basics/
├── model/                    ← 模型文件 (.pt)，.gitignore 排除（太大不进 Git）
│   ├── yolov8n.pt   6.3MB    ← 04-1 用这个（最轻量）
│   ├── yolov8s.pt   22MB
│   ├── yolov8n-seg.pt        ← 04-2 用这个
│   ├── yolov8n-pose.pt       ← 04-3 用这个
│   └── rtdetr-l.pt           ← 04-5 用这个
└── vision_basics/
    ├── yolo_detect.py         ← 加载模型: get_package_share_directory('vision_basics')
    └── ...
```

### 怎么下载第一个模型？

```bash
# 方式 1：Python 自动下载（最简单，需科学上网）
cd ~/Music/spark_humble/src/ros2_vision/vision_basics/model/
python3.10 -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# 方式 2：wget 手动下载
wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt

# 方式 3：从同学/老师那里拷贝（最快）
scp user@teacher-machine:/path/to/yolov8n.pt .

# 验证下载成功
ls -lh yolov8n.pt              # → 6.3MB
python3.10 -c "from ultralytics import YOLO; m=YOLO('yolov8n.pt'); print(m.task)"
# → detect

# 编译让程序找到模型
cd ~/Music/spark_humble
colcon build --packages-select vision_basics
source install/setup.bash
```

> 💡 这个流程适用于本课程**所有模型**（yolov8n/s/m/l/x/yolo11/rtdetr/sam 等等），唯一变的只有文件名。

---

## 📦 环境准备

> 如果你已经完成 04-3 或 04-5 的环境配置，以下步骤可以跳过。这是 04-1，可能是你的第一门实践课。

### 1. 安装 ultralytics

```bash
pip install ultralytics
python3.10 -c "from ultralytics import YOLO; print('OK')"
# → OK
```

> ⚠️ Hermes 虚拟环境的 `python3` 不带 opencv，用系统的 `python3.10`。

### 2. 确认 OpenCV

```bash
python3.10 -c "import cv2; print(cv2.__version__)"
# → 4.9.0
# 如果没有：pip install opencv-python
```

### 3. 确认 ROS2（ROS2 节点需要）

```bash
sudo apt install ros-humble-cv-bridge ros-humble-ament-index-python
source /opt/ros/humble/setup.bash && ros2 --version
# → humble
```

### 4. 编译 vision_basics

```bash
cd ~/Music/spark_humble
source /opt/ros/humble/setup.bash
colcon build --packages-select vision_basics
source install/setup.bash
```

### 5. 验证模型可被程序找到

```bash
python3.10 -c "
from ament_index_python.packages import get_package_share_directory
import os
path = os.path.join(get_package_share_directory('vision_basics'), 'model', 'yolov8n.pt')
print('模型路径:', path)
print('文件存在:', os.path.exists(path))
"
# → 模型路径: .../install/vision_basics/share/vision_basics/model/yolov8n.pt
# → 文件存在: True
```

---

## 参考版结构 & 实践版插入点

参考版 9 章。实践版聚焦 4 个实战章节：

### 第 1~3 章 — 目标检测入门 / YOLO 演进 / YOLOv1 原理
参考版内容：目标检测概念、YOLOv1-v8 演进史、网格划分/边界框回归/IoU。
实践版：**保留理论**，不另写。

### 第 4 章 — YOLOv8 安装
参考版内容：`pip install ultralytics` + `YOLO('yolov8n.pt')` 测试。
实践版插入：
- 📦 **「新手第一课：模型从哪来」**（本课程开头）——替换参考版「pip install」→ 完整的模型生命周期讲解

### 第 6 章 — 命令行与 Python 接口
参考版内容：`yolo predict model=...` CLI + `YOLO() + results[0].plot()` Python API。
实践版插入：
- `yolo_detect.py` → 替换「6.3 Python 接口」— 本地图片检测 + 打印检测框数据
- `yolo_model_info.py` 🔴 → 新增 — 扫描模型目录，对比多个模型的大小/任务类型

### 第 8 章 — 本地视频目标检测
参考版内容：`cv2.VideoCapture` + `model(frame)` 循环。
实践版插入：
- `yolo_video.py` → 替换「8.3 完整代码」— 摄像头/视频文件 + FPS 叠加

### 第 9 章 — ROS2 相机实时检测
参考版内容：订阅 D435 话题 + 实时推理。
实践版插入：
- `ros2_yolo.py` → 替换「9.3 完整代码」— Spark D435 话题 + 终端日志输出

---

## 参考版关键问题

- **首次运行缺模型下载教程**：参考版直接 `YOLO('yolov8n.pt')` 让学生首次运行时等自动下载（GFW 下漫长且可能失败）。实践版开头补全《新手第一课：模型从哪来》。
- **模型路径不可靠**：参考版依赖 ultralytics 的缓存目录（`~/.config/ultralytics/`），换机器就找不到。实践版用 `get_package_share_directory('vision_basics')` 从包内加载。
- **路径写死 leo**：所有代码路径引用 `leo_agv`、`leo_yolov8_class`。
- **无模型管理意识**：参考版不教学生怎么看模型大小、任务类型、存放位置。实践版 `yolo_model_info.py` 补上模型管理能力。
- **ROS2 话题需适配**：参考版话题需改为 Spark D435 的 `/camera/camera/color/image_raw`。

---

## 程序清单

### 本地程序

- `yolo_detect.py` — 本地图片检测 + 打印框数据
- `yolo_video.py` — 摄像头/视频实时检测 + FPS
- `yolo_model_info.py` 🔴 — **模型目录扫描**（大小/任务/统计）

### ROS2 相机程序

- `ros2_yolo.py` — D435 实时检测 + 终端日志

所有程序在 `vision_basics/vision_basics/` 下。

---

# 第 6 章：第一行代码 — YOLO Python API

## 程序 1：本地图片检测

`yolo_detect.py`：

```python
#!/usr/bin/env python3
"""04-1 YOLO: 本地图片目标检测

读取图片 → YOLOv8n 推理 → 打印每个检测框（类别/置信度/坐标）→ 显示标注图。
"""
import sys
import os
import cv2
from ament_index_python.packages import get_package_share_directory
from ultralytics import YOLO

# ── 加载模型 ──
MODEL = os.path.join(
    get_package_share_directory('vision_basics'), 'model', 'yolov8n.pt')
model = YOLO(MODEL)
print(f'模型: {MODEL}')

# ── 读取图片 ──
base = os.path.dirname(os.path.abspath(__file__))
img_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(base, '..', 'pictures', 'lena.png')
img = cv2.imread(img_path)
print(f'图片: {os.path.basename(img_path)} ({img.shape[1]}×{img.shape[0]})')

# ── 推理 ──
results = model(img, conf=0.25, verbose=False)
r = results[0]

# ── 打印每个检测框 ──
boxes = r.boxes
if boxes is not None and len(boxes) > 0:
    print(f'\n检测到 {len(boxes)} 个目标:')
    names = r.names
    for i in range(len(boxes)):
        cls_id = int(boxes.cls[i])
        conf = float(boxes.conf[i])
        xywh = boxes.xywh[i]
        print(f'  {names[cls_id]:<12} conf={conf:.2f}  '
              f'center=({int(xywh[0])},{int(xywh[1])})  '
              f'size={int(xywh[2])}×{int(xywh[3])}')
else:
    print('未检测到目标')

# ── 显示 ──
annotated = r.plot()
cv2.imshow('YOLOv8 Detection', annotated)
print('\n按任意键关闭窗口')
cv2.waitKey(0)
cv2.destroyAllWindows()
```

### 运行

```bash
cd ~/Music/spark_humble && source install/setup.bash
export DISPLAY=:0
python3.10 src/ros2_vision/vision_basics/vision_basics/yolo_detect.py

# 自定义图片
python3.10 src/ros2_vision/vision_basics/vision_basics/yolo_detect.py ~/Pictures/cat.jpg
```

### 预期输出

```
模型: .../install/vision_basics/share/vision_basics/model/yolov8n.pt
图片: lena.png (516×514)

检测到 2 个目标:
  person       conf=0.85  center=(312,360)  size=200×300
  tv           conf=0.72  center=(400,280)  size=80×60
```

---

## 程序 2：模型目录管理

`yolo_model_info.py` 🔴（参考版没有）：

```python
#!/usr/bin/env python3
"""04-1 模型目录扫描

列出 vision_basics/model/ 下所有 .pt 文件，显示:
  文件大小、模型任务类型、参数数量
帮助学生建立模型管理意识——「我有哪些模型？每个多大？干什么用的？」
"""
import os
from ament_index_python.packages import get_package_share_directory
from ultralytics import YOLO

MODEL_DIR = os.path.join(get_package_share_directory('vision_basics'), 'model')

print(f'模型目录: {MODEL_DIR}')
print(f'{"="*70}')

if not os.path.isdir(MODEL_DIR):
    print('模型目录不存在，请先下载模型并 colcon build')
    exit(1)

models = sorted([f for f in os.listdir(MODEL_DIR) if f.endswith('.pt')])

total_mb = 0.0
for name in models:
    path = os.path.join(MODEL_DIR, name)
    size_mb = os.path.getsize(path) / 1e6
    total_mb += size_mb

    # 快速加载获取任务类型（不跑推理）
    try:
        m = YOLO(path)
        task = m.task
    except Exception:
        task = '?'

    print(f'  {name:<25s}  {size_mb:6.1f}MB  task={task}')

print(f'{"-"*70}')
print(f'总计: {total_mb:.1f} MB')

print('\n💡 要下载新模型（如 YOLO11n）：')
print('   from ultralytics import YOLO; YOLO("yolo11n.pt")  # 自动下载')
```

### 运行

```bash
python3.10 src/ros2_vision/vision_basics/vision_basics/yolo_model_info.py
```

### 预期输出

```
模型目录: .../model
======================================================================
  rtdetr-l.pt                128.3MB  task=detect
  yolov8n-pose.pt              6.6MB  task=pose
  yolov8n-seg.pt               6.8MB  task=segment
  yolov8n.pt                   6.3MB  task=detect
  yolov8s-world.pt            26.0MB  task=detect
  yolov8s.pt                  22.0MB  task=detect
----------------------------------------------------------------------
总计: 196.0 MB
```

---

# 第 8 章：视频 — 摄像头实时检测

`yolo_video.py` 接受命令行参数：视频文件路径或摄像头编号（默认 `/dev/video0`），逐帧推理 + FPS 叠加。

```python
#!/usr/bin/env python3
"""04-1 YOLO: 摄像头/视频实时目标检测

打开摄像头(默认 /dev/video0) → YOLOv8n 逐帧推理 → 显示 FPS + 检测框。
第一个参数可传视频文件路径。按 q 退出。
"""
import sys
import os
import cv2
from ament_index_python.packages import get_package_share_directory
from ultralytics import YOLO

MODEL = os.path.join(
    get_package_share_directory('vision_basics'), 'model', 'yolov8n.pt')

video_src = sys.argv[1] if len(sys.argv) > 1 else 0
cap = cv2.VideoCapture(video_src)
if not cap.isOpened():
    print(f'无法打开视频源: {video_src}')
    exit(1)

model = YOLO(MODEL)
print(f'模型: {MODEL} | 视频源: {video_src} | 按 q 退出')

cv2.namedWindow('YOLOv8 Video', cv2.WINDOW_NORMAL)
cv2.resizeWindow('YOLOv8 Video', 800, 600)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, conf=0.3, verbose=False)
    annotated = results[0].plot()

    fps = 1000.0 / results[0].speed['inference'] if results[0].speed else 0
    cv2.putText(annotated, f'FPS: {int(fps)}', (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    cv2.imshow('YOLOv8 Video', annotated)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

### 运行

```bash
# USB 摄像头
python3.10 src/ros2_vision/vision_basics/vision_basics/yolo_video.py

# 视频文件
python3.10 src/ros2_vision/vision_basics/vision_basics/yolo_video.py ~/Videos/test.mp4
```

---

# 第 9 章：ROS2 实时 — Spark D435

`ros2_yolo.py` 订阅 D435 彩色图像话题，逐帧推理并显示。这是学生第一次把深度学习跑在真实机器人相机上。

```python
#!/usr/bin/env python3
"""04-1 YOLO: ROS2 相机实时目标检测

订阅 D435 彩色图像 → YOLOv8n 推理 → 绘制检测框+FPS → 显示。
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import os
from ament_index_python.packages import get_package_share_directory
from ultralytics import YOLO

MODEL = os.path.join(
    get_package_share_directory('vision_basics'), 'model', 'yolov8n.pt')


class YoloNode(Node):
    def __init__(self):
        super().__init__('yolo_node')
        self.bridge = CvBridge()
        self.model = YOLO(MODEL)
        self.conf = 0.3

        self.sub = self.create_subscription(
            Image, '/camera/camera/color/image_raw', self.callback, 10)
        self.get_logger().info(f'YOLOv8n 已加载 | 等待相机帧')

    def callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

        results = self.model(frame, conf=self.conf, verbose=False)
        annotated = results[0].plot()

        speed = results[0].speed
        if speed and 'inference' in speed:
            fps = 1000.0 / speed['inference']
            cv2.putText(annotated, f'FPS: {int(fps)}', (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow('YOLOv8 Camera', annotated)
        cv2.waitKey(1)


def main():
    rclpy.init()
    node = YoloNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
```

### 运行

```bash
# 终端 1：启动相机
ros2 launch spark_bringup d435.launch.py

# 终端 2：启动检测
cd ~/Music/spark_humble && source install/setup.bash
export DISPLAY=:0
ros2 run vision_basics ros2_yolo
```

---

# ⚠️ 常见坑

🕳️ **模型下载失败（GFW）**
- 最常见的问题。GitHub 上的 .pt 文件在国内网络下可能无法访问。
- 解决：用科学上网下载，或从同学的 U 盘拷贝到 `vision_basics/model/`。

🕳️ **`No module named 'cv2'`**
- 用了 Hermes 的 `python3` 而不是系统的 `python3.10`。
- 始终用 `python3.10` 运行程序。

🕳️ **模型找不到：`FileNotFoundError: yolov8n.pt`**
- 还没 `colcon build`，模型文件没复制到 `install/` 目录。
- 先下载模型到 `src/.../model/`，再 `colcon build`。

🕳️ **D435 无图像**
- `ros2 topic list | grep color/image_raw` 检查话题是否存在。
- 没有？先启动相机 `ros2 launch spark_bringup d435.launch.py`。

🕳️ **窗口不显示（SSH）**
- `export DISPLAY=:0` 指向 Spark 的桌面会话。
