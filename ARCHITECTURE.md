# Spark Humble 架构文档

> 面向开发者的系统架构说明。终端用户请参阅 [README.md](README.md)。

## 三层架构

```
┌─────────────────────────────────────────────────────┐
│                    onekey.sh                         │
│               (用户交互入口，13 个菜单)                 │
├─────────────────────────────────────────────────────┤
│                  应用层 (spark_app/)                  │
│  follower │ carry │ navigation2 │ rtab_map │ slam   │
│  yolov8 │ voice │ face_recognition │ torch │ tf     │
├─────────────────────────────────────────────────────┤
│                  核心层 (spark/)                      │
│  bringup │ description │ teleop │ test │ smach     │
│  common_interfaces │ serial-ros2 │ velocity_smoother│
├─────────────────────────────────────────────────────┤
│                  驱动层 (spark_driver/)               │
│  base (C++) │ camera (realsense) │ lidar (ydlidar)  │
│  arm (uarm/swiftpro)                                │
└─────────────────────────────────────────────────────┘
```

## 启动调用链

```
onekey.sh (设定 CAMERATYPE / LIDARTYPE / ARMTYPE)
  └─ 应用 launch (如 teleop.launch.py)
       └─ driver_bringup.launch.py  ← 统一底座
            ├─ spark_description.launch.py  (URDF 模型)
            ├─ spark_base.launch.py         (底盘驱动)
            ├─ start_camera.launch.py       (相机自动检测)
            │    └─ d435.launch.py / astra*.launch.py
            └─ start_lidar.launch.py        (雷达自动检测)
                 └─ ydlidar_g6.launch.py / ydlidar_g2.launch.py
```

- 所有应用 launch 都通过 `driver_bringup` 启动驱动层
- `driver_bringup` 4 个子 launch **并行启动**
- 相机/雷达类型由 `lsusb` + `/opt/lidar.txt` 自动检测

## 包依赖关系

```
应用层:
  spark_follower ──────► spark_bringup, tf2, geometry_msgs
  spark_carry ─────────► spark_bringup, smach
  spark_navigation2 ───► spark_bringup, nav2_bringup
  spark_rtab_map ──────► spark_bringup, rtabmap
  spark_slam_transfer ─► spark_bringup, gmapping / cartographer / slam_toolbox
  spark_yolov8 ────────► spark_bringup, ultralytics
  spark_voice ─────────► spark_bringup, voskros, smach

核心层:
  spark_bringup ───────► spark_description, spark_base, camera/lidar driver_transfer
  spark_description ───► xacro, realsense2_description
  spark_teleop ────────► spark_bringup

驱动层:
  spark_base ──────────► serial, tf2, nav_msgs
  camera_driver_transfer► realsense2_camera / astra_camera
  lidar_driver_transfer─► ydlidar_ros2_driver
```

## 数据流

```
         ┌──────────┐
         │   D435   │──► /camera/color/image_raw ──► yolov8 / follower / tensorflow
         │  相机    │──► /camera/aligned_depth_to_color/image_raw ──► rtabmap
         └──────────┘

         ┌──────────┐
         │   G6     │──► /scan ──► gmapping / cartographer / nav2 / rtabmap
         │  雷达    │
         └──────────┘

         ┌──────────┐
         │  底盘    │──► /odom ──► nav2 / rtabmap / cartographer
         │  base    │──► /imu_data
         └──────────┘     ▲
                     /cmd_vel  ←── teleop / follower / nav2
```

## 关键文件

| 文件 | 作用 |
|---|---|
| `src/onekey.sh` | 用户交互入口，12 个功能菜单 + 隐藏菜单 |
| `spark_bringup/launch/driver_bringup.launch.py` | 统一底座，所有应用 launch 的驱动入口 |
| `spark_bringup/launch/common_launch_args.py` | 5 个公共参数定义（Wave 2 提取，15 文件共享） |
| `spark_base/src/spark_base_driver.cpp` | 底盘 C++ 驱动（664 行），odom / IMU / 传感器 |
| `camera_driver_transfer/launch/start_camera.launch.py` | 相机自动检测（lsusb），选 D435 / Astra Pro / Astra |
| `lidar_driver_transfer/launch/start_lidar.launch.py` | 雷达自动检测（读 /opt/lidar.txt + lsusb） |

## 设计决策

### common_launch_args.py（Wave 2）

15 个应用 launch 文件共享 5 个参数声明，避免逐一修改：

- `camera_type_tel` — 相机类型（d435 / astra_pro）
- `lidar_type_tel` — 雷达类型（ydlidar_g2 / ydlidar_g6）
- `enable_arm_tel` — 是否启动机械臂
- `arm_type_tel` — 机械臂类型
- `namespace` — 多机器人命名空间

### PushRosNamespace 使用规范（Wave 3 + 5b）

- **只在 `driver_bringup.launch.py` 中使用** PushRosNamespace 包裹子 launch
- 子层（start_camera、d435、start_lidar、ydlidar_g6）**不再重复包裹**——避免 namespace 叠加
- `nav2_bringup.launch.py` 独立使用（不被 driver_bringup 包裹）

### 参数传递链

```
onekey.sh 设定环境变量
  → 应用 launch 声明 common_launch_args
    → driver_bringup 接收并向下传递
      → start_camera / start_lidar 接收并继续传递
```

Wave 1 修复了 driver_bringup → start_camera / start_lidar 的参数断链。

## 已完成优化

| Wave | 内容 | 影响 |
|---|---|---|
| 1 | 参数断链修复 | 2 文件 |
| 2 | 公共参数地基 | 16 文件，-331 行 |
| 3 | 死代码清理 + PushRosNamespace | 60+ 文件，-4721 行 |
| 5 | namespace 补全 + 叠加修复 | 9 文件，+27/-4 行 |

## 新增 Demo 指南

参见 [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)。
