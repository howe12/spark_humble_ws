# Spark实践版 — 04-5 RT-DETR 实时 Transformer 检测

> 基于 Spark `vision_basics` 包，`rtdetr-l.pt` 模型（~128MB）。
> 参考版共 7 章，涵盖 DETR 原理→RT-DETR 实战→YOLO 对比→混合项目。
> 实践版聚焦 **3 个可运行程序** + **RT-DETR vs YOLO 并排对比实验**——这是理解「CNN vs Transformer 检测器」最直观的方式。

---

## 📦 环境准备

### 1. 安装 ultralytics

```bash
pip install ultralytics
# 验证
python3.10 -c "from ultralytics import YOLO; print('OK')"
# → OK
```

> ⚠️ 注意：Hermes 的虚拟环境 `python3` 不带 opencv，用系统的 `python3.10`。

### 2. 确认 OpenCV 可用

```bash
python3.10 -c "import cv2; print(cv2.__version__)"
# → 4.9.0（或类似版本号）
```

如果报 `ModuleNotFoundError`：
```bash
pip install opencv-python
```

### 3. 确认 ROS2 环境（ROS2 节点必需）

```bash
# cv_bridge 用于 ROS 图像消息 ↔ OpenCV 格式转换
sudo apt install ros-humble-cv-bridge
# ament_index 用于查找包内文件路径
sudo apt install ros-humble-ament-index-python
```

### 4. 下载 RT-DETR 模型

`rtdetr-l.pt` 约 128MB，不在 Git 仓库中。

```bash
# 方式 1：Python 自动下载（需科学上网）
cd ~/Music/spark_humble/src/ros2_vision/vision_basics/model/
python3.10 -c "from ultralytics import YOLO; YOLO('rtdetr-l.pt')"

# 方式 2：wget 手动下载（同样需科学上网）
wget https://github.com/ultralytics/assets/releases/download/v8.2.0/rtdetr-l.pt

# 方式 3：从其他机器 scp 过来
scp user@other-machine:/path/to/rtdetr-l.pt .

# 验证
ls -lh rtdetr-l.pt          # 应显示 ~128MB
python3.10 -c "from ultralytics import YOLO; m=YOLO('rtdetr-l.pt'); print(m.task)"
# → detect
```

### 5. 编译 vision_basics 包

```bash
cd ~/Music/spark_humble
source /opt/ros/humble/setup.bash
colcon build --packages-select vision_basics
source install/setup.bash
```

### 6. 确认模型可被程序找到

```bash
python3.10 -c "
from ament_index_python.packages import get_package_share_directory
import os
path = os.path.join(get_package_share_directory('vision_basics'), 'model', 'rtdetr-l.pt')
print('模型路径:', path)
print('文件存在:', os.path.exists(path))
"
# → 模型路径: .../install/vision_basics/share/vision_basics/model/rtdetr-l.pt
# → 文件存在: True
```

> 💡 步骤 4~6 也适用于其他模型（yolov8n.pt / sam_b.pt 等），流程完全一致：下载 → 放 model/ → colcon build。

### 7. 确认 ROS2 可用（ROS2 节点）

```bash
# 检查 ROS2 环境
source /opt/ros/humble/setup.bash
ros2 --version
# → humble

# 确认 vision_basics 包的 ROS2 入口
source ~/Music/spark_humble/install/setup.bash
ros2 run vision_basics ros2_rtdetr --help 2>&1 | head -3
# 应该启动节点（没有相机时会等待，Ctrl+C 退出即可）
```

---

## 参考版结构 & 实践版插入点

参考版 7 章，实践版聚焦第 4/5/6 章实战部分：

### 第 1~2 章 — DETR 原理
参考版内容：Transformer 检测器起源、Encoder-Decoder、Object Query、二分图匹配。
实践版：**保留理论**，不另写。

### 第 3 章 — RT-DETR 关键创新
参考版内容：RT-DETR 如何解决 DETR 收敛慢的问题（Hybrid Encoder、IoU-aware Query Selection）。
实践版：**保留理论**，实践版补充「统一 API」的实操演示。

### 第 4 章 — RT-DETR 本地检测
参考版内容：Python 加载 rtdetr-l.pt 对图片推理。
实践版插入：
- `rtdetr_detect.py` → 替换「4.3 完整代码」— 本地图片 + 模型路径管理 + 推理时间统计

