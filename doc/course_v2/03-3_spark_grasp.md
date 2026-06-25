# 03-3 基于深度信息的物体识别抓取（Spark 实践版）

## 灵魂拷问：开始本课之前，请先回答

**问题 1：传统手眼标定（棋盘格）和 Spark 的线性回归法有什么不同？**

传统方法：拍 20+ 张棋盘格 → 解 PnP → 得到 4×4 手眼矩阵（Tsai/Zhang 法），数学严谨但步骤繁琐，对机械臂精度要求高。

Spark 方法：机械臂走 20 个位置 → 记录每个位置的像素坐标 → 跑两个一维线性回归 `x_arm = k₁·yc + b₁` / `y_arm = k₂·xc + b₂`，工程简洁，20 个点 3 分钟跑完。

**问题 2：为什么 Spark 可以简化标定？**

因为两个前提条件：
- 摄像头**固定向下安装**（eye-to-hand），不随机械臂运动
- 机械臂在**桌面 XY 平面**做抓取，Z 由机械臂自己控制

所以不需要完整的 6-DOF 手眼矩阵，只需要像素 XY → 机械臂 XY 的映射。

**问题 3：HSV 颜色标定和线性回归标定是什么关系？**

它们是两件独立的事：
- HSV 标定：让程序认识"这个颜色在当前光照下是什么 HSV 值"→ 用于检测物体
- 线性回归标定：让程序知道"像素坐标 (xc, yc) 对应的机械臂位置 (x, y) 是多少"→ 用于驱动机械臂

**问题 4：HSV 标定是标定什么？为什么标定后效果才好？**

HSV 标定不是标定"颜色本身的 HSV 值"，而是标定**当前光照 + 当前摄像头 + 当前角度下**的 HSV 值。换个灯管、换个摄像头型号、换个安装角度，HSV 阈值就要重标。

**问题 5：抓取失败的常见原因是什么？**

- 颜色识别失败（HSV 阈值不准 — 大概率）
- 标定文件丢失（`~/thefile.txt` 不存在或过期）
- 机械臂未正确上电/驱动未启动
- 摄像头曝光设置不合理
- 方块离机械臂工作范围太远

**问题 6：我能学会吗？**

- 需要的基础：Python + OpenCV + ROS2 基础 + 相机坐标基础
- 难度：⭐⭐⭐⭐（较难，涉及机械臂实操）
- 预计时间：5-6 小时
- ⚠️ 强烈建议先学完 02-2（颜色处理）、03-1（深度相机）、03-2（深度跟随）课程
- ⚠️ 需要 Spark 机器人实体（机械臂 + 深度摄像头）

**问题 7：深度相机在抓取中只是辅助吗？能不能直接用深度控制机械臂的 Z 轴？**

答案是：**可以，而且应该！**

当前 Spark 抓取用的是固定 Z 值（`z = -50mm`），这意味着只适配一种厚度的物体。深度相机可以直接测量物体表面距离，动态计算机械臂应该下降多深：

```
arm_z = table_z + (H_camera - depth) × 1000 + margin
```

- table_z = -110mm（机械臂接触桌面的 Z 值）
- H_camera = 摄像头光心到桌面的距离（米，可标定）
- depth = 深度相机测得的物体表面距离（米）
- margin = 10mm（安全余量）

高物体（5cm）→ depth 小 → arm_z ≈ -50mm（浅抓）
扁平物（5mm）→ depth 大 → arm_z ≈ -95mm（深抓）

本课程第 5.5 节会详细讲解这一步。

---

## 学完本课，你将能够

| 学习前 | 学完 |
|--------|------|
| "手眼标定 = 拍棋盘格" | 理解 Spark 的 20 点线性回归法 |
| "HSV 阈值随便设" | 掌握真机 HSV 标定流程 |
| "不知道机械臂怎么定位物体" | 理解像素→机械臂坐标映射 |
| "标定文件和抓取程序没关系" | 掌握标定→抓取的完整闭环 |
| "Z 轴高度只能写死" | 掌握深度→机械臂 Z 自适应抓取 |
| "抓取失败不知道怎么调" | 系统性排查抓取链路 |

---

## 章节目录

| 章节 | 标题 | 核心内容 | 预计时长 |
|------|------|----------|----------|
| 第 1 章 | Spark 手眼标定入门 | 整体流程、为什么用线性回归 | 20 分钟 |
| 第 2 章 | 了解 Spark 机械臂系统 | swiftpro 驱动、position_write_topic、手眼关系 | 25 分钟 |
| 第 3 章 | HSV 颜色标定（真机） | 吸盘标记 HSV 采样 + 自动计算阈值 | 40 分钟 |
| 第 4 章 | 像素-机械臂映射 | 20 点线性回归原理 + 标定程序运行 | 50 分钟 |
| 第 5 章 | 深度信息与机械臂联动 | 深度采样 + 深度→臂 Z 自适应 | 50 分钟 |
| 第 6 章 | 完整抓取项目实战 | 标定→识别→自适应 Z 抓取的闭环 | 60 分钟 |

---

## 学习基础要求

- ✅ 已完成 02-2 图像颜色处理课程
- ✅ 已完成 03-1 点云与深度相机课程
- ✅ 已完成 03-2 深度信息目标跟随课程
- ✅ Spark 机器人机械臂已上电（uArm swiftpro / sagittarius_arm）
- ✅ 深度摄像头安装完毕（D435 或 Astra Pro，向下安装）
- ✅ 准备好橙色标定标记（贴在吸盘上方）+ 蓝色方块（用于抓取）
- ✅ 工作空间已编译：`colcon build`

---

# 第 1 章 Spark 手眼标定入门

## 1.1 本章目的与目录

本章目标：
- 理解 Spark 机械臂抓取的整体流程
- 明确"手眼标定"在抓取中的核心作用
- 理解为什么 Spark 用线性回归而不是传统棋盘格标定

### 在开始本章前，请思考

**问题 1**：机械臂在 3D 空间工作，它怎么知道桌面上的物体在哪？
*提示：需要把"摄像头看到的像素位置"变成"机械臂能理解的 XY 坐标"。*

**问题 2**：传统手眼标定要拍棋盘格、解 PnP，Spark 为什么没有这一步？
*提示：Spark 的机械臂和摄像头是固定的，且只抓桌面 XY 平面的物体。*

**问题 3**：线性回归标定出来的 k₁, b₁, k₂, b₂ 分别代表什么？
*提示：`x_arm = k₁·yc + b₁`，`y_arm = k₂·xc + b₂`。*

## 1.2 Spark 抓取任务的本质

Spark 机械臂抓取物体的本质是：**让摄像头看到物体 → 算出它的像素坐标 → 用标定系数映射到机械臂坐标 → 驱动机械臂去抓**。

整个流程需要 3 个文件协同工作：

```
~/calibration_HSV.txt   ← HSV 颜色阈值（第 3 章标定）
~/thefile.txt           ← 像素→机械臂映射系数（第 4 章标定）
抓取程序                 ← 读取两个文件，执行抓取（第 6 章）
```

## 1.3 为什么 Spark 不用传统手眼标定？

传统手眼标定（Tsai 法 / Zhang 法）：
- 在机械臂末端装棋盘格
- 机械臂走 15-20 个位姿
- 每个位姿拍一张棋盘格照片
- 用 PnP 求解相机外参 + 手眼矩阵 AX=XB
- 得到 4×4 刚体变换矩阵

Spark 的简化前提：
- **摄像头固定向下**，不随机械臂运动（eye-to-hand）
- **机械臂只在桌面上方 XY 平面作业**，Z 高度由机械臂直接控制
- **吸盘朝下**，抓取时不需要 Roll/Pitch/Yaw 姿态

所以 Spark 不需要完整的 6-DOF 手眼矩阵，只需要 **XY 平面的 2D 映射**：像素 (xc, yc) → 机械臂 (x, y)。

## 1.4 Spark 标定方法：20 点线性回归

核心思想：在桌面 XY 平面上，像素坐标和机械臂坐标是**近似线性关系**。

验证思路：
- 驱动机械臂走到一个已知位置 (x_arm, y_arm)
- 记录摄像头看到的吸盘标记像素坐标 (xc, yc)
- 重复 20 次，得到 20 组数据
- 跑两个独立线性回归：
  - `x_arm = k₁·yc + b₁`（为什么是 yc？因为摄像头旋转了 90°）
  - `y_arm = k₂·xc + b₂`

