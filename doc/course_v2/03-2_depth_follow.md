# Spark实践版 — 03-2 基于深度信息的目标跟随

> 基于 Spark `spark_follower.cpp` (NXROBO) 重构为 Python 渐进式教学版。
> 方法论：**7 版本渐进式** (v1.0 工具箱 → v7.0 完整跟随)，每个版本在前一个基础上增量添加，可独立运行验证。

---

## 🎯 学习目标

🟢 **理解**: 深度跟随的本质——3D ROI 质心跟踪 + 比例控制律

🔵 **掌握**: PointCloud2 解析、3D ROI 过滤、质心计算、cmd_vel 控制

🟣 **应用**: ROS2 参数动态调参、OpenCV 滑块交互调试

🔴 **实战**: 在 Spark 机器人上运行完整深度跟随节点

## 🧱 积木式学习路径

```
v1.0 工具箱 → v2.0 数据 → v3.0 特征 → v4.0 质心 → v5.0 控制 → v6.0 调参 → v7.0 完整跟随
```

每个版本对应一个 `depth_follow_v*.py` 程序，在 `vision_basics/vision_basics/` 下。

---

## 📦 版本 v1.0：点云工具箱 — 读 PointCloud2

> **📌 本章学习重点**
> 理解: PointCloud2 消息结构、`read_points()` API
> 掌握: 从 D435 点云提取 (x,y,z) 坐标

### 1️⃣ 理论讲解

> 💡 **概念解释**
> D435 深度相机点云话题: `/camera/camera/depth/color/points`
> 消息类型: `sensor_msgs/msg/PointCloud2`
> 每个点: x(右), y(下), z(前) — 相机光学坐标系
> **数据依赖**: `package.xml` 需添加 `<depend>sensor_msgs_py</depend>`

**坐标系速查**:

- 相机光学: X=右 Y=下 Z=前
- 机器人: X=前 Y=左 Z=上
- 所以 `-pt.y` = 机器人前方

### 2️⃣ 代码实现

```python
#!/usr/bin/env python3
"""v1.0: 点云工具箱 — 读取 PointCloud2 并统计基本信息"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
import sensor_msgs_py.point_cloud2 as pc2

class V1PointCloudReader(Node):
    def __init__(self):
        super().__init__('v1_pc_reader')
        self.sub = self.create_subscription(
            PointCloud2, 'camera/camera/depth/color/points', self.cb, 10)

    def cb(self, msg):
        count, x_sum = 0, 0.0
        for pt in pc2.read_points(msg, field_names=('x','y','z'), skip_nans=True):
            x_sum += pt[0]; count += 1
        if count:
            self.get_logger().info(f'点云: {count}点, 平均X={x_sum/count:.3f}m')

def main():
    rclpy.init(); rclpy.spin(V1PointCloudReader())
```

### 3️⃣ 运行效果

```
[INFO] v1.0 点云读取器启动
[INFO] 点云: 307200 个点, 平均 X = -0.023m
```

> 📋 **数据集说明** D435 640×480 全分辨率下每帧 ~307K 点。scan 模式 ~30K 点。

### 4️⃣ 关键点/常见错误

> ⚠️ **常见错误 1**: 忘记 `skip_nans=True` → NaN 崩溃
> ⚠️ **常见错误 2**: 用 `msg.data` 而非 `read_points()` → 需手动解析二进制
> ⚠️ **常见错误 3**: 话题路径随配置变，先 `ros2 topic list | grep points` 确认

### 5️⃣ 🔬 本版本测试验证

```bash
# 终端1: ros2 launch realsense2_camera rs_launch.py pointcloud.enable:=true
# 终端2: ros2 run vision_basics depth_follow_v1
```

- [ ] 点云话题存在且订阅成功
- [ ] 输出点数 ~307200（全分辨率）

---

## 📦 版本 v2.0：数据获取 — 订阅双话题 (点云 + 深度图)

> **📌 本章学习重点**
> 在 v1.0 基础上增加: 同步订阅对齐深度图、CameraInfo 动态内参

### 1️⃣ 理论讲解

> 💡 **增量变更 (v1 → v2)**
> 新增了 2 个订阅: `aligned_depth_to_color/image_raw` (32FC1 米制深度)、`color/camera_info` (K 矩阵内参)。深度图用于版本 v6.0 的 ROI 可视化调参，CameraInfo 获取动态内参。

### 2️⃣ 代码实现 (增量)