### 第 5 章 — RT-DETR vs YOLO 对比
参考版内容：理论对比表格。
实践版插入：
- `rtdetr_vs_yolo.py` 🔴 → 替换「5.2 对比实验」— **并排对比图**：同一张图上左 RT-DETR / 右 YOLOv8，含检测框数、推理时间、模型大小

### 第 6 章 — 机器人场景混合检测
参考版内容：YOLO+RT-DETR 混合方案构思。
实践版插入：
- `ros2_rtdetr.py` 🔴 → ROS2 D435 实时 RT-DETR 检测，证明 `ros2_yolo.py` 改一行模型路径就能跑 RT-DETR

---

## 参考版关键问题

- **模型加载不靠谱**：参考版用 `YOLO('rtdetr-l.pt')` 依赖自动下载（~128MB，GFW 下必失败）。实践版用 `get_package_share_directory('vision_basics')` 本地加载。
- **路径写死 leo**：所有代码路径引用 `leo_agv`、`leo_yolov8_class`。
- **ROS2 节点话题错误**：参考版订阅 `/camera/color/image_raw`，实践版改为 Spark D435 的 `/camera/camera/color/image_raw`。
- **对比实验缺可视化**：参考版只有理论表格，实践版 `rtdetr_vs_yolo.py` 输出**并排标注图**让差异一目了然。
- **rtdetr-l.pt 模型大**：~128MB，.gitignore 排除，需单独下载。这也是「模型下载教程」要覆盖的场景。

---

## 核心卖点：统一 API

RT-DETR 和 YOLO 在 ultralytics 中使用**完全相同的 API**：

```python
# YOLO 检测
model = YOLO('yolov8n.pt')
results = model('image.jpg')

# RT-DETR 检测 — 唯一区别是模型文件名
model = YOLO('rtdetr-l.pt')  # 或用 RTDETR('rtdetr-l.pt')
results = model('image.jpg')
```

这意味着**一行代码就能切换检测器**。`ros2_yolo.py` 和 `ros2_rtdetr.py` 的 diff 只有模型路径——实践版刻意保持两个 ROS2 节点代码结构一致，让学生直观理解统一 API 的价值。

---

## 程序清单

### 本地程序

- `rtdetr_detect.py` — 本地图片 RT-DETR 检测 + 推理时间
- `rtdetr_vs_yolo.py` 🔴 — RT-DETR vs YOLOv8 并排对比

### ROS2 相机程序

- `ros2_rtdetr.py` 🔴 — D435 实时 RT-DETR 检测

所有程序在 `vision_basics/vision_basics/` 下。

---

# 第 4 章：本地图片 — RT-DETR 初体验

## 完整代码

`rtdetr_detect.py`：

```python
#!/usr/bin/env python3
"""
RT-DETR 实时 Transformer 目标检测

RT-DETR 是百度提出的实时端到端 Transformer 检测器，直接通过 YOLO() 加载。
与 YOLOv8 的 API 完全一致——唯一区别是模型名。

用法：
    python3 rtdetr_detect.py              # 用 lena.png
    python3 rtdetr_detect.py image.jpg    # 自定义图片

模型：rtdetr-l.pt（首次运行自动下载，约 128MB）
"""

import os, sys, time
from ament_index_python.packages import get_package_share_directory
import cv2
from ultralytics import YOLO

MODEL_DIR = os.path.join(get_package_share_directory('vision_basics'), 'model')
_base = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.join(_base, '..')


def get_model(name):
    local = os.path.join(MODEL_DIR, name)
    return local if os.path.exists(local) else name


def main():
    # MODEL 可与 YOLO 互换：YOLO('rtdetr-l.pt') 和 RTDETR('rtdetr-l.pt') 等效
    model_path = get_model('rtdetr-l.pt')
    print(f'模型: {model_path}')
    model = YOLO(model_path)
    print(f'任务: {model.task}')

    img_path = sys.argv[1] if len(sys.argv) > 1 else f'{PROJ_DIR}/pictures/lena.png'
    img = cv2.imread(img_path)
    print(f'图片: {os.path.basename(img_path)} ({img.shape[1]}×{img.shape[0]})')

    # 推理
    t0 = time.time()
    results = model(img, conf=0.25, verbose=False)
    ms = (time.time() - t0) * 1000

    r = results[0]
    n = len(r.boxes) if r.boxes is not None else 0
    print(f'检测: {n} 个目标, 推理 {ms:.0f}ms')

    annotated = r.plot()
    cv2.imshow('RT-DETR — 按任意键退出', annotated)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
```

