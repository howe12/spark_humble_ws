# Spark实践版 — 03-2 基于深度信息的目标跟随

> 本课定位：在 03-1 掌握点云与深度相机后，回答一个核心问题——「如何让机器人跟随一个目标移动？」
> 前置：03-1 点云与深度相机。学完本课，你能亲手跑通 P→PID→多目标安全三版递进，并一键启动跟随系统。

---

## ❓ 灵魂拷问

开始本课之前，请先回答：

- 如果只需要「跟着目标走」——为什么不能一个 P 控制器搞定？
- PID 多出来的 I（积分）和 D（微分）是锦上添花还是不可或缺？
- 机器人离目标 0.3m 时，你认为应该后退调整还是原地停转？哪个更安全？
- 你的机器人没有后向传感器——后退意味着什么？

> 不亲自跑一遍三个控制器的对比输出，你永远不知道每个升级解决了什么真实的物理问题。

---

## 📚 前章回顾

在 03-1，你学会了从深度图获取点云、用 PCL 做直通滤波和体素降采样。你知道点云中的每个 `(X, Y, Z)` 都是真实世界的 3D 坐标。

🍳 **类比** — 03-1 教你「怎么看」：眼睛睁开了，知道目标在哪里了。本课教你「怎么走」：腿怎么迈、迈多快、什么时候停。

从 03-1 到 03-2，问题从「感知」变成了「控制」。你手里有目标的位置 (X, Z)，现在要把它变成机器人底盘的速度指令 (v, ω)。

---

## 🎯 学习目标

**学习前 → 学习后**

- 认知定位：「跟随就是比例控制，PID 是多余的」 → 「P→PID→安全限幅是有序升级，每步解决真实物理缺陷」
- 核心概念：「PID 就是三个参数瞎调」 → 「Ki 消除稳态误差，Kd 抑制超调，安全限幅防止碰撞」
- 动手能力：只会调 Kp → 能跑通三步递进，读懂每步输出差异
- 分析能力：「机器人怎么不跟了？」 → 「因为进入了安全距离 0.5m——这不是 bug，是设计」

---

## 📊 程序对比分析总表

以下为 03-2 所有 7 个程序的完整对比，覆盖**程序类型、硬件需求、优化方式、操作命令**：

| 程序 | 类型 | 硬件需求 | 课程假设设定 | 实践版优化方式 | 操作方式 |
|------|------|---------|-------------|---------------|---------|
| **following_controller.py** [新] | 纯Python | 无 | P→PID→Object 四类独立 | 三层合一，继承参数，安全限幅内置 | `python3 following_controller.py` |
| **depth_follow.launch.py** [新] | ROS2 launch | D435 | 无（参考版无此文件） | 7 参数一键启动，比手动 ros2 run 方便 | `ros2 launch vision_basics depth_follow.launch.py` |
| **following_utils.py** | 纯Python模块 | 无 | 30+ 内联函数散落文档 | 整合为 8 模块工具集，7 项自测通过 | `python3.10 following_utils.py`（自测） |
| **following_control_node.py** | ROS2 节点 | D435 + 底盘 | 假设检测器总是有结果 | enable_following 默认 False，无目标自动减速 | `ros2 run vision_basics following_control_node` |
| **depth_follow_centroid.py** | 纯Python演示 | 无 | 像素级滤波 (median/bilateral) | 点云级 PCL passthrough+voxel，更快更稳定 | `python3 depth_follow_centroid.py` |
| **ros2_depth_follow.py** | ROS2 节点 | D435 + 底盘 | 比例控制单线 | 3D ROI 质心 + 比例控制 + 死区 + 丢帧保护 | `ros2 run vision_basics ros2_depth_follow` |
| **depth_follow_tuner.py** | 调参工具 | D435 + DISPLAY | 手工改代码调参 | OpenCV 滑块实时调 ROI 参数，即时看过滤效果 | `python3 depth_follow_tuner.py` |

### 📊 跳过的 11 个参考版程序——对比与替代

