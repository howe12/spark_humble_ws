# Spark ML/AI 课程 ROS2 适配方案

> 基于 14 篇飞书参考文档的完整分析，按章节顺序对每篇文档进行 ROS1→ROS2 迁移及代码修复。

---

## 1.1 机器学习概述

### 修改内容
- **问题**: linear_reg.py 是纯 Python 脚本（无 rospy 调用），但被放入 catkin ROS1 包运行
- **方案**: 直接放入 ml_basics，用 python3 运行，不依赖 ROS

### 程序执行流程
```
用户运行: python3 linear_reg.py
  → pandas 生成房价数据集（10条）
  → train_test_split 分割（8训练+2测试）
  → LinearRegression.fit() 训练
  → model.predict() 预测 + MSE 评估
  → 输出系数 + 预测新房价
```

### 修改项
| 项目 | 原始 | 修改后 |
|------|------|--------|
| 构建系统 | catkin_make | 无需构建 |
| 运行方式 | rosrun ml_ros_core linear_reg.py | python3 linear_reg.py |
| 存放位置 | scorpio_app/ml_ros_core/ | ml_basics/ml_basics/ |
| 代码本身 | 无需修改 | 无需修改 |
| shebang | #!/usr/bin/env python | #!/usr/bin/env python3 |

### 验证
```bash
cd /home/spark/Music/spark_humble
python3 src/ml_basics/ml_basics/linear_reg.py
```
预期输出: MSE≈2.37e8, RMSE≈15400, 新房价≈311250

---

## 1.2 数据分析 + 实时轨迹预估

### 状态: ✅ 已完成

### 已交付
- `data_analysis.py` — 传感器 CSV 加载→统计→可视化
- `imu_dead_reckon.py` — 纯IMU vs IMU+编码器航迹推算（改善 268x）
- `ros2_imu_tracker.py` — 订阅 /imu_data → 发布轨迹

### 程序执行流程（imu_dead_reckon.py）
```
python3 imu_dead_reckon.py
  → 生成仿真 IMU 数据（10s, 100Hz）
  → 纯IMU路径: 加速度二重积分 → 严重漂移 6m
  → IMU+编码器: EKF融合 → 误差 0.02m
  → 输出对比图 + 统计表
```

### 与原文档的差异
- 原文档 ROS1 节点（rospy + /imu_data topic）→ 改为本地仿真 + ROS2 节点
- 原文档 JY61P IMU → 改为通用仿真，参数可调
- 原文档 catkin_create_pkg → 用 ml_basics 统一管理

---

## 2.1 机器学习应用 + 垃圾分类实时推理

### 2.1a 训练脚本修复（独立 Python）
**涉及文件**: iris_data_show.py, irs_decesiontree.py, train_waste_tree.py

### 修改内容
- **np.int/np.float/np.bool 补丁**: 删除 `np.int = int` 等语句
- **train_test_split indices 问题**: scikit-learn 新版本不支持第三位置参数 indices
- **GLCM 效率**: 纹理计算改用 numpy 矢量化

### 程序执行流程（train_waste_tree.py）
```
python3 train_waste_tree.py
  → 加载图片数据集（5类×20张）
  → RGBWasteClassifier 提取12维特征
  → train_test_split（80/20）
  → DecisionTreeClassifier.fit()
  → 评估: accuracy + confusion_matrix + classification_report
  → joblib.dump(model, 'waste_classifier.pkl')
```

### 修改项
| 项目 | 原始 | 修改后 |
|------|------|--------|
| np.int/float/bool | np.int = int | 直接使用 int/float/bool |
| train_test_split | (X, y, indices, ...) | 先用 np.arange 生成索引再手动分 |
| GLCM | 双重 for 循环 | numpy 矢量化 |
| 数据集路径 | 硬编码 | ROS2 参数或环境变量 |

### 2.1b 垃圾分类实时推理迁移（ROS1→ROS2）
**涉及文件**: waste_classifier_node.py (×4: DT/RF/SVM/XGB)

### 修改内容
- rospy → rclpy
- 订阅 `/camera/color/image_raw` (sensor_msgs/Image)
- 发布 `/waste_classification` (String) + `/waste_classification/confidence` (Float32)
- CvBridge API 调整