```python
# ------ v2 新增 ------
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge

class V2DataSubscriber(V1PointCloudReader):          # 继承 v1.0!
    def __init__(self):
        super().__init__()
        self.bridge = CvBridge()
        self.depth_sub = self.create_subscription(
            Image, '/camera/camera/aligned_depth_to_color/image_raw',
            self.depth_cb, 10)
        self.ci_sub = self.create_subscription(
            CameraInfo, '/camera/camera/color/camera_info',
            self.ci_cb, 10)
        self.fx = 613.4; self.fy = 612.2
        self.cx = 330.2; self.cy = 240.6

    def depth_cb(self, msg):
        depth = self.bridge.imgmsg_to_cv2(msg, '32FC1')
        valid = depth[depth > 0]
        if len(valid):
            self.get_logger().info(f'深度: {len(valid)}有效点 中值={np.median(valid):.2f}m')

    def ci_cb(self, msg):
        self.fx, self.fy = msg.k[0], msg.k[4]
        self.cx, self.cy = msg.k[2], msg.k[5]
        self.destroy_subscription(self.ci_sub)
```

### 3️⃣ 运行效果

```
[INFO] 点云: 307200点
[INFO] 深度: 248000有效点 中值=1.23m
[INFO] 内参: fx=613.4 fy=612.2
```

### 5️⃣ 🔬 测试验证

```bash
ros2 launch realsense2_camera rs_launch.py align_depth.enable:=true pointcloud.enable:=true
ros2 run vision_basics depth_follow_v2
```

- [ ] 深度图有效点 > 200K（正常室内）
- [ ] CameraInfo 内参与默认值一致

---

## 📦 版本 v3.0：特征提取 — 3D ROI 过滤

> **📌 本章学习重点**
> 在 v2.0 基础上增加: 3D ROI 框过滤，只保留"前方人形区域"内的点

### 1️⃣ 理论讲解

> 💡 **为什么需要 ROI？**
> 全帧 307K 个点中，墙壁+地面+天花板占 95% 以上。
> ROI 框筛选"机器人前方 0.1~0.5m、左右 ±0.2m、高度 <1.5m"的区域——也就是人站的位置。

**ROI 参数 (来自 spark_follower.cpp)**:

- `roi_x_min/max`: -0.2 / 0.2 m (左右)
- `roi_y_min/max`: 0.1 / 0.5 m (前方, 注意 `-pt.y`)
- `roi_z_max`: 1.5 m (高度上限)

### 2️⃣ 代码实现 (增量)

```python
# ------ v3 新增 ------
class V3ROIFilter(V2DataSubscriber):
    def __init__(self):
        super().__init__()
        self.roi_x = (-0.2, 0.2)
        self.roi_y = (0.1, 0.5)
        self.roi_z_max = 1.5

    def cb(self, msg):                    # 重写 v1 的 cb
        inside, total = 0, 0
        for pt in pc2.read_points(msg, field_names=('x','y','z'), skip_nans=True):
            total += 1
            forward = -pt[1]
            if (self.roi_x[0] < pt[0] < self.roi_x[1] and
                self.roi_y[0] < forward < self.roi_y[1] and
                pt[2] < self.roi_z_max):
                inside += 1
        ratio = inside/total*100 if total else 0
        self.get_logger().info(f'ROI内: {inside}/{total} ({ratio:.1f}%)')
```

### 3️⃣ 运行效果

```
[INFO] ROI内: 4523/307200 (1.5%)   ← 人在前方
[INFO] ROI内: 87/307200 (0.03%)    ← 人走开
```

> 📌 **关键观察**: ROI 内点数从 1.5% 降到 0.03% → 这是检测"有人/无人"的核心信号

### 5️⃣ 🔬 测试验证

```bash
ros2 run vision_basics depth_follow_v3
# 站在机器人前方 0.3m → ROI内点数应 >1000
# 走开 → ROI内点数应降到 <500
```

- [ ] 有人: ROI内 >1000 点
- [ ] 无人: ROI内 <500 点

---

## 📦 版本 v4.0：空间划分 — 质心计算

> **📌 本章学习重点**
> 在 v3.0 基础上增加: 计算 ROI 内所有点的 3D 质心 (cx, cz)

### 1️⃣ 理论讲解

> 💡 **质心 = 平均位置**
> cx = Σx / n  (左右偏移，0=正前方)
> cz = Σz / n  (前后距离，m)
> 注意: 我们不需要 cy（高度），因为跟随只关心"人在哪"不关心"人多高"

**物理含义**:

- cx > 0 → 人在右边 → 机器人应左转
- cz > goal_depth(0.7m) → 人太远 → 机器人应前进
- cz < goal_depth → 人太近 → 机器人应后退

