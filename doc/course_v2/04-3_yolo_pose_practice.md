# Spark实践版 — 04-3 YOLO 姿态识别（肢体关键点）

> 基于 Spark `vision_basics` 包，`yolov8n-pose.pt` 模型。
> 参考版使用 `leo_yolov8_class` + 自动下载模型，实践版改为 `get_package_share_directory('vision_basics')` 本地加载。
> 新增「关键点解析与动作分析」章节——这是参考版缺失的从「检测到应用」的关键一步。

---

## 参考版结构 & 实践版插入点

参考版共 6 章：

### 第 1 章 — 姿态估计入门
参考版内容：什么是姿态估计、关键点概念、COCO 17 关键点定义、应用场景。
实践版：**保留理论**，不另写。COCO 17 关键点索引表在实践版程序中引用。

### 第 2 章 — YOLO-Pose 算法原理
参考版内容：Backbone → PANet → Detection Head 三段式架构、YOLO-Pose vs OpenPose。
实践版：**保留理论**，不另写。

### 第 3 章 — 模型选型
参考版内容：n/s/m/l/x 5 种 Pose 模型对比表、选型建议。
实践版：**保留理论**，实践版固定用 `yolov8n-pose.pt`（3.3M 参数，CPU 友好）。

### 第 4 章 — 本地视频肢体识别
参考版内容：`video_pose_detection.py`，从 `video_object_detection.py` 拷贝并改模型名。
实践版插入：
- `yolo_pose_image.py` → 插入「4.2 准备工作」之后 — 本地图片 + 打印 17 个关键点数据
- `yolo_pose_video.py` → 替换「4.3 完整代码」— 支持摄像头/视频文件，FPS 叠加

### 第 5 章 — ROS2 相机肢体识别
参考版内容：`ros2_pose_detection.py`，订阅 `/camera/camera/color/image_raw`。
实践版插入：
- `ros2_yolo_pose.py` → 替换「5.3 完整代码」— 订阅 D435 话题 + 终端打印关键点

### 第 6 章 — 关键点解析与应用
参考版内容：举手判断、手臂角度计算、深蹲计数。
实践版插入：
- `yolo_pose_action.py` 🔴 → 插入「6.4 举手动作」之后 — 实时摄像头举手检测 + 角度显示

---

## 参考版关键问题

- **模型加载不可靠**：参考版用 `YOLO('yolov8n-pose.pt')` 自动下载，GFW 下会失败。实践版用 `get_package_share_directory('vision_basics') + 'model/yolov8n-pose.pt'` 从本地加载。
- **路径写死 leo**：所有代码路径引用 `leo_agv`、`leo_yolov8_class`，学生换环境就跑不了。
- **第 4 章「拷贝改名」教坏习惯**：`cp video_object_detection.py video_pose_detection.py` 鼓励复制粘贴而非理解，实践版提供独立文件。
- **缺关键点数据输出**：参考版只用 `r.plot()` 画图，学生看不到 `keypoints.xy` 数据结构——实践版 `yolo_pose_image.py` 逐点打印坐标 + 置信度条。
- **缺摄像头实时版**：参考版第 4 章只处理视频文件，没有摄像头实时检测。实践版 `yolo_pose_video.py` 默认打开 `/dev/video0`。
- **ROS2 节点未验证 Spark 兼容**：参考版话题是 `input_image` (leo 自定义)，实践版改为 Spark D435 的 `/camera/camera/color/image_raw`。

---

## 程序清单

### 本地程序

- `yolo_pose_image.py` 🔴 — 本地图片 + 17 个关键点数据打印
- `yolo_pose_video.py` 🔴 — 摄像头/视频文件实时姿态估计 + FPS
- `yolo_pose_action.py` 🔴 — 举手检测 + 手臂角度分析

### ROS2 相机程序

- `ros2_yolo_pose.py` 🔴 — D435 实时姿态估计 + 终端输出关键点

所有程序在 `vision_basics/vision_basics/` 下。

---

