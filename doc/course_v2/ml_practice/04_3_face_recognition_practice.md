# 【实践版】4.3 人脸识别及应用

## 参考版结构对照

参考文档「4.3 人脸识别及应用」(`SOpad7e8UocaeTxBumLcVJnKnix`) 包含 3 个 ROS1 节点（采集/训练/识别）。实践版全部迁移至 ROS2 并修复 5 个 bug。

| 参考版 (ROS1) | 实践版 (ROS2) | 变更 |
|---------------|---------------|------|
| get_img.py | face_capture.py | rospy→rclpy |
| trainer.py | face_trainer.py | 去 rospy + 3 bug 修复 |
| detect.py | face_recognizer.py | 去 rospy + 3 bug 修复 |

## 🔴 Bug 修复详情

### Bug 1: trainer.py 无文件过滤

原代码 `os.listdir(path)` 遍历所有文件（包括 `.yml` 模型），`PIL.Image.open()` 对非图片文件崩溃。

**修复**: `if f.endswith(('.jpg','.jpeg','.png','.bmp'))`

### Bug 2: 文件名解析脆弱

原代码 `id = int(path.split('.')[0])` 假设严格 `1.jpg` 格式。

**修复**: `os.path.splitext(f)[0]` 安全提取

### Bug 3: bare except

原代码 `except:` 吞掉 KeyboardInterrupt。

**修复**: `except (IndexError, ValueError, TypeError)`

### Bug 4: CascadeClassifier 每帧重复加载

原代码在 `image_cb` 中每次回调都创建 `cv2.CascadeClassifier(...)`。

**修复**: `__init__` 中加载一次，保存为 `self.face_detector`

### Bug 5: names.sort() 字典序排序

原代码 `self.names.sort()` 产生 `['1','10','2','3']`

**修复**: `sorted(names, key=int)`

---

## 📝 程序执行流程

**采集阶段 (face_capture.py)**
```
ros2 run ml_basics face_capture
  → 订阅 /camera/color/image_raw
  → Haar 人脸检测 → 裁剪 → resize(200,200) → 灰度 → 保存
  → 文件命名: {user_id}.{seq}.jpg
```

**训练阶段 (face_trainer.py)**
```
python3 face_trainer.py
  → 读取 face_images/ 下所有 .jpg
  → PIL 加载 → 灰度 → numpy 数组
  → LBPHFaceRecognizer.train(faces, ids)
  → 保存 trainer.yml
```

**识别阶段 (face_recognizer.py)**
```
ros2 run ml_basics face_recognizer
  → 加载 trainer.yml + Haar cascade
  → image_cb(msg):
      灰度 → detectMultiScale → predict(face_roi)
      → confidence < 阈值 → 显示名字
      → 否则 → "Unknown"
```

### 运行命令

```bash
# 1. 采集人脸
ros2 run ml_basics face_capture --ros-args -p user_id:=1

# 2. 训练模型
python3 src/ml_basics/ml_basics/face_trainer.py

# 3. 实时识别
ros2 run ml_basics face_recognizer
```

### 依赖注意

`face_trainer.py` 需要 `opencv-contrib-python`（提供 `cv2.face.LBPHFaceRecognizer_create`）：

```bash
pip3 install opencv-contrib-python
```

> 完整代码 3 个文件见 `src/ml_basics/ml_basics/face_*.py`
