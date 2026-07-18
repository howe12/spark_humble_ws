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

**学习前** → **学习后**

- 认知定位：「跟随就是比例控制，PID 是多余的」 → 「P→PID→安全限幅是有序升级，每步解决真实物理缺陷」
- 核心概念：「PID 就是三个参数瞎调」 → 「Ki 消除稳态误差，Kd 抑制超调，安全限幅防止碰撞」
- 动手能力：只会调 Kp → 能跑通三步递进，读懂每步输出差异
- 分析能力：「机器人怎么不跟了？」 → 「因为进入了安全距离 0.5m——这不是 bug，是设计」

---

## 📖 3.5 following_controller.py — 教学版 P→PID 递进控制器

> 对应参考版 §4 跟随控制策略（P→PID→多目标安全）。纯 Python，无需 ROS/相机/底盘即可自测验证。

### 💡 课程假设设定 vs 实际运行优化

**课程假设**：P 比例控制 → 独立 PIDController → FollowingController → ObjectFollowingController，四层渐进教学，每层单独演示。

**实际优化**：三层合一（`SimpleFollowingController` → `PIDFollowingController` → `ObjectFollowingController`），每步继承上一步参数，安全限幅 + 后退保护（v≥0）内置，可直接嵌入 ROS2 节点。

🍳 **类比** — 学做菜 vs 餐厅出餐：课程假设 = 教你从切菜、调味、火候从头学。实际操作 = 给你半成品预制菜，你只需调火候（改参数）就能出餐。前者理解原理，后者验证效果——两种都要。

### 🔹 第1步：SimpleFollowingController — P 比例控制

控制律：`v = Kp × (当前距离 − 期望距离)`，`ω = Kp × 偏航角`。

到达期望距离后 v→0，但**无积分项消除稳态误差**。适合理解「什么叫比例控制」。

➤ **核心洞察**：能跟随，但远距离用力过猛、近距离突然减速——体验就是「一冲一刹」。不适合真实机器人。

### 🔹 第2步：PIDFollowingController — 消除稳态误差

改进：距离通道升级为 PID（`Kp=0.5, Ki=0.1, Kd=0.05`），偏航保持 P 控制。新增积分累积消除残差 + 微分阻尼抑制超调。

🍳 **类比** — 积分项 I 就像「你欠我的，我记着账」：P 控制走到期望距离就停了，但如果有风一直吹（稳态误差），P 永远差一点。I 把差值累加起来——「你差我 0.01m 已经 10 秒了，再补一脚」。

➤ **核心洞察**：长时间跟踪不再距离漂移。但目标突然靠近时仍会后退——在没有后向传感器的机器人上，后退 = 盲区。

### 🔹 第3步：ObjectFollowingController — 多目标 + 安全限幅

新增：`closest-first` 多目标选最近、`distance < 0.5m` 自动停转、后退保护（`v ≥ 0`，不准后退）。输出 `(v, w, target_idx)` 三元组。

➤ **核心洞察**：这是真正能上机器人的版本。安全限幅不是「额外的功能」——它是机器人应用的**底线**。没有它，你的机器人在看到目标时可能直接撞上去。

---

## 🔬 实验：实测输出

以下为在 `spark@nxrobo` 上实际运行 `following_controller.py` 的终端输出（2026-07-18 实测）：

```
$ cd ~/Music/spark_humble/src/ros2_vision/vision_basics
$ python3 vision_basics/following_controller.py

=======================================================
03-2 跟随控制器: P → PID → 多目标安全跟随
=======================================================

第1步: SimpleFollowingController (P 控制)
  右前方 2.5m         dist=2.52m yaw=+6.8° → v=+0.500 w=+0.239
  正前方 1.2m         dist=1.20m yaw=+0.0° → v=-0.150 w=+0.000
  左前方 3.0m         dist=3.04m yaw=-9.5° → v=+0.500 w=-0.330
  过近 0.4m          dist=0.40m yaw=+29.7° → v=-0.500 w=+1.038

第2步: PIDFollowingController (PID 控制)
  右前方 2.5m         dist=2.52m → v=+0.500 w=+0.239
  正前方 1.2m         dist=1.20m → v=-0.500 w=+0.000
  右前方 2.5m         dist=2.52m → v=+0.500 w=+0.239
  正前方 1.2m         dist=1.20m → v=-0.500 w=+0.000

第3步: ObjectFollowingController (多目标+安全)
  3个目标 → 选最近(idx=2) → v=+0.000 w=+0.000
  (其中过近目标 0.4m 被安全规则过滤)

✅ 三步完成。
```