### 程序执行流程
```
ros2 run ml_basics waste_classifier
  → Node.__init__(): 加载模型 + 创建订阅/发布者
  → image_callback(msg):
      cv_image = bridge.imgmsg_to_cv2(msg)
      features = extract_features(cv_image)  # 12维
      class_name, confidence = model.predict(features)
      result_pub.publish(class_name)
      confidence_pub.publish(confidence)
  → rclpy.spin(node)
```

### ROS1→ROS2 API 对照
| ROS1 API | ROS2 API |
|----------|----------|
| rospy.init_node() | rclpy.init() + Node() |
| rospy.Subscriber() | node.create_subscription() |
| rospy.Publisher() | node.create_publisher() |
| rospy.spin() | rclpy.spin(node) |
| rospy.loginfo() | node.get_logger().info() |
| rospy.get_param() | node.declare_parameter() |

---

## 2.2 文本指令机器人控制

### 修改内容（3 个 ROS1 节点 → ROS2）

#### 2.2a text_preprocessor.py（保留，无修改）
- 纯 Python，jieba 分词，无 ROS 依赖

#### 2.2b intent_classifier_node.py
- TF-IDF 意图分类
- 订阅 `/text_command` → 发布 `/intent_result` + `/intent_confidence`

#### 2.2c param_parser_node.py
- 解析意图参数
- 订阅 `/intent_result` + `/text_command` → 发布 `/cmd_params`

#### 2.2d cmd_control_node.py
- 指令→底盘控制
- 订阅 `/cmd_params` → 发布 `/cmd_vel`（geometry_msgs/Twist）

### 程序执行流程（完整流水线）
```
用户输入文字 "前进2米"
  → text_preprocessor: 分词 → ["前进", "2", "米"]
  → intent_classifier_node:
      接收 /text_command
      TF-IDF 分类 → intent="forward", confidence=0.95
      发布 /intent_result, /intent_confidence
  → param_parser_node:
      接收 /intent_result + /text_command
      提取参数: linear_speed=0.2, duration=10.0
      发布 /cmd_params
  → cmd_control_node:
      接收 /cmd_params
      查表: forward → (0.2, 0.0)
      发布 /cmd_vel (Twist)
```

### 修改项
| 文件 | 原始 | 修改后 |
|------|------|--------|
| text_preprocessor.py | 独立脚本 | 保留不变 |
| intent_classifier_node.py | rospy 节点 | rclpy 节点 |
| param_parser_node.py | rospy 节点 | rclpy 节点 |
| cmd_control_node.py | rospy 节点 | rclpy 节点 |

---

## 3.1 积木块神经网络构建

### 修改内容
- **类型**: 纯 PyTorch 独立脚本，无 ROS 依赖
- **问题**: 无代码问题，仅需验证 Python 3.11 + PyTorch 环境可运行

### 程序执行流程
```
python3 mnist_nn.py
  → torchvision.datasets.MNIST 下载/加载
  → DataLoader 批处理（batch_size=64）
  → 定义网络: Linear(784,128) → ReLU → Linear(128,10)
  → 训练 5 epochs: CrossEntropyLoss + SGD
  → 测试: 准确率 ~97%
  → 可视化: 损失曲线 + 预测样例
```

### 修改项
| 项目 | 原始 | 修改后 |
|------|------|--------|
| PyTorch 版本 | 不明确 | torch>=2.0 (Python 3.11 兼容) |
| 代码本身 | 无 ROS 依赖 | 无需修改 |
| 存放位置 | 独立目录 | ml_basics/ml_basics/ |

---

## 3.2 YOLOv8 配置课程

### 修改内容
- **类型**: YOLO 独立配置/训练，无 ROS 节点
- **问题**: 原文档引用 Python 3.8，需更新版本号

### 修改项
| 项目 | 原始 | 修改后 |
|------|------|--------|
| Python 版本 | 3.8 | 3.11 |
| ultralytics | 未指定 | ultralytics>=8.0 |
| pip 安装命令 | pip install ... | pip3 install ... |

---

## 4.1 颜色识别及应用

### 修改内容

#### 4.1a follow.py 核心节点（ROS1→ROS2）
- **问题**: 全篇最大单文件，~300 行，HSV 通道选择有误
- **修复**: HSV 通道逻辑 + 全部 ROS1 API → ROS2

