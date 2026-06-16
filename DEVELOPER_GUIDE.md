# Spark Humble 开发者指南

> 如何新增功能、修改 launch 文件、添加传感器驱动。

## 项目结构速览

```
spark_humble/
├── src/
│   ├── onekey.sh              ← 用户交互入口
│   ├── test_launch.sh         ← 自动测试脚本
│   ├── spark/                 ← 核心层
│   │   ├── spark_bringup/     ← 统一底座（driver_bringup + common_launch_args）
│   │   ├── spark_description/ ← URDF 机器人模型
│   │   ├── spark_teleop/      ← 键盘遥控
│   │   ├── spark_test/        ← 老化测试
│   │   └── spark_common_interfaces/ ← 自定义消息定义
│   ├── spark_app/             ← 应用层
│   │   ├── spark_follower/    ← 行人跟随
│   │   ├── spark_carry/       ← 机械臂抓取
│   │   ├── spark_navigation2/ ← 2D 激光导航
│   │   ├── spark_rtab_map/    ← 3D 视觉导航
│   │   ├── spark_slam/        ← SLAM（gmapping / cartographer / toolbox）
│   │   ├── spark_yolov8/      ← YOLO 视觉检测
│   │   ├── spark_voice/       ← 语音控制
│   │   └── voskros/           ← Vosk 语音识别
│   └── spark_driver/          ← 驱动层
│       ├── base/              ← 底盘串口驱动 (C++)
│       ├── camera/            ← 相机驱动（realsense / astra）
│       ├── lidar/             ← 雷达驱动（ydlidar）
│       └── arm/               ← 机械臂驱动（uarm / swiftpro）
├── ARCHITECTURE.md            ← 架构文档
├── TOPICS.md                  ← Topic 参考
└── DEVELOPER_GUIDE.md         ← 本文档
```

## 新增一个 Demo

### Step 1: 创建应用包

```bash
cd src/spark_app
ros2 pkg create --build-type ament_python spark_my_demo \
  --dependencies rclpy std_msgs sensor_msgs geometry_msgs
```

### Step 2: 写应用 launch 文件

创建 `src/spark_app/spark_my_demo/launch/my_demo.launch.py`：

```python
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from spark_bringup.common_launch_args import declare_common_arguments

def generate_launch_description():
    spark_bringup_dir = get_package_share_directory('spark_bringup')

    # 1. 声明公共参数（必须！）
    declared_arguments = declare_common_arguments()

    # 2. 引用参数
    camera_type_tel = LaunchConfiguration('camera_type_tel')
    lidar_type_tel = LaunchConfiguration('lidar_type_tel')
    namespace = LaunchConfiguration('namespace')

    # 3. 启动驱动（必须！）
    driver_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(spark_bringup_dir, 'launch', 'driver_bringup.launch.py')),
        launch_arguments={
            'camera_type_tel': camera_type_tel,
            'lidar_type_tel': lidar_type_tel,
            'namespace': namespace,
        }.items())

    # 4. 启动自己的节点
    my_node = Node(
        package='spark_my_demo',
        executable='my_node',
        namespace=namespace,     # ← 必须加上 namespace
        output='screen')

    return LaunchDescription(declared_arguments + [driver_launch, my_node])
```

### Step 3: 注册到 onekey.sh

在 `src/onekey.sh` 中添加菜单项：

```bash
# 在菜单显示部分添加（约 657 行附近）
echo "  ${Green_font_prefix} 11.${Font_color_suffix} 我的新 Demo"

# 在 case 分支添加（约 700 行附近）
11)
    my_demo_function
    ;;
```

添加对应的函数：

```bash
my_demo_function(){
    PROJECTPATH=$(cd `dirname $0`; pwd)
    source ${PROJECTPATH}/install/setup.bash
    echo -e "${Info} 我的新 Demo"
    echo && stty erase ^? && read -p "按回车键开始："
    ros2 launch spark_my_demo my_demo.launch.py \
        camera_type_tel:=${CAMERATYPE} \
        lidar_type_tel:=${LIDARTYPE}
}
```

### Step 4: 注册到 test_launch.sh

在 `src/test_launch.sh` 中添加：

```bash
# 在 LAUNCH_FILES 数组末尾添加
"spark_my_demo:launch/my_demo.launch.py"
```

## 修改 Launch 文件注意事项

### 必须遵守的规则

1. **所有应用 launch 必须 import `declare_common_arguments`**：

```python
from spark_bringup.common_launch_args import declare_common_arguments
```

2. **所有应用 launch 必须传递 `namespace` 给 driver_bringup**：

```python
launch_arguments={..., 'namespace': namespace,}.items()
```

3. **自己的 Node 必须加上 `namespace=namespace`**：

```python
Node(package='xxx', executable='xxx', namespace=namespace, ...)
```

4. **不要在子层 launch 中使用 PushRosNamespace**——只在 driver_bringup 和 nav2_bringup 中使用。

### 修改后必须做的事情

```bash
# 1. 全量编译
colcon build --symlink-install    # 必须 37/37 通过

# 2. 推送
git add -A && git commit -m "..."
git push

# 3. 真机测试（涉底盘运动需先确认）
```

## 添加新传感器驱动

### 相机

1. 在 `src/spark_driver/camera/camera_driver_transfer/launch/` 下创建 `my_camera.launch.py`
2. 在 `start_camera.launch.py` 的 `camera_type_dict` 中添加 USB ID 映射
3. 在 `common_launch_args.py` 的 `camera_type_tel` choices 中添加新类型

### 雷达

1. 在 `src/spark_driver/lidar/lidar_driver_transfer/launch/` 下创建 `my_lidar.launch.py`
2. 在 `start_lidar.launch.py` 的 `lidar_type_dict` 中添加 USB ID 映射
3. 在 `common_launch_args.py` 的 `lidar_type_tel` choices 中添加新类型

## 编译

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install   # 37 包，~5 秒
```

- 不允许使用 `--packages-skip`
- 编译不通过 → 立刻修，不能带着错误进入下一步

## 测试

```bash
# 快速静态检查
bash src/test_launch.sh

# 真机单 demo 测试（不涉及底盘运动时）
source install/setup.bash
timeout 20 ros2 launch <package> <launch_file> <args...> 2>&1

# 测试前必须
git pull                          # 同步最新代码
lsusb | grep -iE "realsense|ch340|silabs"  # 确认硬件在线
```

## Git 工作流

```bash
# 改代码前：同步
git pull

# 改代码后：编译 → 提交 → 推送
colcon build --symlink-install
git add -A
git commit -m "类型: 简短描述"
git push
```

提交类型：`feat`（新功能）、`fix`（修 bug）、`refactor`（重构）、`docs`（文档）。