## 运行

```bash
cd ~/Music/spark_humble && source install/setup.bash
export DISPLAY=:0
python3.10 src/ros2_vision/vision_basics/vision_basics/rtdetr_detect.py

# 自定义图片
python3.10 src/ros2_vision/vision_basics/vision_basics/rtdetr_detect.py ~/Pictures/photo.jpg
```

---

# 第 5 章：并排对比 — RT-DETR vs YOLOv8

> 这是实践版的核心章节——用真实代码验证参考版的理论对比表。
> 同一张图、同一阈值、同样的 ultralytics API，唯一的变量是**模型文件**。

## 完整代码

`rtdetr_vs_yolo.py`：

```python
#!/usr/bin/env python3
"""
RT-DETR vs YOLOv8 横向对比

同一张图上运行 RT-DETR 和 YOLOv8，对比：
  - 检测框数 + 类别分布
  - 推理时间（ms）
  - 模型大小（MB）
  - 并排标注图（左 RT-DETR / 右 YOLOv8）

用法：
    python3 rtdetr_vs_yolo.py               # lena.png
    python3 rtdetr_vs_yolo.py scene.jpg     # 自定义
"""

import os, sys, time
from ament_index_python.packages import get_package_share_directory
import cv2
import numpy as np
from ultralytics import YOLO

MODEL_DIR = os.path.join(get_package_share_directory('vision_basics'), 'model')
_base = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.join(_base, '..')


def get_model(name):
    local = os.path.join(MODEL_DIR, name)
    return local if os.path.exists(local) else name


def run_one(model_path, label, img):
    t0 = time.time()
    try:
        m = YOLO(model_path)
        # 预热
        _ = m(img, verbose=False)
        t1 = time.time()
        r = m(img, conf=0.25, verbose=False)
        t2 = time.time()
    except Exception as e:
        return None, str(e)[:60], 0, 0

    n = len(r[0].boxes) if r[0].boxes is not None else 0
    annotated = r[0].plot()
    size_mb = os.path.getsize(model_path) / 1e6 if os.path.exists(model_path) else 0
    infer_ms = (t2 - t1) * 1000
    return annotated, f'{n} 框', size_mb, infer_ms


def main():
    img_path = sys.argv[1] if len(sys.argv) > 1 else f'{PROJ_DIR}/pictures/lena.png'
    img = cv2.imread(img_path)
    print(f'图片: {os.path.basename(img_path)} ({img.shape[1]}×{img.shape[0]})')

    # ── RT-DETR ──
    rtdetr_path = get_model('rtdetr-l.pt')
    print(f'\nRT-DETR: {rtdetr_path}', end=' ')
    rt_annotated, rt_info, rt_size, rt_ms = run_one(rtdetr_path, 'RT-DETR', img)
    print(f'→ {rt_info}, {rt_ms:.0f}ms, {rt_size:.1f}MB')

    # ── YOLOv8 ──
    yolo_path = get_model('yolov8n.pt')
    print(f'YOLOv8n: {yolo_path}', end=' ')
    yolo_annotated, yolo_info, yolo_size, yolo_ms = run_one(yolo_path, 'YOLOv8n', img)
    print(f'→ {yolo_info}, {yolo_ms:.0f}ms, {yolo_size:.1f}MB')

    # ── 并排显示 ──
    h, w = img.shape[:2]
    side_by_side = np.hstack([rt_annotated, yolo_annotated])
    cv2.putText(side_by_side, f'RT-DETR: {rt_info} {rt_ms:.0f}ms {rt_size:.1f}MB',
                (10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    cv2.putText(side_by_side, f'YOLOv8n: {yolo_info} {yolo_ms:.0f}ms {yolo_size:.1f}MB',
                (w+10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    # 中间分割线
    cv2.line(side_by_side, (w, 0), (w, h), (0, 0, 255), 2)

    cv2.imshow('RT-DETR (左) vs YOLOv8n (右) — 按任意键退出', side_by_side)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
```

## 运行

```bash
cd ~/Music/spark_humble && source install/setup.bash
export DISPLAY=:0
python3.10 src/ros2_vision/vision_basics/vision_basics/rtdetr_vs_yolo.py
```

