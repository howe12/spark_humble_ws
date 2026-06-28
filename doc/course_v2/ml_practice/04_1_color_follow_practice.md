# 【实践版】4.1 颜色识别及应用

## 参考版结构对照

参考文档「4.1 颜色识别及应用」(`B3sudjbepo2vzsxflH6cBpUCn5e`) 包含 ~18 个 ROS1 教学片段 + 1 个完整 `follow.py` 节点。实践版合并为 1 个 ROS2 节点并修复 3 个 bug。

| 参考版内容 | 实践版处理 |
|-----------|-----------|
| ~18 个 OpenCV 教学片段（独立+ROS版） | ⚠️ 跳过片段，直接交付完整项目 |
| follow.py (ROS1) | 🔴 → color_follow.py (ROS2) |
| HSV 通道选取 | 🔴 **Bug 修复**: 阈值90对蓝色无效 |
| CvBridge 重复实例化 | 🔴 **Bug 修复**: __init__ 中创建一次 |
| 随机偏移越界 | 🔴 **Bug 修复**: np.clip 边界检查 |

## 🔴 Bug 修复详情

### Bug 1: HSV 通道逻辑错误

原代码在用 `inRange` 得到蓝色掩膜后，又取 H 通道做 `threshold(blurred, 90, ...)`——90 在 OpenCV 映射后对应青色/绿色，非蓝色（蓝 ≈ 100-130）。

**修复**: 废弃 H 通道二次阈值，直接对 inRange 掩膜做形态学处理。

### Bug 2: CvBridge 重复实例化

原代码每次回调都 `CvBridge().imgmsg_to_cv2(...)`，创建大量临时对象。

**修复**: `__init__` 中创建 `self.bridge = CvBridge()`，回调中复用。

### Bug 3: 随机偏移越界

原代码 `np.random.uniform(-5,5)` 加到像素坐标后直接索引深度数组，可能越界。

**修复**: `np.clip(y + offset, 0, height - 1)`。

---

## 📝 程序执行流程

```
ros2 run ml_basics color_follow
  → Node.__init__():
      订阅 /camera/color/image_raw (RGB)
      订阅 /camera/aligned_depth_to_color/image_raw (Depth)
      发布 /cmd_vel (Twist)
  → image_cb(msg):
      cv_image = bridge.imgmsg_to_cv2(msg)
      hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
      mask = cv2.inRange(hsv, lower_blue, upper_blue)
      morph = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
      contours, _ = cv2.findContours(morph, ...)
      if contours: 目标中心 = 最大轮廓的 minAreaRect 中心
  → depth_cb(msg):  获取目标深度
  → move():  中心偏移 → Twist (linear + angular)
```

### 运行命令

```bash
ros2 launch spark_bringup d435.launch.py
ros2 run ml_basics color_follow
```

> 完整代码见 `src/ml_basics/ml_basics/color_follow.py`
