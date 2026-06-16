# Spark Humble Wave 1: 参数断链修复 + 死代码微修

> **For Hermes:** 逐任务执行，每个任务改完后立即验证。

**Goal:** 修复 driver_bringup 到子 launch 之间的参数传递断链，以及 rtabmap namespace 默认值 bug。

**Architecture:** 改动仅限于 launch 文件层，不涉及 C++ 或 Python 节点源码。3 个文件改，纯参数透传和默认值修正。

**Tech Stack:** ROS2 Humble launch system (Python)

---

## Task 1: driver_bringup → start_camera 传递 camera_type_tel

**Objective:** camera_type_tel 参数在 driver_bringup 有声明但没传给 start_camera.launch.py

**Files:**
- Modify: `src/spark/spark_bringup/launch/driver_bringup.launch.py:148-152`

**Step 1: 改 driver_bringup.launch.py**

在 camera IncludeLaunchDescription 的 launch_arguments 里加 `camera_type_tel`:

```python
# 找到第 147-152 行
spark_camera_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(camera_driver_transfer_dir, 'launch',
                                                   'start_camera.launch.py')),
        condition=IfCondition(start_camera),
        launch_arguments={'dp_rgist': dp_rgist,
                          'namespace': namespace}.items())
```

改为:

```python
spark_camera_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(camera_driver_transfer_dir, 'launch',
                                                   'start_camera.launch.py')),
        condition=IfCondition(start_camera),
        launch_arguments={'dp_rgist': dp_rgist,
                          'namespace': namespace,
                          'camera_type_tel': camera_type_tel}.items())
```

**Step 2: 验证**

```bash
cd /home/spark/Music/spark_humble
source /opt/ros/humble/setup.bash
source install/setup.bash 2>/dev/null
# Dry-run: 检查 launch 文件能正常解析
python3 -c "
from launch import LaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
# Check syntax only
exec(open('src/spark/spark_bringup/launch/driver_bringup.launch.py').read())
print('OK')
"
```

---

## Task 2: driver_bringup → start_lidar 传递 lidar_type_tel

**Objective:** 同 Task 1，但针对雷达

**Files:**
- Modify: `src/spark/spark_bringup/launch/driver_bringup.launch.py:155-159`

**Step 1: 改 driver_bringup.launch.py**

```python
# 找到第 155-159 行
spark_lidar_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(lidar_driver_transfer_dir, 'launch',
                                                   'start_lidar.launch.py')),
        condition=IfCondition(start_lidar),
        launch_arguments={'namespace': namespace}.items())
```

改为:

```python
spark_lidar_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(lidar_driver_transfer_dir, 'launch',
                                                   'start_lidar.launch.py')),
        condition=IfCondition(start_lidar),
        launch_arguments={'namespace': namespace,
                          'lidar_type_tel': lidar_type_tel}.items())
```

**Step 2: 验证**

```bash
python3 -c "
exec(open('src/spark/spark_bringup/launch/driver_bringup.launch.py').read())
print('OK')
"
```

---

## Task 3: rtabmap.launch.py namespace 默认值修复

**Objective:** 把 rtabmap namespace 默认值从 'rtabmap' 改为 ''（空字符串）

**Files:**
- Modify: `src/spark_app/spark_rtab_map/launch/rtabmap.launch.py:419`

**Step 1: 改一行**

```python
# 找到第 419 行
DeclareLaunchArgument('namespace',      default_value='rtabmap',            description=''),
```

改为:

```python
DeclareLaunchArgument('namespace',      default_value='',            description=''),
```

**Step 2: 验证**

```bash
grep -n "namespace.*default_value.*rtabmap" src/spark_app/spark_rtab_map/launch/rtabmap.launch.py
# 预期: 无输出（已修复）
grep -n "namespace.*default_value" src/spark_app/spark_rtab_map/launch/rtabmap.launch.py
# 预期: 419:        DeclareLaunchArgument('namespace',      default_value='',            description=''),
```

---

## Task 4: colcon build 增量编译验证

**Objective:** 确认改完后编译不报错

```bash
cd /home/spark/Music/spark_humble
source /opt/ros/humble/setup.bash
colcon build --packages-select spark_bringup spark_rtab_map --symlink-install
```

预期: 两个包都编译通过，无报错。

---

## 改动汇总

| 文件 | 改动 | 行数 |
|---|---|---|
| `driver_bringup.launch.py` | camera 调用加 camera_type_tel | +1 |
| `driver_bringup.launch.py` | lidar 调用加 lidar_type_tel | +1 |
| `rtabmap.launch.py` | namespace default_value | 改 1 行 |
