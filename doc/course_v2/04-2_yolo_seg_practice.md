# Spark实践版 — 04-2 YOLO实例分割

适配说明：`leo_vision` → `vision_basics`，代码路径 `src/ros2_vision/vision_basics/`
参考文档 token：`M9ZUd8Ixiou3jvxuQXgcYJxcnDe`

---

## 📦 环境准备

1. **安装 ultralytics**
   ```bash
   pip3 install ultralytics
   python3.10 -c "from ultralytics import YOLO; print('OK')"
   ```

2. **确认 OpenCV**
   ```bash
   python3.10 -c "import cv2; print(cv2.__version__)"
   ```

3. **确认 ROS2 环境**
   ```bash
   sudo apt install ros-humble-cv-bridge ros-humble-ament-index-python
   ```

4. **下载模型**（`yolov8n-seg.pt`，6.8MB）
   ```bash
   # 方式 A：ultralytics 自动（需网络）
   yolo predict model=yolov8n-seg.pt
   # 方式 B：wget 直接下载
   wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n-seg.pt \
     -O src/ros2_vision/vision_basics/model/yolov8n-seg.pt
   # 方式 C：从其他机器 scp 过来
   # 验证
   python3.10 -c "from ultralytics import YOLO; YOLO('src/ros2_vision/vision_basics/model/yolov8n-seg.pt')"
   ```

5. **编译 vision_basics**
   ```bash
   cd /home/spark/Music/spark_humble
   colcon build --packages-select vision_basics
   ```

6. **确认模型路径**
   ```bash
   source install/setup.bash
   python3.10 -c "
   from ament_index_python import get_package_share_directory
   import os
   print(os.path.join(get_package_share_directory('vision_basics'), 'model', 'yolov8n-seg.pt'))
   "
   ```

7. **ROS2 冒烟测试**
   ```bash
   ros2 run vision_basics ros2_yolo_seg
   # 预期：终端打印 "YOLOv8n-seg 已加载 | 等待相机帧"，无崩溃即通过
   Ctrl+C 退出
   ```

---

## 参考版结构 & 实践版插入点

参考版共 7 章。以下是每章对应的实践内容及插入位置：

### 第 1 章 — 实例分割入门
参考版内容：概念、目标检测/语义分割/实例分割三大任务对比、典型应用。
实践版插入：无（纯理论，参考版已覆盖充分）

### 第 2 章 — 实例分割算法演进
参考版内容：Mask R-CNN → YOLACT → YOLOv5-seg → YOLOv8-seg → SAM 时间线。
**重点澄清**：原文档将 YOLACT 介绍为 YOLOv8 基础，实践版在「参考版关键问题」中纠正：YOLACT（2019）和 YOLOv8-seg（2023）是两个独立工作。
实践版插入：无

### 第 3 章 — YOLACT 算法原理
参考版内容：双分支并行架构（Protonet + Prediction Heads）、原型掩码 + 掩码系数组合。
实践版插入：无（理论章节，实践版不重写）

### 第 4 章 — YOLOv8 实例分割模型
参考版内容：YOLOv8-seg 整体架构、与 YOLACT 对比、分割头的实现原理。
实践版插入：无

### 第 5 章 — YOLOv8-seg 模型选型
参考版内容：n/s/m/l/x 五档模型对比、精度/速度/参数量决策树。
实践版插入：
- `yolo_seg.py` — 插入到第 5 章末尾，作为「5.X 实践：本地图片实例分割」

### 第 6 章 — 本地视频实例分割
参考版内容：视频流读取 + mask 解析。
实践版插入：无（实践版本地程序覆盖图片分割，视频/实时用 ROS2 节点替代。如需本地视频版，可直接复用 04-1 的 `yolo_video.py`，仅把模型改为 `yolov8n-seg.pt`）

### 第 7 章 — ROS2 相机实例分割
参考版内容：ROS2 节点订阅 D435 → YOLOv8n-seg 推理 → 实时显示。
实践版插入：
- `ros2_yolo_seg.py` — 替换第 7 章「完整代码」，作为「7.X 实践：Spark D435 实时实例分割」