标定路径（20 个点组成一条斜线）：
```
x_arm: 180 → 275mm（每次 +5mm）
y_arm: 200 → 10mm（每次 -10mm）
z_arm: -110mm（固定）
```

## 1.5 四个步骤的依赖关系

```
[HSV 标定]  ──→ [颜色识别]  ──→ [像素坐标 (u,v)]
                                        ↓
[20 点回归] ──→ [像素→臂映射] ──→ [机械臂坐标 (x,y)]
                                        ↓
                                  [机械臂抓取]
                                        ↓
                                  [搬走 → 释放]
```

💡 **关键提示**：
- HSV 标定是**前提**（第 3 章先做）—— 没有它，检测不到物体
- 20 点回归也是**前提**（第 4 章接着做）—— 没有它，不知道往哪走
- 两个标定文件**一旦环境变化（光照、摄像头位置改变），必须重标**

## 1.6 本章回顾

回答开头的问题：
- 问题 1：通过标定系数把像素映射成机械臂 XY
- 问题 2：因为摄像头固定、机械臂只在 XY 平面作业，不需要完整 6-DOF 矩阵
- 问题 3：k₁ 和 k₂ 是缩放比例（像素→mm），b₁ 和 b₂ 是偏移量

新问题：
- 🤔 Spark 的机械臂驱动是怎么工作的？position_write_topic 是什么？
- 🤔 摄像头和机械臂的手眼关系是怎么确定的？

---

# 第 2 章 了解 Spark 机械臂系统

## 2.1 本章目的与目录

本章目标：
- 了解 Spark 机器人支持的机械臂型号
- 理解 swiftpro 驱动的 topic 接口
- 掌握 position_write_topic 和 pump_topic 的用法
- 理解摄像头-机械臂的手眼关系

### 在开始本章前，请思考

**问题 1**：Spark 支持哪些机械臂？怎么自动识别？
*提示：`lsusb` 检查 USB 设备 ID。*

**问题 2**：机械臂怎么接收运动指令？
*提示：向 `position_write_topic` 发消息。*

**问题 3**：摄像头朝下装，机械臂也在下面——它们的手眼关系是什么？
*提示：摄像头"看到"吸盘标记 → 标记在像素中的位置 → 映射到机械臂坐标。*

## 2.2 Spark 机械臂型号

Spark 支持两种机械臂，由 `onekey.sh` 自动检测：

| USB ID | 型号 | 变量值 |
|--------|------|--------|
| `2341:0042` | uArm swiftpro | `ARMTYPE="uarm"` |
| `2e88:4603` | sagittarius_arm (射手座) | `ARMTYPE="sagittarius_arm"` |

检测逻辑（`onekey.sh` 第 50-59 行）：
```bash
if [ -n "$(lsusb -d 2341:0042)" ]; then
    ARMTYPE="uarm"
elif [ -n "$(lsusb -d 2e88:4603)" ]; then
    ARMTYPE="sagittarius_arm"
else
    echo "机械臂没有正确连接或未上电"
fi
```

## 2.3 swiftpro 驱动接口

机械臂通过 `swiftpro` 驱动包控制，启动后提供 3 个核心 topic：

### position_write_topic（控制机械臂末端位置）

消息类型：`swiftpro/msg/Position`

```
float32 x   # 机械臂末端 X 坐标（mm），前后方向
float32 y   # 机械臂末端 Y 坐标（mm），左右方向
float32 z   # 机械臂末端 Z 坐标（mm），上下方向
```

💡 **坐标系约定**：
- X 轴：机械臂前后方向（正 = 远离底座）
- Y 轴：机械臂左右方向（正 = 向右）
- Z 轴：垂直方向（正 = 向上，负 = 向下）

### pump_topic（控制吸盘/气泵）

消息类型：`swiftpro/msg/Status`

```
uint8 status   # 1 = 吸气（抓取），0 = 释放
```

### 典型控制序列

```python
# 1. 回到初始位置
pos = Position()
pos.x = 120.0; pos.y = 0.0; pos.z = 35.0
pub.publish(pos)

# 2. 移动到目标上方
pos.x = 200.0; pos.y = 50.0; pos.z = 20.0
pub.publish(pos)
time.sleep(3)

# 3. 下降
pos.z = -50.0
pub.publish(pos)
time.sleep(2)

# 4. 吸盘吸气
pump = Status()
pump.status = 1
pub.publish(pump)
time.sleep(2)

# 5. 抬起
pos.z = 50.0
pub.publish(pos)
time.sleep(3)
```

## 2.4 摄像头-机械臂的手眼关系

Spark 的摄像头安装方式是**固定向下**（eye-to-hand）：

```
        ┌─────────────┐
        │   摄像头      │ ← 固定在机器人框架上，朝下看桌面
        │    ↓         │
        ├─────────────┤
        │   机械臂      │ ← 在摄像头视野下方
        │   ├─吸盘     │
        │   │  [橙色]  │ ← 吸盘上的橙色标记（标定用）
        └───┴─────────┘
        ═══════════════  ← 桌面（物体摆放平面）
```

💡 **关键理解**：
- 摄像头**不动**（固定在框架上），机械臂**运动**
- 标定的本质：找出"摄像头看到的像素位置"和"机械臂末端的物理位置"之间的映射
- 因为摄像头固定 + 机械臂只在 XY 平面作业 → 用线性回归近似映射关系

## 2.5 Spark 机械臂驱动启动

在 `onekey.sh` 中，标定和抓取都通过 launch 文件启动机械臂驱动：

```
spark_carry_cal.launch.py      → 标定模式（HSV + 20点回归）
spark_carry_object.launch.py   → 抓取模式（HSV检测 + 抓取）
```

两个 launch 文件都会自动启动：
1. `driver_bringup.launch.py` — 机器人总驱动（底盘 + 摄像头 + 雷达）
2. `pro_control_nomoveit.launch.py` — 机械臂控制驱动

## 2.6 本章回顾

回答开头的问题：
- 问题 1：uArm swiftpro 和 sagittarius_arm，通过 `lsusb` 自动识别
- 问题 2：向 `position_write_topic` 发布 `Position` 消息
- 问题 3：摄像头固定向下，机械臂在视野下方 → 像素坐标可线性映射到机械臂 XY

新问题：
- 🤔 HSV 颜色标定具体怎么做？怎么确定"当前光照下"的 HSV 阈值？
- 🤔 标定程序在代码里是什么结构？

---

# 第 3 章 HSV 颜色标定（Spark 真机）

## 3.1 本章目的与目录

本章目标：
- 运行 Spark 的 HSV 颜色标定程序
- 理解标定程序的代码逻辑
- 掌握 HSV 阈值的物理含义
- 获得 `~/calibration_HSV.txt` 标定文件

### 在开始本章前，请思考

**问题 1**：为什么需要用 Spark 的真机标定而不是用"通用 HSV 值"？
*提示：光照、摄像头型号、安装角度都会影响 HSV 值。*

**问题 2**：标定程序为什么要把机械臂抬起来再开始？
*提示：吸盘上的橙色标记需要出现在摄像头视野中。*

**问题 3**：200 帧采集后取平均值有什么好处？
*提示：摄像头传感器有噪声，均值更稳定。*

## 3.2 HSV 标定原理

HSV 标定的目标是：**让程序知道"当前环境下，吸盘上的橙色标记是什么颜色"**。

整个过程分为 3 个阶段：

### 阶段 1：等待（前 200 帧）

机械臂移动到初始位置（x=120, y=0, z=35），提示用户调整方块：
```
"请将颜色块放入矩形框内"
```

### 阶段 2：采集（第 200~500 帧）

对图像中的一个**小矩形 ROI**（20×30 像素）连续采集 300 次 HSV 值，累积求和。

Spark 的标定 ROI 参数：
```python
cali_w = 20    # ROI 宽（像素）
cali_h = 30    # ROI 高（像素）
collect_times = 300   # 采集次数
```

### 阶段 3：计算阈值（第 500 帧）

- 取 300 次采集的 HSV 均值
- 以均值为中心，±H_range / ±S_range / ±V_range 作为阈值上下界
- 写入 `~/calibration_HSV.txt`

阈值范围计算：
```python
H_range = 12    # H 上下浮动 ±12
S_range = 120   # S 上下浮动 ±120
V_range = 120   # V 上下浮动 ±120

lower_H = int(mean_H - H_range)   # 下限
upper_H = int(mean_H + H_range)   # 上限
# S 和 V 同理，且确保不越界
```