### 程序执行流程
```
ros2 run ml_basics color_follow
  → Node.__init__():
      订阅 /camera/color/image_raw (RGB)
      订阅 /camera/aligned_depth_to_color/image_raw (Depth)
      发布 /cmd_vel (Twist)
  → image_cb(msg):
      cv_image = bridge.imgmsg_to_cv2(msg)
      hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
      mask = cv2.inRange(hsv, lower, upper)  # 蓝色: H[100,130]
      blurred = cv2.GaussianBlur(mask, ...)
      _, thresh = cv2.threshold(blurred, ...)
      morph = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, ...)
      contours, _ = cv2.findContours(morph, ...)
      if contours: 计算最大轮廓中心
  → depth_cb(msg):
      获取目标深度距离
  → move():
      根据中心偏移计算 Twist
      cmd_vel_pub.publish(twist)
```

### 修改项
| 项目 | 原始 | 修改后 |
|------|------|--------|
| **HSV 取通道** | 取 H 但阈值 90（错误） | 取 H 通道 + 阈值为蓝色范围 |
| 构建系统 | catkin_make | colcon build |
| ROS 库 | rospy | rclpy |
| CvBridge | 每次回调 new CvBridge() | __init__ 中创建 self.bridge |
| 随机偏移 | 可能越界 | 添加边界检查 |

---

## 4.2 人脸检测及应用

### 修改内容
- **smile_detect.py** (ROS1→ROS2)
- **Haar 路径硬编码**: `/usr/share/opencv4/` → `cv2.data.haarcascades`

### 程序执行流程
```
ros2 run ml_basics smile_detect
  → 加载级联分类器:
      face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
      smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')
  → image_cb(msg):
      灰度转换 → 人脸检测 → 对每个人脸区域检测笑脸
      检测到笑脸 → cv2.imwrite 抓拍保存
  → depth_cb(msg): 获取目标深度
```

### 修改项
| 项目 | 原始 | 修改后 |
|------|------|--------|
| Haar 路径 | 硬编码 /usr/share/opencv4/ | cv2.data.haarcascades |
| ROS 库 | rospy + rospkg | rclpy + ament_index_python |
| 缩进错误 | 多一个 tab | 修正 |

---

## 4.3 人脸识别及应用

### 修改内容（3 个节点 + 5 个 bug）

### 程序执行流程

**采集阶段 (get_img.py)**
```
ros2 run ml_basics face_get_img
  → 订阅 /camera/color/image_raw
  → Haar 人脸检测
  → 检测到人脸 → 裁剪 → resize(200,200) → 灰度 → 保存
  → 文件命名: {user_id}.{seq}.jpg
```

**训练阶段 (trainer.py)**
```
python3 face_trainer.py
  → 读取 face_dataset/ 下所有 .jpg
  → 解析 id = 文件名第一个数字
  → PIL 加载 → 灰度转换 → numpy 数组
  → LBPHFaceRecognizer.train(faces, ids)
  → 保存 trainer.yml
```

**识别阶段 (detect.py)**  
```
ros2 run ml_basics face_detect
  → 加载 trainer.yml + Haar cascade
  → 订阅 /camera/color/image_raw
  → image_cb(msg):
      灰度 → 人脸检测
      → LBPHFaceRecognizer.predict(face_roi)
      → 返回 (id, confidence)
      → confidence < 阈值 → 显示名字 "User{id}"
      → 否则 → "Unknown"
```

### 修改项（bug 修复）
| 位置 | 问题 | 修复 |
|------|------|------|
| trainer.py | os.listdir 无文件过滤 | 添加 `if f.endswith(('.jpg','.png'))` |
| trainer.py | 文件名解析脆弱 | `os.path.splitext(f)[0].split('.')[0]` |
| detect.py | `except:` 裸异常 | 改为 `except (IndexError, ValueError):` |
| detect.py | CascadeClassifier 每帧重建 | 移到 `__init__` 中 |
| detect.py | names.sort() 字符串排序 | `sorted(names, key=int)` |

### 依赖
- **opencv-contrib-python** (提供 cv2.face.LBPHFaceRecognizer_create)

---

## 依赖安装清单

```bash
pip3 install pandas numpy scikit-learn matplotlib seaborn opencv-python opencv-contrib-python pillow jieba joblib xgboost torch torchvision ultralytics
```