## 预期输出

```
图片: lena.png (516×514)

RT-DETR: .../model/rtdetr-l.pt → 3 框, 85ms, 128.3MB
YOLOv8n: .../model/yolov8n.pt → 2 框, 12ms, 6.3MB
```

> 典型对比：RT-DETR 更重（128MB vs 6.3MB）但检得更全（3 框 vs 2 框），Transformer 对小目标的 recall 更强。

---

# 第 6 章：ROS2 实时 — Spark D435 + RT-DETR

## 完整代码

`ros2_rtdetr.py`：

```python
#!/usr/bin/env python3
"""
ROS2 RT-DETR 实时检测节点

与 ros2_yolo.py 结构完全一致，唯一区别：模型用 rtdetr-l.pt。
证明 ultralytics 统一 API：YOLO 和 RT-DETR 节点代码可互换。
"""

import time
import os
import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from ament_index_python.packages import get_package_share_directory
from ultralytics import YOLO

MODEL = os.path.join(
    get_package_share_directory('vision_basics'), 'model', 'rtdetr-l.pt')


class RTDETRNode(Node):
    def __init__(self):
        super().__init__('rtdetr_node')
        self.get_logger().info('启动 RT-DETR 检测节点...')

        self.bridge = CvBridge()
        self.model = YOLO(MODEL)  # 可用 RTDETR() 或 YOLO()

        self.image_sub = self.create_subscription(
            Image, '/camera/camera/color/image_raw', self.image_callback, 10)

        self.last_fps_time = time.time()
        self.frame_count = 0
        self.fps_value = 0.0
        self.get_logger().info(f'模型加载完成，等待图像...')

    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        results = self.model(frame, conf=0.25, verbose=False)
        annotated = results[0].plot()

        self.frame_count += 1
        now = time.time()
        elapsed = now - self.last_fps_time
        if elapsed >= 1.0:
            self.fps_value = self.frame_count / elapsed
            self.frame_count = 0
            self.last_fps_time = now
            self.get_logger().info(f'FPS: {self.fps_value:.1f}')

        cv2.putText(annotated, f'RT-DETR FPS: {self.fps_value:.1f}',
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow('RT-DETR — ROS2 实时', annotated)
        cv2.waitKey(1)

    def destroy(self):
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = RTDETRNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('收到中断信号...')
    finally:
        node.destroy()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
```

## 运行

```bash
# 终端 1：启动 D435 相机
ros2 launch spark_bringup d435.launch.py

# 终端 2：启动 RT-DETR 节点
cd ~/Music/spark_humble && source install/setup.bash
export DISPLAY=:0
ros2 run vision_basics ros2_rtdetr
```

## 统一 API 证明

对比 `ros2_yolo.py` 和 `ros2_rtdetr.py` 的 diff：

```diff
- MODEL = os.path.join(..., 'model', 'yolov8n.pt')
+ MODEL = os.path.join(..., 'model', 'rtdetr-l.pt')

- super().__init__('yolo_node')
+ super().__init__('rtdetr_node')

- self.get_logger().info(f'YOLOv8n 已加载 | 等待 D435 相机帧')
+ self.get_logger().info(f'模型加载完成，等待图像...')
```

**只改了 3 行！** 这就是 ultralytics 统一 API 的力量——换模型只需换文件路径，代码逻辑零改动。

---

# ⚠️ 常见坑

🕳️ **rtdetr-l.pt 下载失败（GFW）**
- 这是最常见的问题。128MB 的模型文件在 GFW 下几乎必定中断。
- 解决：在其他网络环境下载后 scp 到 Spark 机器，或使用代理。

🕳️ **RT-DETR 在 CPU 上很慢**
- rtdetr-l.pt 有 26.4M 参数，CPU 推理约 80-150ms/帧（6~12 FPS）。
- YOLOv8n 只有 3.3M 参数，CPU 推理约 12ms/帧（80+ FPS）。
- 这是 Transformer vs CNN 的典型权衡：精度更高，但速度更慢。

🕳️ **ros2_rtdetr.py 和 ros2_yolo.py 几乎一样，是不是多余的？**
- 不是！这两个文件的**相似性本身就是教学内容**——证明 ultralytics 统一 API 的存在。
- 学生可以直观理解：「换模型 = 换一行路径」，不需要学新框架。