---

## 参考版关键问题

- **YOLACT ≠ YOLOv8 基础**：参考版第 2~3 章将 YOLACT 作为 YOLOv8 实例分割的前置知识讲解，但两者是独立工作——YOLACT（2019，Bolya 等）和 YOLOv8-seg（2023，Ultralytics）没有继承关系。实践版在「参考版审查」中标注此问题，避免学员形成错误认知。
- **API 统一**：与 04-1 一样，YOLOv8-seg 使用 `YOLO('yolov8n-seg.pt')` 加载，与检测版唯一区别是模型名后缀 `-seg`。预测 API 完全相同：`model(image)` → `results[0].boxes` + `results[0].masks`。
- **mask 输出解读**：参考版未详细讲解 `masks.xy` 和 `masks.data` 的区别。实践版 `yolo_seg.py` 在终端打印每个实例的 `mask_pts`（轮廓点数），让学员直观理解遮罩数据的形状。
- **boxes.xywh 中心点陷阱**（04-1 已记录，04-2 同样适用）：`xywh[0]` 已是中心 x，不需要再加 `w/2`。
- **无本地视频程序**：参考版第 6 章有本地视频分割，实践版用 ROS2 实时节点覆盖（`ros2_yolo_seg.py`），更贴近机器人实际场景。

---

## 程序清单

### 本地图像程序

- `yolo_seg.py` — 本地图片实例分割。对 lena.png + two_blue_cube.png 推理，终端打印每个实例的类别、置信度、中心坐标、遮罩点数，并用 `r.plot()` 显示分割结果。插入到参考版「第 5 章」末尾。

### ROS2 相机程序

- `ros2_yolo_seg.py` — ROS2 D435 实时实例分割。订阅 `/camera/camera/color/image_raw`，YOLOv8n-seg 推理，mask 叠加显示，FPS 标注。替换参考版「第 7 章」完整代码。

---

## 1. yolo_seg.py — 本地图片实例分割

### 插入位置
参考版「第 5 章 YOLOv8-seg 模型选型」末尾，作为「5.X 实践：本地图片实例分割」

### 参考版描述
参考版第 5 章纯理论（模型选型对比表 + 决策树），无本地实践程序。第 6 章虽有本地视频分割，但缺少单张图片的入门级程序。

### 参考版审查
- ✅ 模型选型对比清晰（n/s/m/l/x 五档 + COCO mAP 数据）
- ⚠️ 缺少本地图片入门程序——学员看完选型后无法立刻动手验证"我的模型能用吗"

### 设计原因
在模型选型（第 5 章）之后立即提供一个**本地图片程序**，让学员：
1. 确认模型能加载（不需要相机、不需要 ROS2）
2. 看终端输出理解 `masks.xy` 的数据结构（每个实例的轮廓点数）
3. 对比 `result.boxes`（检测输出）和 `result.masks`（分割输出）的差异
4. 最小化依赖——只需要 Python + `yolov8n-seg.pt`，不依赖相机/ROS2

用 `lena.png`（经典测试图）和 `two_blue_cube.png`（多物体场景）——本地已有，不需联网下载。

### 完整代码