💡 **关键提示**：H_range=12 比较紧（颜色偏差容忍小），S_range=120 和 V_range=120 比较宽（亮度和饱和度变化容忍大）。这是合理的——色相 (H) 是区分"橙色 vs 蓝色"的关键维度。

## 3.3 运行标定程序

### 前置条件

- [ ] 机械臂已上电、摄像头向下安装好
- [ ] 橙色标定标记贴在吸盘正上方
- [ ] 工作空间已编译
- [ ] 没有其他 ROS2 节点在运行

### 步骤 1：启动标定环境

```bash
cd ~/Music/spark_humble
source install/setup.bash
./src/onekey.sh
```

在菜单中输入对应数字，选择 **"机械臂与摄像头匹对标定"**（`cal_camera_arm` 函数）。

或者直接启动 launch：

```bash
cd ~/Music/spark_humble
source install/setup.bash
ros2 launch spark_carry spark_carry_cal.launch.py camera_type_tel:=d435
```

### 步骤 2：等待机械臂初始化

机械臂会自动移动到初始位置 (120, 0, 35)，此时可以看到吸盘上的橙色标记出现在摄像头画面中。

### 步骤 3：执行 HSV 标定

在新终端中，发送启动信号：

```bash
cd ~/Music/spark_humble
source install/setup.bash
ros2 topic pub /start_topic std_msgs/msg/String "data: 'start'" -1
```

标定程序会自动：
1. 用 200 帧等待你把标记对准
2. 用 300 帧采集 HSV 均值
3. 计算阈值范围并保存到 `~/calibration_HSV.txt`

### 步骤 4：验证结果

```bash
cat ~/calibration_HSV.txt
```

输出示例：
```
calibration_HSV is :12,80,90 24,200,210
```

含义：
- 下限：H=12, S=80, V=90
- 上限：H=24, S=200, V=210

## 3.4 标定程序代码详解

### 整体架构

标定程序的关键节点（在 `spark_carry_cal.launch.py` 中定义）：

```
hsv_detection   →  采集 HSV 值，写入 ~/calibration_HSV.txt
cali_cam        →  像素坐标检测（第 4 章用）
cali_pos        →  控制机械臂走 20 个位置（第 4 章用）
cali_send_topic →  发送 "start" 信号触发标定
```

### hsv_detection 核心逻辑

```python
def main(args=None):
    rclpy.init(args=args)
    g_node = rclpy.create_node('hsv_detection')
    
    # 读取参数：标定模式 or 抓取模式
    g_node.declare_parameter('spark_hsv_detection/color', 'calibration')
    name = g_node.get_parameter("spark_hsv_detection/color")
    
    arm_init()  # 机械臂移到初始位置 (120, 0, 35)
    time.sleep(3)
    
    HSV_value = [0, 0, 0]
    count = 0
    capture = cv2.VideoCapture(0)  # 打开摄像头
    
    # ROI 尺寸
    cali_w = 20   # 吸盘标记矩形宽
    cali_h = 30   # 吸盘标记矩形高
    collect_times = 300  # 采集次数
    
    while rclpy.ok():
        ret, img = capture.read()
        if count < 200:
            # 阶段1：提示用户对准
            cv2.putText(img, 'please put the color being tested in rectangle box!', ...)
        elif count > 200 and count < 200 + collect_times:
            # 阶段2：采集 HSV
            frame = img[310:310+cali_h, 355:355+cali_w]  # ROI 区域
            HSV_value = mean_hsv(frame, HSV_value)         # 累加 HSV
        elif count == 200 + collect_times:
            # 阶段3：计算阈值
            for i in range(3):
                HSV_value[i] /= collect_times   # 取均值
            lower_HSV, upper_HSV = hsv_range(HSV_value)    # 计算上下界
            save_hsv(name, lower_HSV, upper_HSV)           # 保存到文件
        count += 1
```

### mean_hsv 函数

```python
def mean_hsv(img, HSV_value):
    HSV = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    HSV_value[0] += np.mean(HSV[:, :, 0])  # H 均值累加
    HSV_value[1] += np.mean(HSV[:, :, 1])  # S 均值累加
    HSV_value[2] += np.mean(HSV[:, :, 2])  # V 均值累加
    return HSV_value
```

### hsv_range 函数

```python
def hsv_range(HSV_value):
    H_range = 12; S_range = 120; V_range = 120
    
    lower_H = max(0,   int(HSV_value[0] - H_range))
    upper_H = min(180, int(HSV_value[0] + H_range))
    lower_S = max(50,  int(HSV_value[1] - S_range))
    upper_S = min(255, int(HSV_value[1] + S_range))
    lower_V = max(50,  int(HSV_value[2] - V_range))
    upper_V = min(255, int(HSV_value[2] + V_range))
    
    lower_HSV = np.array([lower_H, lower_S, lower_V])
    upper_HSV = np.array([upper_H, upper_S, upper_V])
    return lower_HSV, upper_HSV
```

## 3.5 常见问题与排查

### 问题 1：标定出来的 HSV 值在别的光照下失效

**原因**：HSV 标定绑定了当前光照条件。

**解决**：换光照后重新标定。这也是为什么每次抓取前建议重新标定。

### 问题 2：看不到橙色标记

**原因**：摄像头曝光太高/太低，或者机械臂初始位置不对。

**解决**：
- 调整摄像头曝光（通过 `hsv_processor.py` 的 Exposure 滑块）
- 检查机械臂是否成功回到初始位置 (120, 0, 35)
- 确认橙色标记确实贴在吸盘上方

### 问题 3：标定文件写入失败

**原因**：`$HOME` 路径权限问题。

**解决**：检查 `~/calibration_HSV.txt` 是否存在，确认当前用户有写权限。

## 3.6 本章回顾

回答开头的问题：
- 问题 1：不同光照/摄像头/角度下 HSV 值不同，必须现场标定
- 问题 2：机械臂抬起到初始位置 (120, 0, z=35)，使吸盘标记进入摄像头视野
- 问题 3：消除摄像头传感器噪声，得到稳定的 HSV 均值

新问题：
- 🤔 有了 HSV 标定文件，怎么用线性回归把像素坐标映射到机械臂坐标？
- 🤔 20 个采样点怎么分布？机械臂怎么自动走这 20 个点？

---

# 第 4 章 像素-机械臂映射（20 点线性回归）

## 4.1 本章目的与目录

本章目标：
- 理解 Spark 的 20 点线性回归标定原理
- 运行标定程序，生成 `~/thefile.txt`
- 理解标定系数 k₁, b₁, k₂, b₂ 的物理含义

### 在开始本章前，请思考

**问题 1**：为什么是"机械臂走 20 个位置"而不是"摄像头拍 20 张棋盘格"？
*提示：Spark 用机械臂的已知位置作为"真值"，反过来标定摄像头到机械臂的映射。*

**问题 2**：为什么 x_arm 对 yc 回归，而不是对 xc 回归？
*提示：摄像头安装方向可能导致坐标轴交换。*

**问题 3**：线性回归的误差主要来自于哪里？
*提示：机械臂定位精度、摄像头畸变、像素检测噪声。*

## 4.2 标定原理

### 4.2.1 核心假设

Spark 手眼标定基于一个关键假设：**在桌面 XY 平面上，像素坐标 (xc, yc) 和机械臂坐标 (x_arm, y_arm) 近似线性关系**。

这个假设成立的条件：
1. 摄像头光轴垂直于桌面（无透视畸变）
2. 机械臂末端在标定平面内运动（Z 固定）
3. 标定范围足够小（20 个点覆盖约 100mm×200mm 区域）

### 4.2.2 标定流程

```
机械臂走到位置 P₁ (x₁, y₁, z=-110)
    ↓
记录像素坐标 (xc₁, yc₁) → 存入数组
    ↓
机械臂走到位置 P₂ (x₂, y₂, z=-110)
    ↓
记录像素坐标 (xc₂, yc₂) → 存入数组
    ↓
... 重复 20 次 ...
    ↓
用 20 组 (xc, yc) ↔ (x_arm, y_arm) 跑线性回归
    ↓
输出 k₁, b₁, k₂, b₂ → 保存到 ~/thefile.txt
```

### 4.2.3 20 个标定位置

机械臂走一条斜线，确保覆盖主要工作区域：

```python
for i in range(20):
    x_arm = 180 + i * 5    # 180 → 275mm
    y_arm = 200 - i * 10   # 200 → 10mm
    z_arm = -110           # 固定高度
```

### 4.2.4 线性回归公式

两个独立的线性回归（`sklearn.linear_model.LinearRegression`）：

