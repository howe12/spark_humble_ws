# 【实践版】4.2 人脸检测及应用

## 参考版结构对照

参考文档「4.2 人脸检测及应用」(`DIbqdrojuoCbBoxfS1acQrKonzc`) 包含 2 个独立脚本 + 1 个 ROS1 节点。实践版合并为 1 个 ROS2 节点 + 1 个 bug 修复。

| 参考版内容 | 实践版处理 |
|-----------|-----------|
| face_photo.py / face_video.py (独立) | ⚠️ 跳过，直接交付 ROS2 节点 |
| smile_detect.py (ROS1) | 🔴 → face_smile_detect.py (ROS2) |
| Haar 路径硬编码 | 🔴 **Bug 修复**: `/usr/share/opencv4/` → `cv2.data.haarcascades` |
| 缩进错误 | 🔴 **Bug 修复**: 多余 tab |

## 🔴 Bug 修复

### Bug 1: Haar 级联路径硬编码

原代码 `/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml` 仅在 apt 安装 OpenCV 时存在，pip 安装或跨平台不可用。

**修复**: `cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'`，跨平台兼容。

### Bug 2: 缩进错误

原 `image_cb` 中 `roi_gray`/`roi_color` 行多余缩进（肉眼可见不对齐），可能导致 `IndentationError`。

---

## 📝 程序执行流程

```
ros2 run ml_basics face_smile_detect
  → __init__():
      加载级联分类器 (人脸 + 笑脸)
      订阅 /camera/color/image_raw
  → image_cb(msg):
      灰度转换 → detectMultiScale(人脸)
      对每个人脸区域 → detectMultiScale(笑脸)
      检测到笑脸 → cv2.imwrite 抓拍保存
```

### 运行命令

```bash
ros2 launch spark_bringup d435.launch.py
ros2 run ml_basics face_smile_detect
```

> 完整代码见 `src/ml_basics/ml_basics/face_smile_detect.py`