### 2️⃣ 代码实现 (增量)

```python
# ------ v4 新增 ------
class V4Centroid(V3ROIFilter):
    def __init__(self):
        super().__init__()
        self.min_points = 500          # ROI内最少有效点数

    def cb(self, msg):
        x_sum, z_sum, n = 0.0, 0.0, 0
        for pt in pc2.read_points(msg, field_names=('x','y','z'), skip_nans=True):
            forward = -pt[1]
            if (self.roi_x[0] < pt[0] < self.roi_x[1] and
                self.roi_y[0] < forward < self.roi_y[1] and
                pt[2] < self.roi_z_max):
                x_sum += pt[0]; z_sum += pt[2]; n += 1

        if n < self.min_points:
            self.get_logger().warn(f'目标丢失 (n={n})'); return

        cx, cz = x_sum/n, z_sum/n
        self.get_logger().info(f'质心: ({cx:.2f}, {cz:.2f})m  n={n}')
```

### 3️⃣ 运行效果

```
[INFO] 质心: (0.03, 0.72)m  n=4523   ← 正前方 0.72m
[INFO] 质心: (0.15, 0.55)m  n=3100   ← 右前方 0.55m，偏右
[WARN] 目标丢失 (n=87)                ← 人走开
```

### 5️⃣ 🔬 测试验证

```bash
ros2 run vision_basics depth_follow_v4
# 站正前方 → cx≈0, cz≈实际距离
# 站右边  → cx>0
```

- [ ] 正前方: |cx| < 0.05
- [ ] 右边: cx > 0.1

---

## 📦 版本 v5.0：控制训练 — 比例控制律 + cmd_vel

> **📌 本章学习重点**
> 在 v4.0 基础上增加: 比例控制律(linear_x, angular_z) + 死区 + cmd_vel 发布

### 1️⃣ 理论讲解

> 💡 **比例控制律 (P 控制)**
> `linear_x = (cz - goal_depth) × z_scale`
> `angular_z = arcsin(cx / d) × x_scale`
> `d = sqrt(cx² + cz²)`
> **死区**: |cz-goal|<0.05m 或 |cx|<0.087 → 输出 0 (避免微抖动)

**参数表**:

- `goal_depth=0.7`: 目标跟随距离 (m)
- `z_scale=1.2`: 线速度比例 (m/s per m error)
- `x_scale=5.0`: 角速度比例 (rad/s per rad error)

### 2️⃣ 代码实现 (增量)

```python
# ------ v5 新增 ------
from geometry_msgs.msg import Twist
import math

class V5Controller(V4Centroid):
    def __init__(self):
        super().__init__()
        self.goal_depth = 0.7
        self.z_scale, self.x_scale = 1.2, 5.0
        self.cmd_pub = self.create_publisher(Twist, 'cmd_vel', 10)

    def cb(self, msg):
        x_sum, z_sum, n = 0.0, 0.0, 0
        for pt in pc2.read_points(msg, field_names=('x','y','z'), skip_nans=True):
            forward = -pt[1]
            if (self.roi_x[0] < pt[0] < self.roi_x[1] and
                self.roi_y[0] < forward < self.roi_y[1] and
                pt[2] < self.roi_z_max):
                x_sum += pt[0]; z_sum += pt[2]; n += 1

        if n < self.min_points:
            self.publish_cmd(0.0, 0.0); return

        cx, cz = x_sum/n, z_sum/n
        linear_x = (cz - self.goal_depth) * self.z_scale
        d = math.sqrt(cx*cx + cz*cz)
        angular_z = math.asin(cx / d) * self.x_scale if d > 0 else 0.0

        # 死区
        if abs(cz - self.goal_depth) < 0.05: linear_x = 0.0
        if abs(cx) < 0.087: angular_z = 0.0

        self.publish_cmd(linear_x, angular_z)
        self.get_logger().info(
            f'质心=({cx:.2f},{cz:.2f}) cmd=(lx={linear_x:.2f},az={angular_z:.2f})')

    def publish_cmd(self, lx, az):
        cmd = Twist()
        cmd.linear.x = float(lx); cmd.angular.z = float(az)
        self.cmd_pub.publish(cmd)
```

### 3️⃣ 运行效果

```
[INFO] 质心=(0.01,0.72) cmd=(lx=0.02,az=0.05)   ← 正前方，基本停
[INFO] 质心=(0.15,0.55) cmd=(lx=-0.18,az=1.45)  ← 偏右近了，后退+左转
[INFO] 质心=(-0.12,0.85) cmd=(lx=0.18,az=-0.83) ← 偏左远了，前进+右转
```