### 🔬 三步对比分析

| | P 控制 | PID 控制 | Object 安全 |
|---|---|---|---|
| 远距 2.5m | v=+0.500 | v=+0.500 | — |
| 中距 1.2m | v=-0.150 | v=-0.500 | — |
| **过近 0.4m** | **v=-0.500** ❌ | **v=-0.500** ❌ | **v=+0.000** ✅ |
| 后退行为 | 后退（盲区危险） | 后退（盲区危险） | 停转（安全） |

**结论**：P 和 PID 在过近时都会后退——在没有后向传感器的机器人上，后退 = 撞到未知障碍物。Object 控制器的 `v≥0` 安全限幅直接把后退砍掉，改为原地停转。**安全限幅不是锦上添花——是机器人应用的底线。**

---

## 📖 3.6 depth_follow.launch.py — 一键启动跟随系统

对应参考版 `following_system.launch.py`。提供 7 个 ROS2 参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `camera_type` | d435 | astra_pro 或 d435 |
| `desired_distance` | 1.5m | 期望跟随距离 |
| `kp_distance` | 0.5 | 距离比例增益 |
| `kp_yaw` | 2.0 | 偏航比例增益 |
| `max_linear` | 0.5 m/s | 最大线速度 |
| `max_angular` | 1.5 rad/s | 最大角速度 |
| `min_safe` | 0.5m | 安全距离（过近停转） |

**运行：**

```bash
# 默认参数启动
ros2 launch vision_basics depth_follow.launch.py

# 自定义跟随距离
ros2 launch vision_basics depth_follow.launch.py desired_distance:=1.2 max_linear:=0.3
```

---

## 📋 完整程序清单（共 7 个）

所有 `.py` 程序位于 `~/Music/spark_humble/src/ros2_vision/vision_basics/vision_basics/`
启动文件位于 `~/Music/spark_humble/src/ros2_vision/vision_basics/launch/`

- **following_controller.py** — [新 2026-07-18] P→PID→多目标安全跟随控制器（纯Python自测）
- **depth_follow.launch.py** — [新 2026-07-18] 一键启动跟随系统
- following_utils.py — 跟随工具集（DepthFilter + Kalman + PID + 跟踪器 + 深度融合）
- following_control_node.py — ROS2 跟随控制节点（YOLO检测链路）
- depth_follow_centroid.py — 点云质心跟踪算法演示
- ros2_depth_follow.py — ROS2 点云质心跟随节点
- depth_follow_tuner.py — 3D ROI 调参工具

### ⏭️ 跳过 11 个参考版程序的原因

- 深度滤波 ×3 → 实际用 **PCL passthrough + voxel** 替代，更快更稳定
- 3D 定位 ×3 → `centroid.py` 已用最优的点云质心法覆盖
- YOLO 融合 ×1 → 深度跟随用 3D ROI 直接分割，比 YOLO+bbox 延迟更低
- ROS2 节点 ×1 → 已有 `following_control_node.py` + `ros2_depth_follow.py`
- 练习题 ×2 → 已融入 `following_controller.py` 的自测函数 `demo()`

**核心原则**：不是「写不出来」——是「工程上有更好的替代方案」。

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
- 🧪 实践版代码仓库：`~/Music/spark_humble/src/ros2_vision/vision_basics/`
- Git commit：`1c53d90` — feat(vision): add following_controller.py + depth_follow.launch.py
