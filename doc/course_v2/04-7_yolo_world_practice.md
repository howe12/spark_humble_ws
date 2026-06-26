# Spark实践版 — 04-7 YOLO-World 开放词汇检测

> 基于 Spark `vision_basics` 包，`yolov8s-world.pt` 模型（26MB）。
> 参考版 7 章涵盖 OWL-ViT→YOLO-World→Grounding DINO→选型决策。
> 实践版聚焦 **YOLO-World 实战** + **ROS2 动态类别切换**——这是「从固定类别到开放词汇」的关键一步。

---

## 📦 环境准备

> 如果你已完成 04-1 的环境配置，只需确认模型存在即可。

### 1. 基础环境（已完成则跳过）

```bash
pip install ultralytics
python3.10 -c "import cv2; print(cv2.__version__)"
sudo apt install ros-humble-cv-bridge ros-humble-ament-index-python
```

### 2. 模型下载

```bash
cd ~/Music/spark_humble/src/ros2_vision/vision_basics/model/

# 方式 1：Python 自动下载
python3.10 -c "from ultralytics import YOLOWorld; YOLOWorld('yolov8s-world.pt')"

# 方式 2：wget
wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8s-world.pt

# 验证
ls -lh yolov8s-world.pt     # → 26MB
python3.10 -c "from ultralytics import YOLOWorld; m=YOLOWorld('yolov8s-world.pt'); print(m.task)"
# → detect
```

### 3. 编译

```bash
cd ~/Music/spark_humble && source /opt/ros/humble/setup.bash
colcon build --packages-select vision_basics && source install/setup.bash
```

---

## 参考版结构 & 实践版插入点

参考版 7 章。实践版聚焦第 3 章 YOLO-World 实战：

### 第 1~2 章 — 开放词汇概念 / OWL-ViT 原理
参考版内容：传统检测 vs 开放词汇的范式对比、CLIP 文本编码器、OWL-ViT 架构。
实践版：**保留理论**，不另写。

### 第 3 章 — YOLO-World 实战
参考版内容：YOLO-World Python API、`set_classes()` 方法。
实践版插入：
- `yolo_world_detect.py` → 替换「3.3 Python 接口」— 本地图片 + 命令行指定类别
- `ros2_yolo_world.py` 🔴 → **运行时动态切换类别**（ROS2 参数热更新，无需重启节点）

### 第 4~7 章 — Grounding DINO / 选型 / 综合项目 / 生态
实践版：保留参考版理论。Grounding DINO 需要额外模型（~700MB），不在实践版范围。

---

## 参考版关键问题

- **模型加载不靠谱**：参考版用 `YOLOWorld('yolov8s-world.pt')` 依赖自动下载。实践版改为 `get_package_share_directory('vision_basics')`。
- **ROS2 节点无动态切换**：参考版 ROS2 节点写死类别。实践版 `ros2_yolo_world.py` 通过 ROS2 **参数热更新**，运行时无需重启即可切换类别——这是开放词汇检测最酷的特性。
- **路径写死 leo**：所有代码路径引用 `leo_agv`。
- **话题错误**：参考版订阅 `/camera/color/image_raw`，实践版改为 D435 的 `/camera/camera/color/image_raw`。
- **需要 CLIP 依赖**：YOLO-World 底层依赖 CLIP 文本编码器，`pip install ultralytics` 会自动安装。GFW 下可能失败——如果 `import YOLOWorld` 报 CLIP 错误，参考常见坑。

---

## 核心卖点：一句话就能切换检测目标

传统 YOLO 检测什么类别是**训练时就定死的**（80 类 COCO）。YOLO-World 不同——它把**文字描述**编码进模型，可以检测训练时没见过的类别。

```python
from ultralytics import YOLOWorld

model = YOLOWorld('yolov8s-world.pt')

# 检测标准 COCO 类别
model.set_classes(['person', 'car', 'dog'])

# 检测自定义类别——训练时没见过「red cup」！
model.set_classes(['red cup', 'black headphones', 'white sneaker'])

# 运行时动态切换——这个 ROS2 节点实现了！
```

---

## 程序清单