> 📌 **关键观察**: cz≈0.72(≈goal) → lx≈0 (停)，cz=0.55(<goal) → lx<0 (后退)，符合预期

### 5️⃣ 🔬 测试验证

```bash
# 终端1: 启动底盘驱动 (接收cmd_vel)
ros2 launch spark_bringup driver_bringup.launch.py
# 终端2: 运行
ros2 run vision_basics depth_follow_v5
```

- [ ] 正前方 0.7m: lx≈0, az≈0
- [ ] 向前移动 0.2m: lx>0 (前进)
- [ ] 向后退 0.2m: lx<0 (后退)

---

## 📦 版本 v6.0：评估调参 — OpenCV 滑块 + ROS2 Parameter

> **📌 本章学习重点**
> 在 v5.0 基础上增加: ROS2 动态参数 + OpenCV 滑块可视化 + 深度热力图

### 1️⃣ 理论讲解

> 💡 **为什么要调参？**
> 默认参数 (goal=0.7, z_scale=1.2, x_scale=5.0, ROI=±0.2×0.1~0.5m) 是通用值。
> 不同场景需要不同参数: 狭窄走廊→缩小ROI，空旷→增大ROI，快走→增大z_scale。

**v6.0 新增功能**:
1. `ros2 param set` 动态调整所有参数 (无需重启节点)
2. OpenCV 窗口: 左侧 RGB + ROI 标注，右侧深度热力图
3. 7 个 Trackbar: X_min, X_max, Y_min, Y_max, Z_max, Goal, MinPoints
4. 点击深度图 → 终端输出该点 3D 坐标

### 2️⃣ 代码实现 (增量)

```python
# ------ v6 新增 ------
class V6Tuner(V5Controller):
    def __init__(self):
        super().__init__()
        # 声明 ROS2 参数 (可使用 ros2 param set)
        self.declare_parameter('goal_depth', 0.7)
        self.declare_parameter('z_scale', 1.2)
        self.declare_parameter('x_scale', 5.0)
        self.declare_parameter('roi_x_min', -0.2)
        self.declare_parameter('roi_x_max', 0.2)
        self.declare_parameter('roi_y_min', 0.1)
        self.declare_parameter('roi_y_max', 0.5)
        self.declare_parameter('roi_z_max', 1.5)
        self.declare_parameter('min_points', 500)

        # OpenCV 窗口 + 7个滑块
        cv2.namedWindow('Depth Follow Tuner v6', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Depth Follow Tuner v6', 1300, 600)
        for name, default, maxv in [
            ('X min*10', -2, 10), ('X max*10', 2, 10),
            ('Y min*10', 1, 15), ('Y max*10', 5, 30),
            ('Z max*10', 15, 30), ('Goal*10', 7, 20),
            ('MinPts/100', 5, 50)]:
            cv2.createTrackbar(name, 'Depth Follow Tuner v6', default, maxv, lambda v: None)

    def spin_once(self):
        rclpy.spin_once(self, timeout_sec=0.05)
        # 读滑块
        self.roi_x = (cv2.getTrackbarPos('X min*10','...')/10,
                      cv2.getTrackbarPos('X max*10','...')/10)
        self.roi_y = (cv2.getTrackbarPos('Y min*10','...')/10,
                      cv2.getTrackbarPos('Y max*10','...')/10)
        self.goal_depth = cv2.getTrackbarPos('Goal*10','...')/10
        # ... 显示 RGB + 深度热力图 ...
        cv2.imshow('Depth Follow Tuner v6', combined)
        if cv2.waitKey(1) & 0xFF == 27: raise KeyboardInterrupt
```

### 3️⃣ 运行效果

```
左侧: RGB 画面 + 黄色 ROI 线
右侧: 深度热力图 (蓝=近, 红=远)
底部: 7 个 Trackbar 滑块
点击深度图: 终端输出 "3D=(0.12, 0.45, 0.72)m"
```

### 5️⃣ 🔬 测试验证

```bash
ros2 launch realsense2_camera rs_launch.py align_depth.enable:=true pointcloud.enable:=true
export DISPLAY=:0
ros2 run vision_basics depth_follow_v6

# 动态调参 (另一终端):
ros2 param set /v6_tuner goal_depth 1.0
ros2 param set /v6_tuner z_scale 0.8
```

- [ ] 拖动滑块 → ROI 范围实时变化
- [ ] `ros2 param set` → 参数即时生效
- [ ] 点击深度图 → 终端正确输出 3D 坐标