```python
# 回归 1：机械臂 X 对像素 Y 回归
Reg_x_yc = LinearRegression().fit(yc_array, xarray)
k1 = Reg_x_yc.coef_[0][0]   # 斜率
b1 = Reg_x_yc.intercept_[0] # 截距
# 公式：x_arm = k1 * yc + b1

# 回归 2：机械臂 Y 对像素 X 回归
Reg_y_xc = LinearRegression().fit(xc_array, yarray)
k2 = Reg_y_xc.coef_[0][0]   # 斜率
b2 = Reg_y_xc.intercept_[0] # 截距
# 公式：y_arm = k2 * xc + b2
```

💡 **为什么交叉回归**（x_arm 对 yc，y_arm 对 xc）？

因为摄像头安装时可能旋转了约 90°，导致：
- 机械臂的 X 轴移动 → 在像素上表现为 Y 轴移动
- 机械臂的 Y 轴移动 → 在像素上表现为 X 轴移动

## 4.3 运行标定程序

### 前置条件

- [ ] 已完成第 3 章的 HSV 标定
- [ ] 机械臂仍在上电状态，摄像头正常工作
- [ ] 标定 launch 仍在运行（如果已退出，重新启动）

### 步骤 1：确认标定 launch 运行中

```bash
ros2 node list | grep cali
```

应能看到：
```
/cali_cam
/cali_pos
/hsv_detection
```

### 步骤 2：发送启动信号

```bash
ros2 topic pub /start_topic std_msgs/msg/String "data: 'start'" -1
```

### 步骤 3：观察标定过程

机械臂会自动走 20 个位置，每走一个位置后输出：

```
1/20, pose x,y: 180,200. cam x,y: 325,278
2/20, pose x,y: 185,190. cam x,y: 332,285
...
20/20, pose x,y: 275,10. cam x,y: 450,155
finish the calibration. please check the value. then press ctrl-c to exit
```

### 步骤 4：验证结果

```bash
cat ~/thefile.txt
```

输出示例：
```
0.3521 -0.5123 0.4156 -0.6234
```

含义：
- k₁ = 0.3521, b₁ = -0.5123 → `x_arm = 0.3521 × yc + (-0.5123)`
- k₂ = 0.4156, b₂ = -0.6234 → `y_arm = 0.4156 × xc + (-0.6234)`

## 4.4 标定程序代码详解

### 发布机械臂运动指令（cali_pos.py）

```python
def talker(threadName, delay):
    global g_node
    pub1 = g_node.create_publisher(Position, 'position_write_topic', 10)
    pub2 = g_node.create_publisher(Status, 'cali_pix_topic', 10)
    
    # 等待订阅者就绪
    while g_node.count_subscribers('position_write_topic') < 1:
        time.sleep(1)
    
    # 初始位置
    pos = Position()
    pos.x = 120.0; pos.y = 0.0; pos.z = 35.0
    pub1.publish(pos)
    time.sleep(10)  # 等待用户准备
    
    # 等 start 信号
    while start_cali == 0:
        time.sleep(1)
    time.sleep(5)
    
    # 走 20 个位置
    for i in range(20):
        time.sleep(1)
        pos.x = 180.0 + i * 5
        pos.y = 200.0 - i * 10
        pos.z = -110.0
        pub1.publish(pos)
        
        time.sleep(1.5)
        sta.status = 1
        pub2.publish(sta)  # 通知 cali_cam 记录当前像素
        time.sleep(1.5)
    
    # 回到初始位置
    pos.x = 120.0; pos.y = 0.0; pos.z = 35.0
    pub1.publish(pos)
```

### 记录像素坐标 + 执行回归（cali_cam.py 中的 command_callback）

```python
def command_callback(data):
    global xc_array, yc_array, xarray, yarray, index
    
    if index < 20:
        # 记录当前像素 + 当前机械臂位置
        xc_array[index] = xc    # 像素 X
        yc_array[index] = yc    # 像素 Y
        xarray[index] = 180 + index * 5       # 机械臂 X
        yarray[index] = 200 - index * 10      # 机械臂 Y
        
        index += 1
    
    if index == 20:
        # 跑线性回归
        Reg_x_yc = LinearRegression().fit(yc_array.reshape(-1,1), xarray)
        Reg_y_xc = LinearRegression().fit(xc_array.reshape(-1,1), yarray)
        
        k1 = Reg_x_yc.coef_[0][0]
        b1 = Reg_x_yc.intercept_[0]
        k2 = Reg_y_xc.coef_[0][0]
        b2 = Reg_y_xc.intercept_[0]
        
        # 保存到文件
        with open(os.environ['HOME'] + "/thefile.txt", 'w') as f:
            f.write(f"{k1} {b1} {k2} {b2}\n")
        
        print("finish the calibration.")
        index = 0
```

## 4.5 标定系数验证

拿到标定系数后，可以做一个简单的验证：**选一个颜色方块放到桌面上，手动记录它的大致位置，然后用 `grasp_object.py` 让机械臂去抓它**。

```bash
cd ~/Music/spark_humble
source install/setup.bash
ros2 launch spark_carry spark_carry_object.launch.py camera_type_tel:=d435
```

在 `hsv_processor.py` 的 GUI 中：
1. 调整 HSV 滑块使方块清晰可见
2. 点击 **SEND: ON** 启用发送
3. 在画面中框选方块 → 机械臂自动去抓

💡 **关键提示**：如果机械臂定位偏差超过 2cm，说明标定有问题——可能原因：
- 机械臂移动时摄像头有轻微晃动
- 光照变化（重新做 HSV 标定）
- 机械臂初始位置未归零

## 4.6 验证程序：线性回归原理推导

以下程序用模拟数据验证线性回归的数学原理（不需硬件）：

**程序 `grasp_regression_demo.py`** — 用 20 组模拟数据演示线性回归

```python
#!/usr/bin/env python3
"""03-3 线性回归标定原理验证：用模拟数据演示 Spark 的 20 点标定法"""

import numpy as np
from sklearn.linear_model import LinearRegression

# --- 模拟 20 组真实数据 ---
# 假设实际映射关系: x_arm = 0.4*yc - 10, y_arm = 0.5*xc - 20
# 加一点噪声模拟真实情况
np.random.seed(42)

x_arm_true = np.array([180 + i*5 for i in range(20)])     # 180→275
y_arm_true = np.array([200 - i*10 for i in range(20)])    # 200→10

# 反推像素坐标（加噪声）
yc_true = (x_arm_true + 10) / 0.4 + np.random.normal(0, 2, 20)
xc_true = (y_arm_true + 20) / 0.5 + np.random.normal(0, 2, 20)

print("=" * 60)
print("Spark 20 点手眼标定 — 线性回归原理验证")
print("=" * 60)
print()

# --- 回归 1: x_arm 对 yc ---
Reg_x_yc = LinearRegression().fit(yc_true.reshape(-1,1), x_arm_true)
k1 = Reg_x_yc.coef_[0]
b1 = Reg_x_yc.intercept_
print(f"回归 1: x_arm = {k1:.5f} × yc + ({b1:.5f})")
print(f"  真值: x_arm = 0.4 × yc + (-10)")

# --- 回归 2: y_arm 对 xc ---
Reg_y_xc = LinearRegression().fit(xc_true.reshape(-1,1), y_arm_true)
k2 = Reg_y_xc.coef_[0]
b2 = Reg_y_xc.intercept_
print(f"回归 2: y_arm = {k2:.5f} × xc + ({b2:.5f})")
print(f"  真值: y_arm = 0.5 × xc + (-20)")

print()
print("-" * 60)
print("验证：用回归系数反推机械臂坐标")
print(f"{'序号':<6} {'真值(x,y)':<18} {'预测(x,y)':<18} {'误差(mm)':<12}")
print("-" * 60)

for i in range(20):
    x_pred = k1 * yc_true[i] + b1
    y_pred = k2 * xc_true[i] + b2
    err = np.sqrt((x_pred-x_arm_true[i])**2 + (y_pred-y_arm_true[i])**2)
    print(f"{i+1:<6} ({x_arm_true[i]:>4.0f},{y_arm_true[i]:>4.0f})"
          f"        ({x_pred:>5.1f},{y_pred:>5.1f})"
          f"        {err:<12.2f}")

print()
print("=" * 60)
print("关键观察:")
print("  1. 线性回归能从噪声数据中恢复近似真值")
print("  2. 20 个采样点足以覆盖约 100mm 的工作范围")
print("  3. 误差主要来自摄像头噪声（实际约 2-5mm）")
print("  4. k1/k2 是比例系数（mm/pixel），b1/b2 是偏移（mm）")
```