```python
#!/usr/bin/env python3
"""04-2 YOLO实例分割: 本地图片实例分割

用 YOLOv8n-seg 对 lena.png + two_blue_cube.png 做实例分割,
打印每个实例: 类别/置信度/边界框/遮罩点数。

与 04-1 目标检测的唯一区别: 模型名加 -seg, 输出含 result.masks。
"""

import sys
import os
import cv2
from ament_index_python.packages import get_package_share_directory
from ultralytics import YOLO

# 模型路径 — 需要先下载: yolo predict model=yolov8n-seg.pt (参考版第4章)
MODEL_NAME = 'yolov8n-seg.pt'

local_model = os.path.join(
    get_package_share_directory('vision_basics'), 'model', MODEL_NAME)
if os.path.exists(local_model):
    model_path = local_model
else:
    model_path = MODEL_NAME  # ultralytics 自动下载

print(f"模型: {model_path}")
model = YOLO(model_path)

base = os.path.dirname(__file__)
pics = os.path.join(base, '..', 'pictures')
images = [
    os.path.join(pics, 'lena.png'),
    os.path.join(pics, 'two_blue_cube.png'),
]

results = model(images, conf=0.25)

for i, r in enumerate(results):
    print(f"\n{'='*50}")
    print(f"图片 {i+1}: {os.path.basename(r.path)}")

    boxes = r.boxes
    masks = r.masks
    names = r.names

    if boxes is None or len(boxes) == 0:
        print("  未检测到目标")
        annotated = r.plot()
        cv2.imshow(f'Seg {i+1}', annotated)
        cv2.waitKey(0)
        continue

    for j in range(len(boxes)):
        cls_id = int(boxes.cls[j])
        conf = float(boxes.conf[j])
        xywh = boxes.xywh[j]
        name = names.get(cls_id, f'id:{cls_id}')

        # 遮罩点数
        mask_pts = len(masks.xy[j]) if masks and j < len(masks.xy) else 0

        print(f"  {name:<12} conf={conf:.2f} "
              f"center=({int(xywh[0])},{int(xywh[1])}) "
              f"mask_pts={mask_pts}")

    annotated = r.plot()
    cv2.imshow(f'Instance Seg {i+1}', annotated)
    cv2.waitKey(0)

cv2.destroyAllWindows()
```

### 执行流程

1. 从 `get_package_share_directory('vision_basics')` 加载 `yolov8n-seg.pt` 模型
2. 读取 `pictures/lena.png` 和 `pictures/two_blue_cube.png` 两张本地图片
3. `model(images, conf=0.25)` 批量推理
4. 遍历每张图片的检测结果：
   - 遍历每个实例：打印类别名、置信度、中心坐标、遮罩轮廓点数
   - 调用 `r.plot()` 生成带 mask 叠加的标注图
   - `cv2.imshow` 显示
5. 按任意键关闭窗口 → `destroyAllWindows` 退出

---

## 2. ros2_yolo_seg.py — ROS2 D435 实时实例分割

### 插入位置
替换参考版「第 7 章 ROS2 相机实例分割」中的「完整代码」，作为「7.X 实践：Spark D435 实时实例分割」

### 参考版描述
参考版第 7 章提供了 ROS2 节点框架（订阅图片话题 → YOLO 推理 → cv2 显示），使用 leo 专用话题 `/camera/color/image_raw`。

### 参考版审查
- ⚠️ 相机话题为 leo 专用 `/camera/color/image_raw`，实践版改为 Spark D435 实际话题 `/camera/camera/color/image_raw`
- ⚠️ 模型路径硬编码，实践版用 `get_package_share_directory`
- ✅ ROS2 节点结构正确：`CvBridge + YOLO + spin`

### 设计原因
- 话题适配 Spark D435（双 camera 前缀）
- 模型路径统一用 `get_package_share_directory`（与全仓一致）
- 增加 FPS 显示（推理速度标注在左上角），学员直观感受 `yolov8n-seg` 的实时性能
- 与 `ros2_yolo.py`（04-1 检测版）结构一致——唯一区别是模型名加 `-seg`

### 完整代码