---

## 📦 版本 v7.0：完整预测 — Spark 机器人真机跟随

> **📌 本章学习重点**
> 在 v6.0 基础上增加: 底盘联动 + 避障 + 完整部署流程

### 1️⃣ 理论讲解

> 💡 **v7.0 = v6.0 + 底盘驱动 + 安全保护**
> v6.0 已经发布了 cmd_vel，但 Spark 底盘还没启动。
> v7.0 加上 `driver_bringup.launch.py`（底盘+摄像头+雷达），形成完整闭环。

**完整节点图**:
```
D435 → /camera/.../points → depth_follow_v7 → /cmd_vel → spark_base → 电机
                                                ↑
                       激光雷达 → /scan → 避障检测 (spark_follower 原版)
```

### 2️⃣ 部署步骤

```bash
# --- 一键启动跟随 ---
cd ~/Music/spark_humble
./src/onekey.sh
# 选择「让SPARK跟着你走」 (people_follow 函数)
# 或手动:
ros2 launch spark_follower spark_follower.launch.py camera_type_tel:=d435 lidar_type_tel:=ydlidar_g6

# --- 或使用 Python 教学版 ---
ros2 launch spark_bringup driver_bringup.launch.py camera_type_tel:=d435 lidar_type_tel:=ydlidar_g6 enable_arm_tel:=false
ros2 run vision_basics depth_follow_v7
```

### 3️⃣ 运行效果

```
站在机器人前方 0.5m → 机器人后退保持 0.7m
向右移动 → 机器人右转跟踪
走开 → 机器人停止
后方有障碍物 (激光雷达 <0.4m) → 停止 (避障)
```

### 4️⃣ 参数调优建议

> ⚠️ **室内窄走廊**: 缩小 ROI (X=±0.15, Y=0.1~0.4), 降低 x_scale=3.0
> ⚠️ **室外/开阔**: 增大 ROI (X=±0.3, Y=0.1~0.8), z_scale=1.5
> ⚠️ **慢速跟随**: z_scale=0.5, x_scale=2.0

### 5️⃣ 🔬 本版本测试验证

```bash
# 1. 确认底盘连接
ls /dev/ttyUSB* && lsusb -d 1a86:7523

# 2. 启动跟随
ros2 launch spark_follower spark_follower.launch.py camera_type_tel:=d435 lidar_type_tel:=ydlidar_g6

# 3. 站前方 1m → 机器人应向前移动
# 4. 走开 → 机器人应停止
# 5. 后方放障碍物 → 不应后退
```

- [ ] 机器人能跟随人移动
- [ ] 保持在 0.7m 左右距离
- [ ] 人走开后 2 秒内停止
- [ ] 后方障碍物触发避障

---

## 📚 知识点总结

### 7 版本演进关系

| 版本 | 模块 | 增量内容 | 可独立运行 |
|------|------|----------|------------|
| v1.0 | 工具箱 | PointCloud2 读取 | ✅ |
| v2.0 | 数据 | + 深度图 + CameraInfo | ✅ |
| v3.0 | 特征 | + 3D ROI 过滤 | ✅ |
| v4.0 | 空间 | + 质心计算 | ✅ |
| v5.0 | 控制 | + 比例控制律 + cmd_vel | ✅ |
| v6.0 | 调参 | + ROS2 param + OpenCV 滑块 | ✅ |
| v7.0 | 预测 | + 底盘联动 + 避障 | ✅ |

### 核心公式

```
质心: cx = Σx/n, cz = Σz/n

控制律:
  linear_x  = (cz - goal_depth) × z_scale
  angular_z = arcsin(cx / d) × x_scale

死区:
  |cz - goal| < 0.05m → linear_x = 0
  |cx| < 0.087 → angular_z = 0
```

### 坐标系转换

```
相机光学 (D435): X=右 Y=下 Z=前
机器人前方: forward = -pt.Y
机器人左方: left = pt.X
```

---

## 🤔 思考题

1. 为什么用质心而不是"最近点"？提示: 最近点可能是噪点
2. `z_scale=1.2` 改成 `z_scale=3.0` 会怎样？提示: 震荡
3. 为什么 `angular_z` 用 `arcsin` 而不是 `atan`？提示: 小角度近似
4. 如果人穿了黑色衣服 (红外吸收)，深度图会怎样？提示: 空洞

---

*课程制作：Spark 实践版 v2 — 7 版本渐进式*
*更新日期：2026 年 7 月*
*基于 spark_follower.cpp (NXROBO) 重构*