## 4.7 本章回顾

回答开头的问题：
- 问题 1：因为摄像头固定 + 机械臂做 XY 平面运动，用机械臂已知位置反推映射更直接
- 问题 2：摄像头旋转约 90°，导致 x_arm 和 yc 相关，y_arm 和 xc 相关
- 问题 3：机械臂定位精度 ±1mm、摄像头像素噪声 ±2px、镜头畸变

新问题：
- 🤔 有了标定文件，抓取程序怎么把它们串起来？
- 🤔 深度相机在抓取中起什么作用？

---

# 第 5 章 深度信息与机械臂联动

## 5.1 本章目的与目录

本章目标：
- 理解深度相机在抓取中的核心作用
- 掌握深度采样策略（ROI 中值法）
- **学会用深度值动态控制机械臂 Z 轴**（本课亮点）
- 完成摄像头高度标定（H_camera）

### 在开始本章前，请思考

**问题 1**：Spark 抓取中，Z 轴是怎么确定的？
*提示：当前用固定值 z=-50，但为什么不直接用深度相机测出物体高度？*

**问题 2**：深度相机测的"深度"是相对于谁的距离？
*提示：是相机光心到物体表面的距离，不是到桌面的距离。*

**问题 3**：如果物体只有 2mm 厚（如一张卡片），z=-50 还能抓到吗？
*提示：z=-50 意味着机械臂末端离桌面还有 60mm 高（-110 桌面 - (-50) = 60mm），对 2mm 的卡片来说太高了。*

## 5.2 当前抓取的局限：固定 Z

Spark 现有的 `grasp_object.py` 使用硬编码的 Z 值：

```python
# 阶段 1：逼近
pos.z = 20.0     # 目标上方 20mm

# 阶段 2：下降抓取
pos.z = -50.0    # 固定下降深度

# 阶段 3：抬起
pos.z = 50.0     # 固定抬起高度
```

**问题**：`z = -50mm` 只对约 5cm 高的物体有效。为什么？

机械臂标定平面（桌面）在 z = -110mm。抓取时 z = -50mm 意味着机械臂末端离桌面还有 60mm（-110 - (-50) = 60mm）。加上物体高度 50mm + 安全余量 10mm = 60mm，刚好吻合。

但如果换成：
- 扁平物体（5mm）→ z=-50 太高，吸盘根本碰不到
- 高物体（8cm）→ z=-50 太低，会压坏物体

💡 **关键结论**：固定 Z = 固定物体高度假设。深度相机可以打破这个假设。

## 5.3 深度→机械臂 Z 的坐标系转换

### 5.3.1 坐标系关系

```
        ┌─────────┐
        │ 深度相机  │ ← 摄像头光心，距桌面 H_camera 米
        │    ↓    │
        │  depth  │ ← 深度值 = 相机光心到物体表面的距离
        ├─────────┤
        │ object  │ ← 物体，高度 object_h
        ═══════════  ← 桌面（z = -110mm）
```

### 5.3.2 核心公式

```python
# 深度→物体高度→机械臂 Z 的转换
depth_m    = get_depth_median(cx, cy, depth_img, radius=8)  # 米
object_h   = (H_camera - depth_m) * 1000                      # 毫米
grasp_z    = TABLE_Z + object_h + MARGIN_MM                   # 机械臂 Z 值

# 常量
TABLE_Z    = -110.0   # 机械臂接触桌面的 Z 值（从 20 点标定获得）
H_camera   = 0.450    # 摄像头离桌面高度（米，需实测，见 5.4 节）
MARGIN_MM  = 10.0     # 安全余量（吸盘压在物体上方 10mm）
```

### 5.3.3 数值验证

| 物体类型 | 实际高度 | depth(m) | object_h(mm) | arm_z(mm) | 固定 z=-50 能抓？ |
|----------|----------|----------|--------------|-----------|-------------------|
| 高方块 | 50mm | 0.400 | 50 | -50 | ✅ 刚好 |
| 中方块 | 30mm | 0.420 | 30 | -70 | ❌ 太高碰不到 |
| 扁平卡片 | 5mm | 0.445 | 5 | -95 | ❌ 差 45mm |
| 厚书 | 80mm | 0.370 | 80 | -20 | ❌ 会压坏 |

💡 **可以看到**：固定 z=-50 只适配一种物体；深度自适应自动适应所有厚度。

## 5.4 标定第三步：摄像头高度 H_camera

在 20 点回归标定（第 4 章）完成之后，加一步获取 H_camera：

### 原理

利用已知条件：机械臂标定平面（z=-110）就是桌面。把机械臂末端平贴在桌面上，读取深度图该位置的值，就是摄像头到桌面的距离 = H_camera。

### 操作步骤

```python
# 1. 机械臂移到桌面高度（标定结束时的位置）
pos = Position()
pos.x = 120.0; pos.y = 0.0; pos.z = -110.0  # 末端贴桌面
pub.publish(pos)
time.sleep(3)

# 2. 读取深度图桌面区域（取 ROI 中值，消空洞）
roi = depth_img[center_y-30:center_y+30, center_x-30:center_x+30]
valid = roi[roi > 0]
H_camera = np.median(valid)  # 单位：米

# 3. 保存
with open(os.environ['HOME'] + '/camera_height.txt', 'w') as f:
    f.write(f'{H_camera:.4f}\n')

print(f'摄像头离桌面高度: {H_camera:.3f}m')
```

### 为什么取中值而不是均值？

桌面可能有局部反光或异物导致 depth=0。中值对离群值鲁棒，30×30 像素的 ROI 即使有几处空洞也能给出准确值。

### 何时需要重标？

- ✅ 摄像头安装高度改变了
- ✅ 机械臂底座高度改变了
- ❌ 光照变化（不影响深度测量）

## 5.5 深度自适应抓取程序

### 核心改动：固定 Z → 动态 Z

原来的抓取逻辑（固定 Z）：

```python
# 阶段 2：固定下降
pos.z = -50.0
self.pos_pub.publish(pos)
```

改为深度自适应（动态 Z）：

```python
# 阶段 2：自适应下降
depth_m = get_depth_median(cx, cy, self.depth_img, radius=8)
if depth_m > 0 and depth_m < H_camera:
    object_h_mm = (self.H_camera - depth_m) * 1000
    grasp_z = TABLE_Z + object_h_mm + MARGIN_MM
    grasp_z = max(grasp_z, TABLE_Z + 5)  # 不低于桌面 + 5mm
else:
    grasp_z = -50.0  # fallback：深度读取失败时用默认值

self.get_logger().info(f'深度={depth_m:.3f}m → arm_z={grasp_z:.0f}mm')
pos.z = grasp_z
self.pos_pub.publish(pos)
```

### 完整程序：`grasp_spark_depth.py`

