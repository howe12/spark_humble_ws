# Spark实践版 — 03-2 基于深度信息的目标跟随

适配说明：基于 Spark `spark_follower` 功能包（C++）翻译为 Python 教学版。
代码路径：`src/ros2_vision/vision_basics/`
核心算法：3D ROI 点云质心跟踪 + 比例控制律

---

## 参考版结构 & 实践版插入点

参考版共 5 章，理论以深度跟随原理为主线。参考版文档为空（仅标题），实践版基于 `spark_follower.cpp` 独立编写。

### 第 1 章 — 深度跟随入门

参考版内容：什么是深度跟随、与 2D 图像跟随的区别。

实践版插入：
- `depth_follow_centroid.py` — 质心跟踪算法原理演示 → 插入「1.3 核心算法」之后

### 第 2~3 章 — 点云 ROI + 控制律

实践版插入：
- `ros2_depth_follow.py` — ROS2 实时点云跟随节点 → 插入「3.2 cmd_vel 发布」之后
- `depth_follow_tuner.py` — 3D ROI 调参工具 → 插入「2.3 ROI 参数调节」之后

---

## 核心算法：3D 质心跟踪 + 比例控制

Spark 深度跟随的本质是 **3D ROI 点云质心跟踪 + 比例控制律**：

```
点云 (PointCloud2)
     ↓
3D ROI 过滤（X/Y/Z 范围）
     ↓
计算质心 (cx, cz)     ← 需要 > 2000 个有效点
     ↓
控制律:
  linear_x  = (cz - goal_depth) × z_scale
  angular_z = arcsin(cx / dist) × x_scale
     ↓
cmd_vel 发布
```

## 坐标系注意事项

| 坐标系 | X | Y | Z | 说明 |
|--------|---|---|---|------|
| 相机光学 | 右 | 下 | 前 | D435 默认 |
| 机器人 | 前 | 左 | 上 | ROS base_link |
| 本算法 | cx=pt.x | forward=-pt.y | cz=pt.z | 直接用相机坐标 |

**为什么用 `-pt.y`？** 相机 Y 轴向下，`-pt.y` 即机器人前方。质心 cx = 左右偏移，cz = 前后距离。

## 关键参数速查

| 参数 | 默认值 | 含义 |
|------|--------|------|
| `goal_depth` | 0.7m | 目标跟随距离 |
| `z_scale` | 1.2 | 线速度比例系数 |
| `x_scale` | 5.0 | 角速度比例系数 |
| `roi_x_min/max` | -0.2/0.2m | 左右 ROI 范围 |
| `roi_y_min/max` | 0.1/0.5m | 前方 ROI 范围 (-py) |
| `roi_z_max` | 1.5m | 高度上限 |
| `min_points` | 2000 | 最少有效点数 |

---

## 程序清单

### 本地演示程序

- `depth_follow_centroid.py` — 质心跟踪算法演示（纯数值，无需硬件）

### ROS2 节点

- `ros2_depth_follow.py` — 实时点云跟随节点（需 D435）
- `depth_follow_tuner.py` — 3D ROI 调参工具（需 D435，OpenCV 滑块）

---

## 1. depth_follow_centroid.py — 质心跟踪算法演示

### 插入位置
参考版「1.3 核心算法」之后，作为原理验证。

### 设计原因
把 C++ 的质心跟踪逻辑封装成纯 Python 函数，用模拟点云验证公式正确性。学生可以在无硬件环境下理解算法核心。

### 算法公式

```
质心: cx = Σx/n, cz = Σz/n  （ROI 内的点）

控制律:
  linear_x  = (cz - goal_depth) × z_scale    ← 距离控制
  angular_z = arcsin(cx / d) × x_scale       ← 方向控制
  d = sqrt(cx² + cz²)

死区:
  |cz - goal| < 0.05m → linear_x = 0
  |cx| < 0.087 → angular_z = 0
  n < 2000 → 停止
```

### 测试场景

1. **人在正前方 0.8m**（cz > goal → 后退）
2. **人在右前方 0.5m**（cz < goal → 前进 + 偏右 → 左转）
3. **目标丢失**（ROI 内 < 2000 点 → 停止）