- `yolo_world_detect.py` — 本地图片 + 命令行指定类别
- `ros2_yolo_world.py` 🔴 — **ROS2 动态类别切换**（参数热更新，无需重启）

所有程序在 `vision_basics/vision_basics/` 下。

---

# 程序 1：本地图片 — 命令行指定类别

`yolo_world_detect.py` 通过 `set_classes()` 方法指定想检测的物体名（支持任意英文词汇）。

```python
#!/usr/bin/env python3
"""
YOLO-World 开放词汇目标检测

最大的不同：不用重新训练，只需告诉模型"我要找什么"。
set_classes(['person', 'red cup', 'laptop']) → 只检测这些类别。

用法：
    python3 yolo_world_detect.py                      # lena.png, 默认类别
    python3 yolo_world_detect.py "red cup,laptop"     # 自定义类别
    python3 yolo_world_detect.py "dog,cat" image.jpg  # 自定义+图片

模型：yolov8s-world.pt（约 26MB）
"""

import os, sys
from ament_index_python.packages import get_package_share_directory
import cv2
from ultralytics import YOLOWorld

MODEL_DIR = os.path.join(get_package_share_directory('vision_basics'), 'model')
_base = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.join(_base, '..')


def get_model(name):
    local = os.path.join(MODEL_DIR, name)
    return local if os.path.exists(local) else name


def main():
    model_path = get_model('yolov8s-world.pt')
    print(f'模型: {model_path}')
    model = YOLOWorld(model_path)
    print(f'任务: {model.task}')

    # ── 解析参数 ──
    args = sys.argv[1:]
    custom_classes = None
    img_arg = None

    for a in args:
        if ',' in a and not a.endswith(('.jpg', '.png', '.jpeg')):
            custom_classes = [c.strip() for c in a.split(',')]
        elif a.endswith(('.jpg', '.png', '.jpeg')):
            img_arg = a

    if custom_classes:
        model.set_classes(custom_classes)
        print(f'检测类别: {custom_classes}')
    else:
        print('检测类别: COCO 默认 80 类')

    img_path = img_arg or f'{PROJ_DIR}/pictures/lena.png'
    img = cv2.imread(img_path)
    print(f'图片: {os.path.basename(img_path)} ({img.shape[1]}×{img.shape[0]})')

    results = model(img, conf=0.3, verbose=False)
    r = results[0]
    n = len(r.boxes) if r.boxes is not None else 0
    print(f'检测: {n} 个目标')

    annotated = r.plot()
    cv2.imshow('YOLO-World — 按任意键退出', annotated)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
```

### 运行

```bash
cd ~/Music/spark_humble && source install/setup.bash
export DISPLAY=:0

# 默认 COCO 类别
python3.10 src/ros2_vision/vision_basics/vision_basics/yolo_world_detect.py

# 自定义类别：只检测人和笔记本
python3.10 src/ros2_vision/vision_basics/vision_basics/yolo_world_detect.py "person,laptop"

# 自定义类别 + 自定义图片
python3.10 src/.../yolo_world_detect.py "red cup,white chair" ~/Pictures/office.jpg
```

---

# 程序 2：ROS2 动态类别切换 🔴

`ros2_yolo_world.py` 是本课程最独特的 ROS2 节点——**不重启节点就能切换检测类别**。

```bash
# 启动节点（默认检测 person,cup,bottle,laptop,chair）
ros2 run vision_basics ros2_yolo_world

# 运行时动态切换！无需 Ctrl+C 重启
ros2 param set /yolo_world_node classes "person,dog,cat"
# → 终端输出：[INFO] 检测类别: ['person', 'dog', 'cat']

# 再切一次
ros2 param set /yolo_world_node classes "red cup,black phone,white sneaker"
# → 立即生效！
```