# 第 4 章：本地图片 — 关键点数据探索

> **📌 本章学习重点**
> 理解: `results[0].keypoints.xy` 和 `.conf` 的数据结构
> 掌握: COCO 17 关键点索引，从坐标数组提取具体部位

## 完整代码

`yolo_pose_image.py`：

```python
#!/usr/bin/env python3
"""04-3 YOLO姿态识别: 本地图片关键点提取

读取图片 → YOLOv8n-pose 推理 → 打印每个人 17 个关键点的坐标和置信度。
与 04-1 目标检测的区别: 模型换 -pose, 输出含 keypoints。
"""
import os
import sys
import cv2
from ament_index_python.packages import get_package_share_directory
from ultralytics import YOLO

# ── 模型 ──
MODEL_PATH = os.path.join(
    get_package_share_directory('vision_basics'), 'model', 'yolov8n-pose.pt')
model = YOLO(MODEL_PATH)
print(f'模型: {MODEL_PATH}')

# ── 图片 ──
base = os.path.dirname(os.path.abspath(__file__))
img_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(base, '..', 'pictures', 'lena.png')
img = cv2.imread(img_path)
print(f'图片: {os.path.basename(img_path)} ({img.shape[1]}×{img.shape[0]})')

# ── 推理 ──
results = model(img, conf=0.3, verbose=False)
r = results[0]

# ── 关键点索引 ──
KEYPOINT_NAMES = {
    0: "鼻子",  1: "左眼",  2: "右眼",
    3: "左耳",  4: "右耳",
    5: "左肩",  6: "右肩",
    7: "左肘",  8: "右肘",
    9: "左腕", 10: "右腕",
   11: "左髋", 12: "右髋",
   13: "左膝", 14: "右膝",
   15: "左踝", 16: "右踝",
}

keypoints = r.keypoints
if keypoints is not None:
    n_people = keypoints.xy.shape[0]
    print(f'\n检测到 {n_people} 个人:')
    for p in range(n_people):
        print(f'\n── 人 {p+1} ──')
        kp = keypoints.xy[p]      # (17, 2)
        conf = keypoints.conf[p]  # (17,)
        for i in range(17):
            name = KEYPOINT_NAMES.get(i, f'kp{i}')
            x, y = int(kp[i][0]), int(kp[i][1])
            c = float(conf[i])
            bar = '█' * int(c * 10) + '░' * (10 - int(c * 10))
            print(f'  {i:2d} {name:4s} ({x:4d},{y:4d}) 置信度 {c:.2f} {bar}')
else:
    print('未检测到任何人')

# ── 可视化 ──
annotated = r.plot()
cv2.imshow('YOLOv8-Pose Image', annotated)
print('\n按任意键关闭窗口')
cv2.waitKey(0)
cv2.destroyAllWindows()
```

## 运行

```bash
cd ~/Music/spark_humble && source install/setup.bash
export DISPLAY=:0
python3.10 src/ros2_vision/vision_basics/vision_basics/yolo_pose_image.py

# 指定自定义图片
python3.10 src/ros2_vision/vision_basics/vision_basics/yolo_pose_image.py /path/to/photo.jpg
```

## 预期输出

```
模型: .../install/vision_basics/share/vision_basics/model/yolov8n-pose.pt
图片: lena.png (514×516)

检测到 1 个人:

── 人 1 ──
   0 鼻子   (312,325) 置信度 0.99 ██████████
   1 左眼   (300,310) 置信度 0.98 █████████░
   2 右眼   (324,310) 置信度 0.97 █████████░
   3 左耳   (290,315) 置信度 0.56 █████░░░░░
   4 右耳   (338,315) 置信度 0.54 █████░░░░░
   5 左肩   (270,370) 置信度 0.96 █████████░
  ...
```

> ⚠️ lena.png 里只有一张脸没有完整身体，所以标记检测率低（耳、肩以下几乎不可见）。换一张**含完整人体的图片**来体验 17 个关键点全貌。

---

# 第 5 章：摄像头实时 — 视频/相机姿态估计