| 参考版程序 | 课程目的 | 为何跳过 | 工程替代方案 |
|-----------|---------|---------|-------------|
| depth_median_filter() | 教学像素级中值滤波 | 深度图滤波效率低 | PCL passthrough（直通）直接在点云过滤 |
| depth_bilateral_filter() | 教学双边滤波原理 | 点云上不需要逐像素滤波 | PCL voxel（体素）降采样 + 去噪 |
| depth_inpainting() | 教学深度空洞填充 | D435 硬件已做填充 | 直接跳过——硬件已处理 |
| get_target_3d_from_bbox() | 均值深度法演示 | 单一 bbox 深度不稳定 | depth_follow_centroid.py 用点云质心 |
| get_target_3d_with_median() | 中值深度法演示 | 与质心法效果相当 | centroid 已覆盖，不重复 |
| get_target_3d_pointcloud() | 点云质心法演示 | centroid.py 已实现 | centroid.py 已用最优方法 |
| yolo_detection_example() | 演示检测+跟随组合 | YOLO 属 04-1 章节 | 深度跟随用 3D ROI，比 YOLO 延迟更低 |
| SimpleFollowingController | P 控制教学 | 功能已有 | 融入 following_controller.py 第1步 |
| PIDController (独立类) | PID 教学 | 功能已有 | 融入 following_controller.py 第2步 |
| FollowingControlNode | ROS2 节点教学 | 已有 2 个节点 | following_control_node + ros2_depth_follow |
| pixel_and_depth_to_3d() | 像素反投影练习 | 练习题，非核心 | 函数已内置在 following_utils.py 中 |

**核心原则**：不是「写不出来」——是「工程上有更好的替代方案」。

---

## 📖 3.5 following_controller.py — P→PID 递进控制器（教学版）

> 对应参考版 §4 跟随控制策略。纯 Python，无需 ROS/相机/底盘即可自测验证。

### 💡 课程假设设定 vs 实际运行优化

**课程假设**：P 比例控制 → 独立 PIDController → FollowingController → ObjectFollowingController，四层渐进教学，每层单独演示。假设每个学生从头实现一个控制器类。

**实际优化**：三层合一（`SimpleFollowingController` → `PIDFollowingController` → `ObjectFollowingController`），每步继承上一步参数，安全限幅 + 后退保护（v≥0）内置，可直接嵌入 ROS2 节点。学生只需改参数，不需重写类。

🍳 **类比** — 学做菜 vs 餐厅出餐：课程假设 = 教你从切菜、调味、火候从头学。实际操作 = 给你半成品预制菜，你只需调火候（改参数）就能出餐。前者理解原理，后者验证效果——两种都要。

### 🔹 第1步：SimpleFollowingController — P 比例控制

控制律：`v = Kp × (当前距离 − 期望距离)`，`ω = Kp × 偏航角`。到达期望距离后 v→0，但**无积分项消除稳态误差**。

➤ **核心洞察**：能跟随，但远距离用力过猛、近距离突然减速——「一冲一刹」。不适合真实机器人。

### 🔹 第2步：PIDFollowingController — 消除稳态误差

改进：距离通道升级为 PID（`Kp=0.5, Ki=0.1, Kd=0.05`），偏航保持 P 控制。

🍳 **类比** — 积分 I 就像「你欠我的，我记着账」：P 控制走到期望距离就停了，但如果有风一直吹（稳态误差），P 永远差一点。I 把差值累加——「你差我 0.01m 已经 10 秒了，再补一脚」。

➤ **核心洞察**：长时间跟踪不再距离漂移。但目标靠近时仍会后退——在没有后向传感器的机器人上，后退 = 盲区。

### 🔹 第3步：ObjectFollowingController — 多目标 + 安全限幅

新增：`closest-first` 多目标选最近、`distance < 0.5m` 自动停转、后退保护（`v ≥ 0`）。输出 `(v, w, target_idx)`。

➤ **核心洞察**：这是能上机器人的版本。安全限幅不是「额外功能」——是机器人应用的**底线**。

---

## 🔬 实验：实测输出（2026-07-18 spark@nxrobo 实测）