```python
#!/usr/bin/env python3
"""
ROS2 YOLO-World 开放词汇检测节点

运行时可通过参数动态切换检测类别——无需重启节点。

默认检测: person, cup, bottle, laptop, chair
自定义: ros2 run vision_basics ros2_yolo_world --ros-args -p classes:="person,dog,cat"
"""

import time
import os
import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from ament_index_python.packages import get_package_share_directory
from ultralytics import YOLOWorld

MODEL = os.path.join(
    get_package_share_directory('vision_basics'), 'model', 'yolov8s-world.pt')


class YOLOWorldNode(Node):
    def __init__(self):
        super().__init__('yolo_world_node')

        self.declare_parameter('classes', 'person,cup,bottle,laptop,chair')
        self.declare_parameter('conf', 0.3)

        self.bridge = CvBridge()
        self.model = YOLOWorld(MODEL)
        self._update_classes()

        # 参数变更回调（运行时动态切换的魔法所在！）
        self.add_on_set_parameters_callback(self._on_param_change)

        self.image_sub = self.create_subscription(
            Image, '/camera/camera/color/image_raw', self.image_callback, 10)

        self.last_fps_time = time.time()
        self.frame_count = 0
        self.fps_value = 0.0
        self.get_logger().info('YOLO-World 节点启动，支持动态类别切换')

    def _update_classes(self):
        classes_str = self.get_parameter('classes').value
        classes = [c.strip() for c in classes_str.split(',') if c.strip()]
        self.model.set_classes(classes)
        self.get_logger().info(f'检测类别: {classes}')

    def _on_param_change(self, params):
        for p in params:
            if p.name == 'classes':
                self._update_classes()
        return rclpy.parameter.SetParametersResult(successful=True)

    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        conf = self.get_parameter('conf').value
        results = self.model(frame, conf=conf, verbose=False)
        annotated = results[0].plot()

        self.frame_count += 1
        now = time.time()
        elapsed = now - self.last_fps_time
        if elapsed >= 1.0:
            self.fps_value = self.frame_count / elapsed
            self.frame_count = 0
            self.last_fps_time = now

        cv2.putText(annotated, f'YOLO-World FPS: {self.fps_value:.1f}',
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow('YOLO-World — ROS2 动态类别', annotated)
        cv2.waitKey(1)

    def destroy(self):
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = YOLOWorldNode()
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

### 运行

```bash
# 终端 1：启动 D435
ros2 launch spark_bringup d435.launch.py

# 终端 2：启动 YOLO-World
cd ~/Music/spark_humble && source install/setup.bash
export DISPLAY=:0
ros2 run vision_basics ros2_yolo_world

# 终端 3：动态切换！不用重启节点
ros2 param set /yolo_world_node classes "person,dog"
ros2 param set /yolo_world_node classes "laptop,cell phone,book"
ros2 param set /yolo_world_node classes "red cup,white chair,black bag"
```

### 动态切换的原理

```python
# 关键三步：
# 1. declare_parameter('classes', ...)     — 声明可调参数
# 2. add_on_set_parameters_callback(...)   — 注册参数变更回调
# 3. model.set_classes(new_list)           — 模型内部更新文本嵌入

# 效果：无需重新加载模型、无需重启节点、无需重新订阅话题
# 唯一代价：set_classes() 需要 0.5~1 秒（重新编码文本）
```

---

# ⚠️ 常见坑

🕳️ **`import YOLOWorld` 报 CLIP 错误**
- YOLO-World 依赖 CLIP（OpenAI 的文本-图像对齐模型）。
- GFW 下 `pip install ultralytics` 时 CLIP 可能下载失败。
- 解决：`pip install git+https://github.com/openai/CLIP.git`（可能也需要科学上网），或使用预装了 CLIP 的环境。

🕳️ **`set_classes(['red cup'])` 不检测 red cup**
- YOLO-World 的开放词汇能力**不是无限的**。它只对训练数据中见过的概念有效。
- 「red cup」= 颜色 + 物体，YOLO-World 可能只识别「cup」而忽略「red」。
- 这是正常的——YOLO-World 不是真正的 VLM，只是「比 COCO 更灵活」。

🕳️ **动态切换不是即时生效**
- `set_classes()` 需要重新编码文本（CLIP），耗时 0.5~1 秒。
- 切换期间会丢 1~2 帧。

🕳️ **话题无数据**
- 确保 D435 相机已启动：`ros2 topic list | grep color/image_raw`