```python
#!/usr/bin/env python3
"""03-3 Spark 深度自适应抓取：HSV 检测→深度Z→标定映射→动态抓取
需要硬件：Spark 机器人 + 机械臂 + D435 + 蓝色方块
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from swiftpro.msg import Position, Status
import cv2
import numpy as np
import os
import time

# === 常量 ===
TABLE_Z = -110.0      # 机械臂桌面 Z（mm），从 20 点标定获得
MARGIN_MM = 10.0       # 抓取安全余量（mm）
FALLBACK_Z = -50.0     # 默认抓取 Z（深度失效时使用）

class GraspDepthNode(Node):
    def __init__(self):
        super().__init__('grasp_depth_node')
        self.bridge = CvBridge()
        self.rgb_image = None
        self.depth_image = None
        self.grasping = False
        
        # 1. 加载标定系数
        try:
            with open(os.environ['HOME'] + '/thefile.txt', 'r') as f:
                k1, b1, k2, b2 = map(float, f.read().split())
            self.k1, self.b1 = k1, b1
            self.k2, self.b2 = k2, b2
            self.get_logger().info(
                f'XY标定: k1={k1:.4f} b1={b1:.4f} k2={k2:.4f} b2={b2:.4f}')
        except FileNotFoundError:
            self.get_logger().error('未找到 ~/thefile.txt！请先完成第 4 章标定')
            raise
        
        # 2. 加载摄像头高度
        try:
            with open(os.environ['HOME'] + '/camera_height.txt', 'r') as f:
                self.H_camera = float(f.read().strip())
            self.get_logger().info(f'摄像头高度: {self.H_camera:.3f}m')
        except FileNotFoundError:
            self.get_logger().warn('未找到 ~/camera_height.txt，用默认值 0.45m')
            self.H_camera = 0.45
        
        # 3. 订阅
        self.rgb_sub = self.create_subscription(
            Image, 'camera/color/image_raw', self.rgb_cb, 10)
        self.depth_sub = self.create_subscription(
            Image, 'camera/camera/aligned_depth_to_color/image_raw',
            self.depth_cb, 10)
        
        # 4. 机械臂发布者
        self.pos_pub = self.create_publisher(
            Position, 'position_write_topic', 10)
        self.pump_pub = self.create_publisher(
            Status, 'pump_topic', 10)
        
        # 5. HSV 阈值（蓝色方块）
        self.lower_blue = np.array([100, 80, 80])
        self.upper_blue = np.array([130, 255, 255])
        
        self.get_logger().info('深度自适应抓取节点启动')
    
    def rgb_cb(self, msg):
        self.rgb_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
    
    def depth_cb(self, msg):
        self.depth_image = self.bridge.imgmsg_to_cv2(msg, '32FC1')
    
    def get_depth(self, x, y, radius=8):
        """ROI 中值深度采样"""
        if self.depth_image is None:
            return 0.0
        h, w = self.depth_image.shape
        x1, x2 = max(0, x-radius), min(w, x+radius+1)
        y1, y2 = max(0, y-radius), min(h, y+radius+1)
        roi = self.depth_image[y1:y2, x1:x2]
        valid = roi[roi > 0]
        return float(np.median(valid)) if len(valid) > 20 else 0.0
    
    def detect_blue_block(self):
        """HSV 检测蓝色方块 → 返回最大轮廓的 (cx, cy)"""
        if self.rgb_image is None:
            return None
        
        hsv = cv2.cvtColor(self.rgb_image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_blue, self.upper_blue)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)
        
        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        
        c = max(contours, key=cv2.contourArea)
        if cv2.contourArea(c) < 500:
            return None
        M = cv2.moments(c)
        if M['m00'] == 0:
            return None
        return int(M['m10']/M['m00']), int(M['m01']/M['m00'])
    
    def grasp(self, cx, cy):
        """深度自适应抓取"""
        self.grasping = True
        
        # --- 像素→机械臂 XY ---
        x_arm = self.k1 * cy + self.b1
        y_arm = self.k2 * cx + self.b2
        
        # --- 深度→机械臂 Z（核心改动！） ---
        depth_m = self.get_depth(cx, cy, radius=8)
        if depth_m > 0 and depth_m < self.H_camera:
            object_h_mm = (self.H_camera - depth_m) * 1000
            grasp_z = TABLE_Z + object_h_mm + MARGIN_MM
            grasp_z = max(grasp_z, TABLE_Z + 5.0)
            self.get_logger().info(
                f'深度={depth_m:.3f}m 物体高={object_h_mm:.0f}mm → arm_z={grasp_z:.0f}mm')
        else:
            grasp_z = FALLBACK_Z
            self.get_logger().warn(
                f'深度读取失败(depth={depth_m:.3f})，用默认 Z={grasp_z:.0f}mm')
        
        self.get_logger().info(
            f'抓取: 像素({cx},{cy}) → XY({x_arm:.0f},{y_arm:.0f}) Z({grasp_z:.0f})')
        
        pos = Position()
        pump = Status()
        
        # 阶段 1：逼近上方
        pos.x = float(x_arm); pos.y = float(y_arm); pos.z = 20.0
        self.pos_pub.publish(pos); time.sleep(3)
        
        # 阶段 2：自适应下降（用动态 Z 代替固定 -50）
        pos.z = float(grasp_z)
        self.pos_pub.publish(pos); time.sleep(2)
        
        # 阶段 3：吸气
        pump.status = 1
        self.pump_pub.publish(pump); time.sleep(2)
        
        # 阶段 4：抬起
        pos.x = 180.0; pos.y = 0.0; pos.z = 50.0
        self.pos_pub.publish(pos); time.sleep(3)
        
        # 阶段 5：搬走
        pos.x = 150.0; pos.y = 150.0; pos.z = 35.0
        self.pos_pub.publish(pos); time.sleep(3)
        
        # 阶段 6：释放
        pos.z = -50.0
        self.pos_pub.publish(pos); time.sleep(2)
        pump.status = 0
        self.pump_pub.publish(pump); time.sleep(2)
        
        # 回初始位置
        pos.x = 180.0; pos.y = 0.0; pos.z = 50.0
        self.pos_pub.publish(pos); time.sleep(3)
        
        self.grasping = False
        self.get_logger().info('抓取完成！')
    
    def spin_once(self):
        rclpy.spin_once(self, timeout_sec=0.05)
        if self.rgb_image is None:
            return
        
        display = self.rgb_image.copy()
        result = self.detect_blue_block()
        
        if result and not self.grasping:
            cx, cy = result
            cv2.circle(display, (cx, cy), 8, (0, 255, 0), -1)
            
            # 预计算并显示深度信息
            depth_m = self.get_depth(cx, cy, radius=8)
            if depth_m > 0:
                object_h = (self.H_camera - depth_m) * 1000
                arm_z = TABLE_Z + object_h + MARGIN_MM
                cv2.putText(display,
                    f'depth={depth_m:.3f}m h={object_h:.0f}mm Z={arm_z:.0f}',
                    (cx+10, cy-10), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (255, 0, 0), 2)
                cv2.putText(display,
                    f'Fixed Z=-50 vs Adaptive Z={arm_z:.0f}',
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (0, 0, 255), 2)
            else:
                cv2.putText(display,
                    f'XY({cx},{cy}) depth=N/A',
                    (cx+10, cy-10), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (0, 0, 255), 2)
        
        cv2.putText(display, 'Press G to grasp (adaptive Z)', (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow('Spark Grasp (Depth Adaptive)', display)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('g') and result and not self.grasping:
            cx, cy = result
            self.grasp(cx, cy)
        elif key == 27:
            raise KeyboardInterrupt

def main():
    rclpy.init()
    node = GraspDepthNode()
    try:
        while rclpy.ok():
            node.spin_once()
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
```

## 5.6 深度采样策略

### 5.6.1 单点采样（基础）

```python
def get_depth_single(x, y, depth_img):
    z = depth_img[y, x]
    return z if z > 0 else 0.0
```

问题：遇到深度空洞（0 值）直接失败。

### 5.6.2 ROI 中值采样（推荐）

```python
def get_depth_median(x, y, depth_img, radius=10):
    h, w = depth_img.shape
    x1, x2 = max(0, x-radius), min(w, x+radius+1)
    y1, y2 = max(0, y-radius), min(h, y+radius+1)
    roi = depth_img[y1:y2, x1:x2]
    valid = roi[roi > 0]
    return float(np.median(valid)) if len(valid) > 20 else 0.0
```

优点：10px 半径内有 441 个点，即使有一部分空洞也能取到有效值。中值比均值更抗离群值。

### 5.6.3 分层搜索（鲁棒）

```python
def get_depth_hierarchical(x, y, depth_img):
    for r in [5, 10, 20]:
        z = get_depth_median(x, y, depth_img, r)
        if z > 0:
            return z
    return 0.0
```

90% 的情况小半径就够了，大半径兜底。

## 5.7 实验：对比固定 Z vs 深度自适应

### 实验 1：不同高度物体

准备 3 个不同高度的方块（如 5cm、3cm、1cm），分别用固定 Z 和深度自适应模式抓取，记录成功率。

**预期结果**：
- 固定 Z 模式：只对 5cm 方块成功率 > 90%
- 深度自适应：3 个方块成功率均 > 90%

### 实验 2：深度采样策略对比

在同一个物体上分别用单点、ROI 中值（r=8）、分层搜索测深度，看：
- 空洞处单点返回 0
- ROI 中值抗空洞
- 分层搜索从近到远扩展

## 5.8 本章回顾

回答开头的问题：
- 问题 1：当前用固定 z=-50，但应该用深度动态计算——不同物体厚度需要不同的下降深度
- 问题 2：深度 = 相机光心到物体表面的距离（不是到桌面）
- 问题 3：z=-50 离桌面还有 60mm，对 2mm 卡片太高；用深度自适应后 arm_z≈-103mm，能碰到

**新增关键公式**：
```
arm_z = TABLE_Z + (H_camera - depth_m) × 1000 + MARGIN_MM
```

新问题：
- 🤔 完整抓取程序怎么把深度自适应 Z 集成进去？
- 🤔 深度读取失败时怎么 fallback？

---