## 完整代码

`yolo_pose_video.py`：

```python
#!/usr/bin/env python3
"""04-3 YOLO姿态识别: 摄像头实时姿态估计

打开摄像头(默认 /dev/video0) → YOLOv8n-pose 逐帧推理 → 绘制火柴人 + FPS。
按 q 退出。第一个参数可以传视频文件路径。
"""
import os
import sys
import cv2
from ament_index_python.packages import get_package_share_directory
from ultralytics import YOLO

# ── 模型 ──
MODEL_PATH = os.path.join(
    get_package_share_directory('vision_basics'), 'model', 'yolov8n-pose.pt')
model = YOLO(MODEL_PATH)
print(f'模型: {MODEL_PATH}')

# ── 视频源 ──
video_src = sys.argv[1] if len(sys.argv) > 1 else 0
cap = cv2.VideoCapture(video_src)
if not cap.isOpened():
    print(f'无法打开视频源: {video_src}')
    exit(1)
print(f'视频源: {video_src} | 按 q 退出')

cv2.namedWindow('YOLOv8 Pose', cv2.WINDOW_NORMAL)
cv2.resizeWindow('YOLOv8 Pose', 800, 600)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, conf=0.3, verbose=False)
    annotated = results[0].plot()

    # ── FPS ──
    speed = results[0].speed
    if speed and 'inference' in speed:
        fps = 1000.0 / speed['inference']
        cv2.putText(annotated, f'FPS: {int(fps)}', (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    cv2.imshow('YOLOv8 Pose', annotated)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

## 运行

```bash
# USB 摄像头
python3.10 src/ros2_vision/vision_basics/vision_basics/yolo_pose_video.py

# 视频文件
python3.10 src/ros2_vision/vision_basics/vision_basics/yolo_pose_video.py ~/Videos/dance.mp4
```

---

# 第 6 章：ROS2 相机实时 — Spark D435

## 完整代码

`ros2_yolo_pose.py`：

```python
#!/usr/bin/env python3
"""04-3 YOLO姿态识别: ROS2 D435 相机实时姿态估计

订阅 D435 彩色图像 → YOLOv8n-pose 推理 → 绘制火柴人+FPS → 显示。
与 ros2_yolo.py 的唯一区别: 模型换 yolov8n-pose.pt, 输出含关键点。

运行前确保:
  source install/setup.bash
  ros2 launch spark_bringup d435.launch.py   # 或类似启动相机
  export DISPLAY=:0
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import os
from ament_index_python.packages import get_package_share_directory
from ultralytics import YOLO

MODEL_PATH = os.path.join(
    get_package_share_directory('vision_basics'), 'model', 'yolov8n-pose.pt')

# ── COCO 关键点名称 ──
KEYPOINT_NAMES = {
    0: "鼻子",  1: "左眼",  2: "右眼",
    3: "左耳",  4: "右耳",
    5: "左肩",  6: "右肩",
    7: "左肘",  8: "右肘",
    9: "左腕", 10: "右腕",
   11: "左髋", 12: "右髋",
   13: "左膝", 14: "右膝",
   15: "左踝", 16: "右踝",
}

class YoloPoseNode(Node):
    def __init__(self):
        super().__init__('yolo_pose_node')
        self.bridge = CvBridge()
        self.model = YOLO(MODEL_PATH)
        self.conf = 0.3

        # Spark D435 彩色图像话题
        self.sub = self.create_subscription(
            Image, '/camera/camera/color/image_raw', self.callback, 10)
        self.get_logger().info(f'YOLOv8n-pose 已加载 | 等待 D435 相机帧')

    def callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

        results = self.model(frame, conf=self.conf, verbose=False)
        annotated = results[0].plot()

        # ── FPS ──
        speed = results[0].speed
        if speed and 'inference' in speed:
            fps = 1000.0 / speed['inference']
            cv2.putText(annotated, f'FPS: {int(fps)}', (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # ── 额外：打印关键点信息到终端 ──
        keypoints = results[0].keypoints
        if keypoints is not None and keypoints.xy.shape[0] > 0:
            kp = keypoints.xy[0]    # 第一个人的关键点
            conf = keypoints.conf[0]
            # 只打印高置信度关键点
            high_conf = [(i, KEYPOINT_NAMES.get(i, f'kp{i}'),
                          int(kp[i][0]), int(kp[i][1]), float(conf[i]))
                         for i in range(17) if conf[i] > 0.5]
            if high_conf:
                parts = [f'{name}({x},{y})' for _, name, x, y, _ in high_conf[:6]]
                self.get_logger().info(f'  {" ".join(parts)}')

        cv2.imshow('YOLOv8 Pose - D435', annotated)
        cv2.waitKey(1)


def main():
    rclpy.init()
    node = YoloPoseNode()
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

## 运行

```bash
# 终端 1：启动 D435 相机
ros2 launch spark_bringup d435.launch.py

# 终端 2：启动姿态识别节点
cd ~/Music/spark_humble && source install/setup.bash
export DISPLAY=:0
ros2 run vision_basics ros2_yolo_pose
```

## 预期终端输出

```
[INFO] [yolo_pose_node]: YOLOv8n-pose 已加载 | 等待 D435 相机帧
[INFO] [yolo_pose_node]:   鼻子(312,200) 左眼(300,188) 右眼(324,188) 左肩(270,240) 右肩(354,240) 左肘(250,300)
```

---

# 🔴 新增：关键点解析 — 举手检测与手臂角度

> 这是参考版没有的「深度学习 → 应用闭环」章节。
> 目标：不只「看见火柴人」，而是「理解动作语义」。

## 完整代码

`yolo_pose_action.py`：

```python
#!/usr/bin/env python3
"""04-3 YOLO姿态识别: 关键点解析 — 举手检测 + 手臂角度

