# Spark Humble Topic & Service 参考

> 消息类型定义见 `spark_common_interfaces` 包。

## 底盘 (spark_base)

| 方向 | 名称 | 类型 | 说明 |
|---|---|---|---|
| Pub | `/odom` | `nav_msgs/Odometry` | 里程计 |
| Pub | `/imu_data` | `sensor_msgs/Imu` | IMU 数据（线加速度 + 角速度 + 姿态角） |
| Pub | `/wheel_states` | `sensor_msgs/JointState` | 轮子关节状态 |
| Pub | `/spark_base/command/velocity` | `geometry_msgs/Twist` | 实际执行的速度反馈 |
| Pub | `/spark_base/gyro` | `spark_base/GyroMessage` | 陀螺仪原始数据 |
| Pub | `/spark_base/sensor` | `spark_base/SparkBaseSensor` | 红外/超声传感器 |
| Pub | `/spark_base/dock` | `spark_base/SparkBaseDock` | 充电桩状态 |
| Sub | `/cmd_vel` | `geometry_msgs/Twist` | 速度控制指令 |
| Sub | `/dock_control` | `std_msgs/String` | 充电桩控制 |
| Sub | `/search_control` | `std_msgs/String` | 搜寻控制 |

## 相机 (realsense D435)

| 方向 | 名称 | 类型 | 说明 |
|---|---|---|---|
| Pub | `/camera/color/image_raw` | `sensor_msgs/Image` | RGB 彩色图像（640×480@30fps） |
| Pub | `/camera/color/camera_info` | `sensor_msgs/CameraInfo` | 彩色相机参数 |
| Pub | `/camera/aligned_depth_to_color/image_raw` | `sensor_msgs/Image` | 对齐到彩色的深度图（848×480） |
| Pub | `/camera/depth/image_rect_raw` | `sensor_msgs/Image` | 原始深度图 |
| Pub | `/camera/depth/camera_info` | `sensor_msgs/CameraInfo` | 深度相机参数 |

## 雷达 (ydlidar G6)

| 方向 | 名称 | 类型 | 说明 |
|---|---|---|---|
| Pub | `/scan` | `sensor_msgs/LaserScan` | 激光扫描数据（12Hz，360°） |

## 跟随 (spark_follower)

| 方向 | 名称 | 类型 | 说明 |
|---|---|---|---|
| Pub | `/cmd_vel` | `geometry_msgs/Twist` | 跟随控制速度 |
| Sub | `/camera/depth/color/points` | `sensor_msgs/PointCloud2` | 深度点云（行人检测） |
| Sub | `/scan` | `sensor_msgs/LaserScan` | 激光扫描（避障） |

## YOLO 视觉 (spark_yolov8)

| 方向 | 名称 | 类型 | 说明 |
|---|---|---|---|
| Sub | `/camera/color/image_raw` | `sensor_msgs/Image` | 输入图像 |
| Pub | `/yolo/debug_image` | `sensor_msgs/Image` | 标注后的调试图像 |
| Pub | `/yolo/objects` | `spark_common_interfaces/VisionInference` | 检测结果（类别 + 置信度 + bbox） |

## 语音 (spark_voice)

| 方向 | 名称 | 类型 | 说明 |
|---|---|---|---|
| Pub | `/cmd_vel` | `geometry_msgs/Twist` | 语音导航速度指令 |
| Pub | `/voice_command` | `std_msgs/String` | 识别出的语音指令文本 |

## 机械臂 (swiftpro)

| 方向 | 名称 | 类型 | 说明 |
|---|---|---|---|
| Pub | `/swiftpro/state` | `swiftpro/Status` | 机械臂状态 |
| Sub | `/swiftpro/command` | `swiftpro/Position` | 位置控制指令 |

## 3D 建图 (rtabmap)

| 方向 | 名称 | 类型 | 说明 |
|---|---|---|---|
| Sub | `/rgbd_image` | `rtabmap_msgs/RGBDImage` | RGB-D 同步数据（由 rgbd_sync 合成） |
| Sub | `/odom` | `nav_msgs/Odometry` | 里程计 |
| Sub | `/scan` | `sensor_msgs/LaserScan` | 激光扫描 |
| Pub | `/rtabmap/mapData` | `rtabmap_msgs/MapData` | 3D 地图数据 |

## 自定义消息 (spark_common_interfaces)

- `VisionInference` — `header` + `InferenceResult[]`（视觉推理结果聚合）
- `InferenceResult` — `class_name` + `score` + `bbox`（单个检测目标）
- `Position` — `x, y, z`（3D 位置，用于机械臂控制）
- `Status` — `uint8 status`（状态码）

## 核心数据流

```
D435 ──► /camera/color/image_raw ──► yolov8 ──► /yolo/objects
     ──► /camera/aligned_depth_to_color/image_raw ──► rgbd_sync ──► /rgbd_image ──► rtabmap

G6  ──► /scan ──► gmapping / cartographer / nav2 / follower

底盘 ──► /odom ──► nav2 / rtabmap / cartographer
     ◄── /cmd_vel ── teleop / follower / nav2 / voice
```

## 调试命令

```bash
# 查看所有活跃 topic
ros2 topic list

# 查看 topic 带宽
ros2 topic bw /camera/color/image_raw

# 查看 topic 发布频率
ros2 topic hz /scan

# 查看 topic 消息内容
ros2 topic echo /odom --once
```