# 第 6 章 完整抓取项目实战

## 6.1 本章目的与目录

本章目标：
- 理解完整抓取程序 `grasp_object.py` 的代码逻辑
- 掌握抓取动作序列（逼近→下降→吸气→抬起→搬走→释放）
- 运行完整抓取演示
- 学会排查抓取失败的问题

### 在开始本章前，请思考

**问题 1**：抓取前需要哪些前置条件？
*提示：标定文件 / 机械臂驱动 / 摄像头 / 目标物体。*

**问题 2**：为什么抓取分 6 个阶段而不是一步到位？
*提示：安全感！直接冲到物体上会撞到。*

**问题 3**：抓取失败最可能的原因是什么？
*提示：标定过期（光照 / 摄像头位置变了）。*

## 6.2 抓取程序架构

抓取程序的完整节点链（`spark_carry_object.launch.py`）：

```
driver_bringup        ← 底盘 + 摄像头 + 雷达驱动
uarm_launch           ← 机械臂控制驱动
hsv_processor         ← HSV 颜色检测 + GUI 交互
grasp_object          ← 标定读取 + 坐标映射 + 抓取执行
```

### grasp_object.py 完整流程

```python
class GraspObject(Node):
    def __init__(self):
        # 1. 读取标定文件
        with open(os.environ['HOME'] + "/thefile.txt", 'r') as f:
            k1, b1, k2, b2 = map(float, f.read().split())
        
        # 2. 订阅目标中心点
        self.sub = self.create_subscription(
            PointStamped, 'target_center', self.target_center_cb, 10)
        
        # 3. 创建发布者
        self.pos_pub = self.create_publisher(
            Position, 'position_write_topic', 10)
        self.pump_pub = self.create_publisher(
            Status, 'pump_topic', 10)
    
    def target_center_cb(self, msg):
        # 收到目标像素坐标 → 执行抓取
        xc, yc = int(msg.point.x), int(msg.point.y)
        
        # 映射到机械臂坐标
        x_arm = k1 * yc + b1
        y_arm = k2 * xc + b2
        
        # 执行抓取序列
        self.grasp(x_arm, y_arm)
```

## 6.3 抓取动作序列（深度自适应版）

抓取分为 6 个阶段，其中**阶段 2 的 Z 值由深度动态计算**：

```
阶段 1：逼近上方
  pos.x = x_arm, pos.y = y_arm, pos.z = 20
  → 机械臂移动到目标正上方 20mm

阶段 2：自适应下降 🔴（替代固定 z=-50）
  depth_m = ROI中值(物体像素位置)
  grasp_z = TABLE_Z + (H_camera - depth_m)×1000 + MARGIN
  pos.z = grasp_z
  → 根据物体厚度动态决定下降深度

阶段 3：吸气吸附
  pump.status = 1
  → 吸盘启动，吸住物体

阶段 4：抬起
  pos.z = 50
  → 机械臂抬起

阶段 5：搬走
  pos.x = 150, pos.y = ±150, pos.z = 35
  → 移到放置位置

阶段 6：释放
  pos.z = -50 → pump.status = 0 → pos.z = 50
  → 下降→释放→抬起
```

完整代码：

```python
def grasp(self, x_arm, y_arm):
    pos = Position()
    pump = Status()
    
    # 阶段 1：移到目标上方
    pos.x = x_arm; pos.y = y_arm; pos.z = 20.0
    self.pos_pub.publish(pos)
    time.sleep(3)
    
    # 阶段 2：下降
    pos.z = -50.0
    self.pos_pub.publish(pos)
    time.sleep(2)
    
    # 阶段 3：吸气
    pump.status = 1
    self.pump_pub.publish(pump)
    time.sleep(2)
    
    # 阶段 4：抬起
    pos.x = 180.0; pos.y = 0.0; pos.z = 50.0
    self.pos_pub.publish(pos)
    time.sleep(3)
    
    # 阶段 5：移到放置位置（左右交替）
    if self.direction:
        pos.x = 150.0; pos.y = 150.0; pos.z = 35.0
        self.direction = False
    else:
        pos.x = 150.0; pos.y = -150.0; pos.z = 35.0
    self.pos_pub.publish(pos)
    time.sleep(3)
    
    # 阶段 6：释放
    pos.z = -50.0
    self.pos_pub.publish(pos)
    time.sleep(2)
    pump.status = 0
    self.pump_pub.publish(pump)
    time.sleep(2)
    
    # 回初始位置
    pos.x = 180.0; pos.y = 0.0; pos.z = 50.0
    self.pos_pub.publish(pos)
```

## 6.4 运行完整抓取

### 前置条件

- [ ] 已生成 `~/calibration_HSV.txt`（第 3 章）
- [ ] 已生成 `~/thefile.txt`（第 4 章）
- [ ] 机械臂上电、摄像头向下安装好
- [ ] 蓝色方块放在桌面上（机械臂可及范围内）
- [ ] 工作空间已编译

### 步骤 1：启动抓取环境

```bash
cd ~/Music/spark_humble
source install/setup.bash
ros2 launch spark_carry spark_carry_object.launch.py camera_type_tel:=d435
```

或者通过 onekey.sh：
```bash
cd ~/Music/spark_humble
./src/onekey.sh
# 选择 "让SPARK通过机械臂进行视觉抓取" → 选择 "固定位置移动"
```

### 步骤 2：HSV 调参

启动后会出现 3 个窗口：
- **Origin Image**：原始彩色画面
- **HSV Processing**：HSV 处理后的 mask 画面
- **Controls**：HSV 滑块 + SEND 按钮 + SAVE 按钮

**操作**：
1. 拖动 H/S/V 滑块，直到蓝色方块在 HSV Processing 窗口中呈现清晰的白色轮廓
2. 点击 **SEND: ON**（按钮变绿，表示目标中心点将被发送给机械臂）
3. 在 Origin Image 或 HSV Processing 窗口中**框选蓝色方块**
4. 机械臂自动执行抓取序列

### 步骤 3：观察抓取过程

机械臂会自动执行：
1. 移动到方块上方 → 下降 → 吸起方块
2. 抬起 → 移到放置位置（左右交替）→ 放下 → 返回

💡 **关键提示**：抓取成功后，再次框选方块 → 机械臂会放到另一边。

## 6.5 完整抓取演示程序

以下程序演示完整的抓取链路（**需要硬件**）：

**程序 `grasp_spark_full.py`** — Spark 完整抓取（HSV 检测 + 标定映射 + 抓取执行）