从摄像头读取帧 → YOLOv8n-pose 推理 → 判断是否举手 + 计算手臂角度。
这是「从检测到应用」的关键一步：把关键点坐标变成语义动作。
"""
import os
import sys
import cv2
import math
import numpy as np
from ament_index_python.packages import get_package_share_directory
from ultralytics import YOLO

# ── 模型 ──
MODEL_PATH = os.path.join(
    get_package_share_directory('vision_basics'), 'model', 'yolov8n-pose.pt')
model = YOLO(MODEL_PATH)

# ── COCO 关键点索引 ──
LEFT_SHOULDER  = 5
RIGHT_SHOULDER = 6
LEFT_ELBOW     = 7
RIGHT_ELBOW    = 8
LEFT_WRIST     = 9
RIGHT_WRIST    = 10

def calc_angle(a, b, c):
    """计算三点夹角 ∠ABC (a=肩, b=肘, c=腕)"""
    v1 = a - b
    v2 = c - b
    cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
    return math.degrees(math.acos(np.clip(cos_angle, -1, 1)))

def analyze_pose(keypoints, person_idx=0):
    """分析单个人体姿态: 举手方向 + 手臂角度"""
    if keypoints is None or keypoints.xy.shape[0] == 0:
        return None
    kp = keypoints.xy[person_idx]
    conf = keypoints.conf[person_idx]

    result = []

    # ── 左臂 ──
    if all(conf[i] > 0.3 for i in [LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST]):
        l_angle = calc_angle(kp[LEFT_SHOULDER], kp[LEFT_ELBOW], kp[LEFT_WRIST])
        l_wrist_y = kp[LEFT_WRIST][1]
        l_shoulder_y = kp[LEFT_SHOULDER][1]
        result.append(f'左臂: {l_angle:.0f}°')
        if l_wrist_y < l_shoulder_y and l_angle > 120:
            result.append('  ⬆ 左手举起!')

    # ── 右臂 ──
    if all(conf[i] > 0.3 for i in [RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST]):
        r_angle = calc_angle(kp[RIGHT_SHOULDER], kp[RIGHT_ELBOW], kp[RIGHT_WRIST])
        r_wrist_y = kp[RIGHT_WRIST][1]
        r_shoulder_y = kp[RIGHT_SHOULDER][1]
        result.append(f'右臂: {r_angle:.0f}°')
        if r_wrist_y < r_shoulder_y and r_angle > 120:
            result.append('  ⬆ 右手举起!')

    return '\n'.join(result) if result else '未检测到完整手臂'

# ── 主循环 ──
video_src = sys.argv[1] if len(sys.argv) > 1 else 0
cap = cv2.VideoCapture(video_src)
print(f'视频源: {video_src} | 举手检测中 | 按 q 退出')
print(f'模型: {MODEL_PATH}')

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, conf=0.3, verbose=False)
    annotated = results[0].plot()

    # ── 分析第一个人的姿态 ──
    analysis = analyze_pose(results[0].keypoints, 0)
    if analysis:
        # 多行文字叠加
        y_offset = 60
        for line in analysis.split('\n'):
            cv2.putText(annotated, line, (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            y_offset += 25

    cv2.imshow('Pose Action Analysis', annotated)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

## 运行

```bash
cd ~/Music/spark_humble && source install/setup.bash
export DISPLAY=:0
python3.10 src/ros2_vision/vision_basics/vision_basics/yolo_pose_action.py
```

## 代码逻辑解析

📐 **角度计算**：
```
calc_angle(肩, 肘, 腕)  → 使用向量点积计算 ∠肩-肘-腕
180° = 手臂完全伸直
90°  = 手臂弯曲呈直角
```

⬆ **举手判断（两个条件必须同时满足）**：
1. 手腕 Y 坐标 < 肩膀 Y 坐标（在图像坐标系中 Y 向上递减，所以手腕在肩膀"上面"）
2. 手臂角度 > 120°（几乎是伸直的，排除弯曲手臂的情况）

## 拓展：怎么改成深蹲计数器？

```python
# 在 analyze_pose() 中追加:
LEFT_HIP, LEFT_KNEE, LEFT_ANKLE = 11, 13, 15
if all(conf[i] > 0.3 for i in [LEFT_HIP, LEFT_KNEE, LEFT_ANKLE]):
    knee_angle = calc_angle(kp[LEFT_HIP], kp[LEFT_KNEE], kp[LEFT_ANKLE])
    result.append(f'膝角: {knee_angle:.0f}°')
    if knee_angle < 100:
        result.append('  ⬇ 深蹲中!')
```

---

# 📦 前置准备：模型下载

```bash
# 方式 1：在 Python 中自动下载（需科学上网）
python3.10 -c "from ultralytics import YOLO; YOLO('yolov8n-pose.pt')"

# 方式 2：wget 手动下载
cd ~/Music/spark_humble/src/ros2_vision/vision_basics/model/
wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n-pose.pt

# 验证
ls -lh yolov8n-pose.pt          # 应显示 ~6.6MB
python3.10 -c "from ultralytics import YOLO; m=YOLO('yolov8n-pose.pt'); print(m.task)"
# → pose

# 重新编译让模型进入 install 目录
cd ~/Music/spark_humble && colcon build --packages-select vision_basics
```

---

# ⚠️ 常见坑

🕳️ **模型找不到**：`FileNotFoundError: yolov8n-pose.pt`
- 原因：`get_package_share_directory` 需要 `colcon build` 后才生效。先编译再运行。

🕳️ **`No module named 'cv2'`**：Hermes 虚拟环境里没有 OpenCV
- 用 `python3.10` 替代 `python3`（系统 Python 带了 ROS2 + OpenCV）

🕳️ **D435 无图像**：终端输出一直在等待
- 检查：`ros2 topic list | grep color/image_raw` 有没有 `/camera/camera/color/image_raw`
- 没有？先启动相机：`ros2 launch spark_bringup d435.launch.py`

🕳️ **窗口不显示**：`could not connect to display`
- SSH 远程连接需要 `export DISPLAY=:0`（以 spark 用户的桌面会话为准）