```python
#!/usr/bin/env python3
"""04-2 YOLO实例分割: ROS2 相机实时实例分割

订阅 D435 彩色图像 → YOLOv8n-seg 推理 → mask 叠加显示。
与 ros2_yolo.py 的唯一区别: 模型加 -seg, 输出含遮罩。
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import os
from ament_index_python.packages import get_package_share_directory
from ultralytics import YOLO


MODEL_NAME = 'yolov8n-seg.pt'
local_model = os.path.join(
    get_package_share_directory('vision_basics'), 'model', MODEL_NAME)
MODEL = local_model if os.path.exists(local_model) else MODEL_NAME


class YoloSegNode(Node):
    def __init__(self):
        super().__init__('yolo_seg_node')
        self.bridge = CvBridge()
        self.model = YOLO(MODEL)
        self.conf = 0.3

        self.sub = self.create_subscription(
            Image, '/camera/camera/color/image_raw', self.callback, 10)
        self.get_logger().info(f'YOLOv8n-seg 已加载 | 等待相机帧')

    def callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

        results = self.model(frame, conf=self.conf, verbose=False)
        annotated = results[0].plot()

        speed = results[0].speed
        if speed and 'inference' in speed:
            fps = 1000.0 / speed['inference']
            cv2.putText(annotated, f'FPS: {int(fps)}', (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow('YOLOv8-seg Camera', annotated)
        cv2.waitKey(1)


def main():
    rclpy.init()
    node = YoloSegNode()
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

### 执行流程

1. ROS2 初始化 → 创建 `YoloSegNode`
2. `__init__`：加载 YOLOv8n-seg 模型 + 创建 CvBridge + 订阅 `/camera/camera/color/image_raw`
3. 每收到一帧相机图像：
   - `CvBridge` 将 `sensor_msgs/Image` 转为 OpenCV BGR
   - `model(frame, conf=0.3)` 推理 → `results[0].boxes`（边界框）+ `results[0].masks`（遮罩）
   - `results[0].plot()` 生成标注图（mask 叠加 + 边界框 + 类别标签）
   - 左上角显示 FPS（从 `results[0].speed['inference']` 换算）
   - `cv2.imshow` 显示
4. Ctrl+C → `destroyAllWindows` → `destroy_node` → `shutdown`

---

## 运行步骤

### 本地程序

```bash
cd /home/spark/Music/spark_humble/src/ros2_vision/vision_basics/vision_basics
export DISPLAY=:0

python3 yolo_seg.py
```

预期输出：
- 终端打印每张图片的每个实例信息（类别、置信度、中心坐标、遮罩点数）
- 弹出两个窗口，分别显示 lena.png 和 two_blue_cube.png 的分割结果（mask 叠加 + 边界框）
- 按任意键关闭窗口

### ROS2 相机程序

```bash
# 先启动相机
ros2 launch camera_driver_transfer start_camera.launch.py

# 确认相机话题
ros2 topic list | grep /camera/camera/color/image_raw

# 再运行分割节点
cd /home/spark/Music/spark_humble && source install/setup.bash
export DISPLAY=:0
ros2 run vision_basics ros2_yolo_seg
```

预期效果：
- 终端打印 "YOLOv8n-seg 已加载 | 等待相机帧"
- 弹出窗口 "YOLOv8-seg Camera"，实时显示相机画面 + mask 叠加
- 左上角显示 FPS
- Ctrl+C 退出

### 编译

```bash
cd /home/spark/Music/spark_humble
colcon build --packages-select vision_basics
# 预期：Summary: 1 package finished
```

---

## ⚠️ 常见坑

### mask 数据结构混淆

**症状**：访问 `results[0].masks[0]` 报错
**原因**：`masks` 不是 list，是 `Masks` 对象，用 `.xy` 和 `.data` 访问
**解决**：
```python
masks = results[0].masks
# ✅ 正确
masks.xy[0]    # 第 0 个实例的轮廓坐标 [(x,y), ...]
masks.data[0]  # 第 0 个实例的概率图 (H, W)
# ❌ 错误
masks[0]       # Masks 对象不支持索引
```

### 模型用错

**症状**：运行 `yolo_seg.py` 但输出只有边界框，没有 mask
**原因**：加载了 `yolov8n.pt`（检测模型）而不是 `yolov8n-seg.pt`（分割模型）
**解决**：确认模型名带 `-seg` 后缀，打印 `model.task` 应为 `'segment'`

### boxes.xywh 中心点陷阱

（04-1 已记录，04-2 同样适用）
`xywh[0]` 已经是中心 x 坐标，不需要再加 `w/2`。这与 OpenCV 的 `cv2.boundingRect` 等返回左上角的 API 不同。

### `NameError: name 'cv2' is not defined`

**症状**：模型推理成功，但在 `cv2.imshow()` 处崩溃
**原因**：文件没有 `import cv2`
**解决**：确保文件顶部有 `import cv2`