```python
#!/usr/bin/env python3
"""03-3 Spark 完整抓取链路：HSV 检测→标定映射→机械臂抓取
需要硬件：Spark 机器人 + 机械臂 + 深度摄像头 + 蓝色方块
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from swiftpro.msg import Position, Status
from geometry_msgs.msg import PointStamped
import cv2
import numpy as np
import os
import time

class SparkGrasp(Node):
    def __init__(self):
        super().__init__('spark_grasp_full')
        self.bridge = CvBridge()
        
        # 1. 加载标定系数
        try:
            with open(os.environ['HOME'] + '/thefile.txt', 'r') as f:
                k1, b1, k2, b2 = map(float, f.read().split())
            self.k1, self.b1 = k1, b1
            self.k2, self.b2 = k2, b2
            self.get_logger().info(
                f'标定系数: k1={k1:.4f} b1={b1:.4f} k2={k2:.4f} b2={b2:.4f}')
        except FileNotFoundError:
            self.get_logger().error(
                '未找到标定文件 ~/thefile.txt！请先完成第 4 章标定')
            raise
        
        # 2. 订阅摄像头
        self.rgb_sub = self.create_subscription(
            Image, 'camera/color/image_raw', self.rgb_cb, 10)
        self.rgb_image = None
        
        # 3. 机械臂发布者
        self.pos_pub = self.create_publisher(
            Position, 'position_write_topic', 10)
        self.pump_pub = self.create_publisher(
            Status, 'pump_topic', 10)
        
        # 4. 蓝色方块 HSV 阈值（从标定文件读或手动设）
        self.lower_blue = np.array([100, 80, 80])
        self.upper_blue = np.array([130, 255, 255])
        
        self.grasping = False
        self.get_logger().info('Spark 抓取节点启动 — 等待摄像头画面')
    
    def rgb_cb(self, msg):
        self.rgb_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
    
    def detect_blue_block(self):
        """HSV 检测蓝色方块 → 返回像素中心"""
        if self.rgb_image is None:
            return None
        
        hsv = cv2.cvtColor(self.rgb_image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_blue, self.upper_blue)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)
        
        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
        
        # 找最大轮廓
        c = max(contours, key=cv2.contourArea)
        if cv2.contourArea(c) < 500:
            return None
        
        M = cv2.moments(c)
        if M['m00'] == 0:
            return None
        
        cx = int(M['m10'] / M['m00'])
        cy = int(M['m01'] / M['m00'])
        return cx, cy
    
    def grasp(self, xc, yc):
        """执行抓取序列"""
        self.grasping = True
        
        # 像素 → 机械臂坐标
        x_arm = self.k1 * yc + self.b1
        y_arm = self.k2 * xc + self.b2
        
        self.get_logger().info(
            f'抓取: 像素({xc},{yc}) → 机械臂({x_arm:.1f},{y_arm:.1f})')
        
        pos = Position()
        pump = Status()
        
        # 阶段 1：上方逼近
        pos.x = float(x_arm); pos.y = float(y_arm); pos.z = 20.0
        self.pos_pub.publish(pos); time.sleep(3)
        
        # 阶段 2：下降
        pos.z = -50.0
        self.pos_pub.publish(pos); time.sleep(2)
        
        # 阶段 3：吸气
        pump.status = 1
        self.pump_pub.publish(pump); time.sleep(2)
        
        # 阶段 4：抬起
        pos.x = 180.0; pos.y = 0.0; pos.z = 50.0
        self.pos_pub.publish(pos); time.sleep(3)
        
        # 阶段 5：搬走
        pos.x = 150.0; pos.y = 150.0; pos.z = 35.0
        self.pos_pub.publish(pos); time.sleep(3)
        
        # 阶段 6：释放
        pos.z = -50.0
        self.pos_pub.publish(pos); time.sleep(2)
        pump.status = 0
        self.pump_pub.publish(pump); time.sleep(2)
        
        # 回初始位置
        pos.x = 180.0; pos.y = 0.0; pos.z = 50.0
        self.pos_pub.publish(pos); time.sleep(3)
        
        self.grasping = False
        self.get_logger().info('抓取完成！')
    
    def spin_once(self):
        rclpy.spin_once(self, timeout_sec=0.05)
        if self.rgb_image is None:
            return
        
        display = self.rgb_image.copy()
        
        # 检测蓝色方块
        result = self.detect_blue_block()
        if result and not self.grasping:
            cx, cy = result
            cv2.circle(display, (cx, cy), 8, (0, 255, 0), -1)
            cv2.putText(display, f'Blue({cx},{cy})',
                       (cx+10, cy), cv2.FONT_HERSHEY_SIMPLEX,
                       0.6, (0, 255, 0), 2)
            
            # 预览机械臂坐标
            x_arm = self.k1 * cy + self.b1
            y_arm = self.k2 * cx + self.b2
            cv2.putText(display, f'Arm({x_arm:.0f},{y_arm:.0f})',
                       (cx+10, cy+25), cv2.FONT_HERSHEY_SIMPLEX,
                       0.5, (255, 0, 0), 2)
        
        cv2.putText(display, 'Press G to grasp', (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.imshow('Spark Grasp', display)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('g') and result and not self.grasping:
            cx, cy = result
            self.grasp(cx, cy)
        elif key == 27:  # ESC
            raise KeyboardInterrupt

def main():
    rclpy.init()
    node = SparkGrasp()
    try:
        while rclpy.ok():
            node.spin_once()
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
```

运行：
```bash
# 终端 1：先启动机械臂 + 摄像头驱动
cd ~/Music/spark_humble
source install/setup.bash
ros2 launch spark_carry spark_carry_object.launch.py camera_type_tel:=d435

# 终端 2：运行抓取程序
python3 grasp_spark_full.py
# 看到蓝色方块后按 G 键抓取
```

## 6.6 常见问题排查

### 问题 1：机械臂不动

**检查**：
```bash
ros2 node list | grep -E "uarm|swiftpro"
ros2 topic list | grep position_write_topic
ros2 topic echo /position_write_topic  # 看是否有消息
```

### 问题 2：抓取位置偏移超过 2cm

**可能原因 + 解决**：
- 标定过期 → 重新跑第 4 章标定
- 光照变化 → 重新跑第 3 章 HSV 标定
- 摄像头松动 → 固定摄像头后重标

### 问题 3：检测不到蓝色方块

**检查**：
- HSV 阈值是否合适？在 `hsv_processor` GUI 中调滑块
- 方块是否在画面中？检查 Origin Image 窗口
- 摄像头曝光是否过高/过低？

### 问题 4：吸盘吸不起来

**检查**：
- 气泵是否正常工作？（听是否有吸气声）
- `pump_topic` 是否正确发送？
- 下降高度是否足够？（检查 `pos.z = -50.0` 是否够深）

## 6.7 本章回顾

回答开头的问题：
- 问题 1：标定文件 + 机械臂驱动 + 摄像头 + 目标物体
- 问题 2：先逼近上方 → 下降 → 吸气 → 抬起 → 搬走 → 释放，分阶段保证安全
- 问题 3：标定过期（光照/摄像头位置改变）→ 重标

---

## 实践程序总结

本课程提供 5 个程序：

### 程序 1：`grasp_regression_demo.py`（无需硬件）

用 20 组模拟数据验证线性回归原理。理解 k₁, b₁, k₂, b₂ 的来源。

**运行**：
```bash
cd ~/Music/spark_humble
source install/setup.bash
ros2 run vision_basics grasp_regression_demo
```

### 程序 2：`grasp_depth_check.py`（需深度相机，不需机械臂）

验证深度相机是否能检测到桌面上的物体。演示 ROI 中值采样。

**运行**：
```bash
# 终端 1：启动摄像头
ros2 launch spark_bringup driver_bringup.launch.py camera_type_tel:=d435 enable_arm_tel:=false

# 终端 2：运行验证
ros2 run vision_basics grasp_depth_check
```

### 程序 3：`grasp_spark_depth.py` 🔴（需全硬件，本课核心）

**深度自适应抓取**：HSV 检测 → 深度 Z → 标定映射 → 动态抓取。替代原来的固定 Z 方案，根据物体真实厚度控制下降深度。

**运行**：
```bash
# 终端 1：启动机械臂 + 摄像头
ros2 launch spark_carry spark_carry_object.launch.py camera_type_tel:=d435

# 终端 2：运行深度自适应抓取
ros2 run vision_basics grasp_spark_depth.py
# 画面显示深度值和计算的 arm_z，按 G 键抓取
```

### 程序 4：`grasp_spark_full.py`（需全硬件，固定 Z 版本）

完整抓取链路（固定 Z 模式），用于与程序 3 对比实验。

**运行**：
```bash
ros2 run vision_basics grasp_spark_full.py
```

### 程序 5：Spark 标定 + 抓取 GUI（交互式）

使用 Spark 自带的 `hsv_processor.py` + `grasp_object.py`，通过 GUI 进行标定和抓取（固定 Z）。

**运行**：
```bash
ros2 launch spark_carry spark_carry_object.launch.py camera_type_tel:=d435
```

---

## 学完本课回顾

### 你应该掌握的核心概念

1. **Spark 手眼标定原理**：20 点线性回归替代传统棋盘格标定
2. **HSV 颜色标定**：现场采集、均值计算、阈值保存
3. **像素→机械臂映射**：k₁·yc + b₁ / k₂·xc + b₂
4. **深度→机械臂 Z 自适应**：`arm_z = TABLE_Z + (H_camera - depth) × 1000 + MARGIN`
5. **抓取动作序列**：逼近→自适应下降→吸气→抬起→搬走→释放
6. **深度采样策略**：单点 / ROI 中值 / 分层搜索

### 标定文件清单

| 文件 | 内容 | 生成方式 |
|------|------|----------|
| `~/calibration_HSV.txt` | 橙色标记 HSV 阈值 | 第 3 章 HSV 标定 |
| `~/thefile.txt` | 像素→臂 X/Y 映射系数 | 第 4 章 20 点回归 |
| `~/camera_height.txt` | 摄像头离桌面高度 H_camera | 第 5.4 节 Z 轴标定 |

### 后续学习建议

- 学完本课后，可以继续 04-1 YOLO 目标检测，用深度学习替代 HSV 颜色识别
- 建议反复练习标定→抓取流程，掌握不同光照下的调参技巧
- 理解标定是"一次性成本"——环境不变可以复用

---

*课程制作：Spark 实践版 v2*
*更新日期：2026 年 7 月*
*下一课：04-1 YOLO 目标检测（深度学习）*