### 完整代码
(见 `vision_basics/depth_follow_centroid.py`)

### 运行步骤

```bash
cd ~/Music/spark_humble/src/ros2_vision/vision_basics/vision_basics
python3 depth_follow_centroid.py
```

---

## 2. ros2_depth_follow.py — ROS2 实时点云跟随

### 插入位置
参考版「3.2 cmd_vel 发布」之后。

### 设计原因
Python 翻译 `spark_follower.cpp` 的完整点云回调逻辑。所有参数通过 ROS2 parameter 暴露，可用 `ros2 param set` 动态调参。

### 关键差异（vs C++ 原版）

- C++ 版有激光雷达避障（`scanCb`）→ Python 版省略，聚焦核心算法
- C++ 版用 PCL 库 → Python 版用 `sensor_msgs_py.point_cloud2`
- 算法逻辑完全一致：ROI 过滤 → 质心 → 控制律 → cmd_vel

### 核心代码（cloud_cb）

```python
def cloud_cb(self, msg):
    points = list(pc2.read_points(msg, field_names=('x','y','z'),
                                  skip_nans=True))
    x_sum, z_sum, n = 0.0, 0.0, 0
    for px, py, pz in points:
        forward = -py
        if (self.roi_x[0] < px < self.roi_x[1] and
            self.roi_y[0] < forward < self.roi_y[1] and
            pz < self.roi_z_max):
            x_sum += px; z_sum += pz; n += 1

    if n < self.min_points: self.publish_stop(); return

    cx, cz = x_sum/n, z_sum/n
    linear_x  = (cz - self.goal_depth) * self.z_scale
    angular_z = math.asin(cx / math.sqrt(cx*cx+cz*cz)) * self.x_scale
    self.publish_cmd(linear_x, angular_z)
```

### 运行步骤

```bash
# 终端 1: 启动 D435 点云
ros2 launch realsense2_camera rs_launch.py pointcloud.enable:=true

# 终端 2: 运行跟随节点
cd ~/Music/spark_humble && source install/setup.bash
ros2 run vision_basics ros2_depth_follow

# 动态调参（可选）
ros2 param set /depth_follow_node goal_depth 1.0
ros2 param set /depth_follow_node z_scale 0.8
```

### 注意事项

- ⚠️ 必须先启动机器人底盘驱动（接收 cmd_vel）
- ⚠️ 人在相机前方 0.3~2m 范围内才能被检测
- ⚠️ 点云话题: `/camera/camera/depth/color/points`（D435 默认路径）

---

## 3. depth_follow_tuner.py — 3D ROI 调参工具

### 插入位置
参考版「2.3 ROI 参数调节」之后。

### 设计原因
学生拖动 OpenCV 滑块实时观察 ROI 范围，点击深度图查看 3D 坐标，直观理解参数含义。

### 界面说明

- 左侧：RGB 彩色画面 + ROI 范围标注
- 右侧：深度热力图（蓝=近, 红=远）
- 底部滑块：X_min, X_max, Y_min, Y_max, Z_max, Goal
- 点击深度图：终端输出该点 3D 坐标

### 运行步骤

```bash
# 终端 1: 启动相机（需对齐深度）
ros2 launch realsense2_camera rs_launch.py align_depth.enable:=true

# 终端 2: 运行调参工具
cd ~/Music/spark_humble && source install/setup.bash
export DISPLAY=:0
ros2 run vision_basics depth_follow_tuner
```

---

## 编译

```bash
cd ~/Music/spark_humble
colcon build --packages-select vision_basics
```

---

## Spark onekey.sh 原始启动方式

```bash
cd ~/Music/spark_humble
./src/onekey.sh
# 选择「让SPARK跟着你走」（people_follow 函数）
# 底层启动: ros2 launch spark_follower spark_follower.launch.py
```

---

*课程制作：Spark 实践版 v2*
*更新日期：2026 年 7 月*
*基于 spark_follower.cpp (NXROBO) 翻译为 Python 教学版*