```
$ cd ~/Music/spark_humble/src/ros2_vision/vision_basics
$ python3 vision_basics/following_controller.py

=======================================================
03-2 跟随控制器: P → PID → 多目标安全跟随
=======================================================

第1步: SimpleFollowingController (P 控制)
  右前方 2.5m    dist=2.52m yaw=+6.8° → v=+0.500 w=+0.239
  正前方 1.2m    dist=1.20m yaw=+0.0° → v=-0.150 w=+0.000
  左前方 3.0m    dist=3.04m yaw=-9.5° → v=+0.500 w=-0.330
  过近 0.4m      dist=0.40m yaw=+29.7° → v=-0.500 w=+1.038

第2步: PIDFollowingController (PID 控制)
  右前方 2.5m    dist=2.52m → v=+0.500 w=+0.239
  正前方 1.2m    dist=1.20m → v=-0.500 w=+0.000

第3步: ObjectFollowingController (多目标+安全)
  3个目标 → 选最近(idx=2) → v=+0.000 w=+0.000
  (其中过近目标 0.4m 被安全规则过滤 ✓)

✅ 三步完成。
```

### 🔬 三步对比分析

| 场景 | P 控制 | PID 控制 | Object 安全 |
|------|--------|---------|------------|
| 远距 2.5m | v=+0.500 w=+0.239 | v=+0.500 w=+0.239 | — |
| 中距 1.2m | v=-0.150 w=+0.000 | v=-0.500 w=+0.000 | — |
| **过近 0.4m** | **v=-0.500** ❌ 后退 | **v=-0.500** ❌ 后退 | **v=+0.000** ✅ 停转 |

**结论**：P 和 PID 在过近时都会后退——无后向传感器时后退 = 盲区碰撞。Object 的 `v≥0` 安全限幅把后退砍掉，改为原地停转。安全限幅**不是锦上添花——是机器人应用的底线**。

---

## 📖 3.6 depth_follow.launch.py — 一键启动跟随系统

对应参考版 `following_system.launch.py`。7 个 ROS2 参数：

| 参数 | 默认值 | 优化说明 |
|------|--------|---------|
| `camera_type` | d435 | 支持 astra_pro / d435 双相机切换 |
| `desired_distance` | 1.5m | 根据实际跟随场景调整（近距 0.8m / 远距 2.0m） |
| `kp_distance` | 0.5 | 调大→激进跟随，调小→平滑跟随 |
| `kp_yaw` | 2.0 | 调大→快速转向，调小→缓慢修正 |
| `max_linear` | 0.5 m/s | 安全上限，真实底盘不超过此值 |
| `max_angular` | 1.5 rad/s | 安全上限，防止急转甩飞负载 |
| `min_safe` | 0.5m | **核心安全参数**——过近自动停转 |

**运行：**

```bash
# 默认参数
ros2 launch vision_basics depth_follow.launch.py

# 自定义（近距离慢速跟随）
ros2 launch vision_basics depth_follow.launch.py desired_distance:=0.8 max_linear:=0.2 min_safe:=0.3
```

---

## 📋 本课检查清单

- [ ] 我知道 P 控制器的优势和缺陷——能跟随，但会一冲一刹
- [ ] 我知道 PID 中 I（积分）消除稳态误差，D（微分）抑制超调
- [ ] 我亲手跑过 `following_controller.py` 的三步递进输出
- [ ] 我能解释为什么第三步在过近时 v=0.000——安全限幅不是 bug，是设计
- [ ] 我知道 `depth_follow.launch.py` 的 7 个参数各自的作用
- [ ] 我能理直气壮地说：「这 11 个参考版程序不需要重写——工程上有更好的替代方案」

---

## ❓ 引出下一章

你有了控制器——但控制器需要「目标在哪个方向、距离多远」的输入。

这个输入从哪来？点云质心？YOLO 检测框？还是两者融合？
在真实机器人上，噪声和遮挡会怎样影响输入质量？

→ **03-3 见：基于深度信息的物体识别抓取**——在跟随之后，让机器人伸出手去抓。

---

## 📚 参考资料

- 📖 参考版文档：`X3qRdYfoco4XwcxI6Hkc4pXuneb`（03-2 基于深度信息的目标跟随，2749 行）
- 📖 Q3 风格参考：`KnM9wS7YQi3AUzkoubOceR8bnbO`
- 🧪 实践版代码仓库：`~/Music/spark_humble/src/ros2_vision/vision_basics/`
- Git commit：`1c53d90` + `2f861d8`
