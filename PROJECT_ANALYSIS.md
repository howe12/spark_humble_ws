# Spark Humble 项目分析与改进路线图

> 本文档汇总对 `/home/spark/Music/spark_humble`（NXROBO Spark 机器人 ROS2 Humble 工程）的代码审查结果，按优先级组织，作为后续迭代的路线图。
>
> **最近更新**：2026-06-13  
> **仓库**：`git@github.com:howe12/spark_humble_ws.git`（私有）  
> **总状态**：5 项修复已完成 ✅ ｜ 18 项待办（按优先级 P1→P4 排列）

---

## 一、项目速览

### 工程结构

```
spark_humble/
├── src/
│   ├── onekey.sh                          # 一键启动管理脚本（用户入口）
│   ├── spark/                             # 核心层
│   │   ├── spark_bringup/                 # ★ 公共底座 driver_bringup.launch.py
│   │   ├── spark_description/             # URDF 机器人模型
│   │   ├── spark_teleop/                  # 键盘控制节点
│   │   ├── spark_common_interfaces/       # 自定义 msg/srv
│   │   ├── velocity_smoother/             # 速度平滑（实际未使用，见 P3-A）
│   │   ├── serial-ros2/                   # 串口库
│   │   ├── executive_smach/               # SMACH 状态机（未在 onekey 调用）
│   │   └── spark_test/                    # 老化测试
│   ├── spark_app/                         # 应用层
│   │   ├── spark_teleop*, spark_follower, spark_carry
│   │   ├── spark_navigation2, spark_rtab_map, spark_slam
│   │   ├── spark_yolov8, spark_voice/voskros
│   │   ├── spark_face_recognition, spark_handpose, spark_torch
│   │   ├── ros2-tensorflow, spark_object_detector (yolov8_object_detector) ⚠️
│   │   └── ...
│   └── spark_driver/                      # 驱动层
│       ├── base/spark_base                # 底盘
│       ├── camera/                        # 摄像头 (含 realsense-ros)
│       ├── lidar/                         # 雷达 (含 ydlidar_ros2_driver)
│       ├── arm/uArm, arm/maxarm ⚠️       # 机械臂 (maxarm 未被使用)
│       ├── my_pkg ⚠️ (CATKIN_IGNOREx)    # 测试包，已禁用
│       └── test_pkg ⚠️                   # 空壳
```

### 菜单映射（onekey.sh）

| 菜单 | 功能 | 实际 launch |
|---|---|---|
| 1 | 键盘遥控 | `spark_teleop/teleop.launch.py` |
| 2 | 跟随 | `spark_follower/...` |
| 3 | 2D 建图 | `spark_slam_transfer/start_build_map_*.launch.py` |
| 4 | 3D 建图 | `spark_rtab_map/start_rtabmap_rgbd_sync.launch.py` |
| 5 | 2D 导航 | `spark_navigation2/start_spark_navigation2.launch.py` |
| 6 | 3D 导航 | `spark_rtab_map/start_rtabmap_rgbd_sync.launch.py` (localization=true) |
| 7 | 摄像头-机械臂标定 | `spark_carry/spark_carry_cal.launch.py` |
| 8 | 视觉抓取 | `spark_carry/spark_carry_object*.launch.py` |
| 9 | 深度学习 | yolov8_object / yolov8_pose |
| 10 | 语音控制 | `spark_voice/vosk_nav.launch.py` |

---

## 二、P0 — Namespace 与多机协同（已完成 ✅）

> 目标：让多台 Spark 能在同一 ROS2 环境中共存，互不干扰。

### ✅ 改动清单（5 个文件，+50/-17 行）

| 文件 | 改动 |
|---|---|
| `src/spark_app/spark_follower/launch/spark_follower.launch.py` | 修字面量 bug：`namespace='namespace'` → `namespace=namespace` |
| `src/spark_driver/base/spark_base/launch/spark_base.launch.py` | 新增 `frame_prefix` launch arg；解开 tf remap；透传 frame_prefix 参数 |
| `src/spark_driver/base/spark_base/src/spark_base_driver.cpp` | 新增 `frame_prefix` 参数声明，给 odom/base frame 自动加前缀（防重复） |
| `src/spark/spark_description/launch/spark_description.launch.py` | 新增 `frame_prefix` launch arg；传给 `robot_state_publisher`；解开 tf remap |
| `src/spark/spark_bringup/launch/driver_bringup.launch.py` | 新增 `frame_prefix` launch arg；透传给下层 |

### ✅ 验证状态

- ✅ colcon 增量编译通过（spark_base / spark_bringup / spark_description / spark_follower 4 个包）
- ✅ 单机器人模式 dry-run：节点走全局命名空间，行为不变
- ✅ 多机器人模式 dry-run：节点全部进入 `/robot1/`，底盘/雷达/相机都成功打开设备

### ⚠️ 已知遗留（已记录到 P1）

跑多机时这几个还会打架：
1. 相机/雷达共享：`start_camera.launch.py` 用 `lsusb` 自动选，多机会撞
2. 串口硬编码：默认 `/dev/sparkBase`，多机必须显式传
3. `/opt/lidar.txt` 全局共享
4. `PushRosNamespace` 仍未使用

---

## 三、P1 — Namespace 架构补全（待办）

> 在 P0 基础上做完整的 namespace 机制，支持硬件级隔离。

### P1-A：补齐 `use_namespace` 布尔开关
- **状态**：⬜ 待办
- **原因**：当前只有 `namespace=''` 字符串开关，无法区分"显式空 namespace"和"不用 namespace"
- **参考**：nav2_bringup 的 `use_namespace=True/False` + `namespace='robot1'` 模式
- **影响文件**：`driver_bringup.launch.py` + 所有应用 launch（约 15 个）

### P1-B：用 `PushRosNamespace` 包裹子 launch
- **状态**：⬜ 待办
- **原因**：7 个文件 import 了 `PushRosNamespace` 但几乎没用；当前依赖每个 Node 自己传 `namespace=`，子 launch 没声明 namespace 的节点会漏
- **方案**：在 `driver_bringup` / `start_camera` / `start_lidar` 入口用 `PushRosNamespace` 包整组 action
- **影响文件**：`driver_bringup.launch.py`, `start_camera.launch.py`, `start_lidar.launch.py`

### P1-C：硬件设备路径参数化
- **状态**：⬜ 待办
- **原因**：
  - 底盘：`serial_port` 默认 `/dev/sparkBase`，多机必然冲突
  - 摄像头：`start_camera.launch.py` 用 `lsusb` 自动选，无法指定
  - 雷达：`start_lidar.launch.py` 读 `/opt/lidar.txt` 全局共享
  - 标定文件：`~/.ros/camera_info` 多机共享
- **方案**：
  - 摄像头：加 `camera_serial_no` 参数，传给 `realsense2_camera` 节点
  - 雷达：加 `lidar_usb_port` 参数（基于 USB 端口路径）
  - 底盘：`serial_port` 强制从参数传入（默认 `/dev/sparkBase` 保持兼容）
- **影响文件**：`start_camera.launch.py`, `start_lidar.launch.py`, `spark_base.launch.py`

### P1-D：修复 `rtabmap.launch.py` namespace 默认值
- **状态**：⬜ 待办
- **位置**：`src/spark_app/spark_rtab_map/launch/rtabmap.launch.py:419`
- **问题**：`DeclareLaunchArgument('namespace', default_value='rtabmap', ...)` —— 默认值错误，应该为 `''`
- **方案**：直接改成 `''`，或者写一个 `spark_rtabmap.launch.py` 包装层

### P1-E：把 `frame_prefix` 透传到相机/雷达 launch
- **状态**：⬜ 待办
- **原因**：当前 `frame_prefix` 只传到 robot_state_publisher 和 spark_base，相机和雷达的静态 TF（如 `camera_link`）也需要 frame prefix 才能在多机时隔离
- **方案**：在 `start_camera.launch.py` / `start_lidar.launch.py` 加 `frame_prefix` 参数透传
- **影响文件**：`start_camera.launch.py`, `start_lidar.launch.py`, 各相机/雷达具体 launch

---

## 四、P2 — 死代码清理（待办）

> 删除未使用或重复的代码，减少认知负担。

### P2-A：清理 `spark_navigation2/launch/` 里的历史 launch
- **状态**：⬜ 待办
- **死代码清单**（共 11 个文件，实际只用 `start_spark_navigation2.launch.py`）：
  ```
  bringupn_launch.py                              ❌
  multi_sparks.launch.py                          ❌ (从 nav2 拷的空壳，引用 turtlebot3)
  nav2_bringup.launch.py                          ❌
  nav2_localization_launch.py                     ❌
  nav2_navigation.launch.py                       ❌
  navigation2.launch.py                           ❌
  navigation2.launch_test.py                      ❌
  navigation2o.launch.py                          ❌
  start_spark_navigation2old.launch.py            ❌
  start_spark_navigation2_test.launch.py          ❌
  start_spark_navigation2.launch.py               ✅ 保留
  ```

### P2-B：清理空壳 / 未使用包
- **状态**：⬜ 待办
- **清单**：
  - `src/spark_driver/arm/maxarm/` + `maxarm_msg/` —— 不在 onekey 里调用
  - `src/spark_driver/my_pkg/` —— 已被 `CATKIN_IGNOREx` 禁用（说明作者已决定弃用）
  - `src/spark_driver/test_pkg/` —— 空壳
  - `src/spark_app/spark_object_detector/yolov8_object_detector/` —— 疑似被 `spark_yolov8` 取代（需确认）
  - `src/spark_app/spark_handpose/` —— 不在 onekey 里调用（需确认是否独立项目）

### P2-C：清理带空格的备份文件
- **状态**：⬜ 待办
- **清单**：
  ```
  src/spark/spark_description/urdf/spark_340.urdf copy.xacro
  src/spark_app/spark_navigation2/param/spark_navigation copy.yaml
  src/spark_app/spark_follower/src/spark_follower copy.cpp
  ```
- **风险**：带空格的路径在 CMake / install 阶段容易炸

### P2-D：清理 `spark_description` 里的备份 launch
- **状态**：⬜ 待办
- **清单**：
  ```
  src/spark/spark_description/launch/spark_description_old.launch.py
  src/spark/spark_description/launch/launch_utils.py        (需确认是否真用)
  src/spark/spark_description/launch/spark_xacro.py         (需确认是否真用)
  ```

### P2-E：清理 `spark_navigation2/param/` 里的备份
- **状态**：⬜ 待办
- **清单**：
  ```
  spark_navigation copy.yaml
  nav2_multirobot_params_1.yaml   (P2 阶段暂留，P3 阶段用作多机参数模板)
  ```

### P2-F：`doc/` 下的大体积 PDF
- **状态**：⬜ 待办（看用户决定）
- **清单**：`doc/标定棋盘9x7 20x20mm.pdf` —— 如果 README 里不引用，没必要入库

---

## 五、P3 — 架构优化（待办）

> 提升代码可维护性、可扩展性。

### P3-A：抽公共 launch 参数模块
- **状态**：⬜ 待办
- **问题**：每个应用 launch 都重复声明 5 个相同参数（`camera_type_tel`, `lidar_type_tel`, `enable_arm_tel`, `arm_type_tel`, `namespace`）
- **方案**：在 `spark_bringup` 包内新建 `launch/common.py`，导出 `declare_common_arguments()` 函数，所有应用 launch `from spark_bringup.common import declare_common_arguments`
- **影响文件**：~15 个应用 launch
- **收益**：未来改默认参数只改一处

### P3-B：重构 onekey.sh UI 模板
- **状态**：⬜ 待办
- **问题**：`let_robot_go` / `people_follow` / `voice_nav` 等函数都是"打印提示 + 按回车 + print_command + ros2 launch"四步，大量复制粘贴
- **方案**：抽 `launch_app()` 函数，传入标题/提示/launch 命令
- **影响文件**：`src/onekey.sh`
- **收益**：代码量预计能减 30-50%

### P3-C：SLAM 包结构优化
- **状态**：⬜ 待办
- **问题**：`spark_slam/{slam_gmapping, spark_cartographer, spark_slam_transfer}` 三层，但所有 launch 都在 transfer 里
- **方案**：合并三个包到 `spark_slam_transfer`，把 `slam_gmapping/` 和 `spark_cartographer/` 作为子模块或直接删掉（它们的实现都是从标准 ROS 包继承的）

### P3-D：自定义消息统一
- **状态**：⬜ 待办（优先级低）
- **问题**：`spark_common_interfaces` 里的 `Classification2D` 用了 `vision_msgs`，其他模块用的是自定义的 `InferenceResult`，两种风格混用
- **方案**：要么全用 `vision_msgs`，要么全用自定义

### P3-E：`velocity_smoother` 是否保留
- **状态**：⬜ 待办（先确认）
- **问题**：被 `nav2_navigation.launch.py` 引用，但 `nav2_navigation.launch.py` 是 P2-A 要删的死代码
- **方案**：确认 `velocity_smoother` 是否真有用，没有就一并删

### P3-F：升级 `multi_sparks.launch.py` 真正支持 Spark
- **状态**：⬜ 待办
- **问题**：当前是从 nav2 拷的空壳，引用 turtlebot3 的 `tb3_simulation_launch.py`，跟 Spark 毫无关系
- **方案**：基于 `ParseMultiRobotPose`，对每台 robot 展开一组 `driver_bringup + 应用层`

---

## 六、P4 — 工程质量（待办）

> 长期改进项。

### P4-A：python 节点依赖管理
- **状态**：⬜ 待办
- **问题**：`spark_carry/spark_carry/setup.py` 依赖没列全；节点通过手动 sys.path.append 找模块
- **方案**：用 ament_python 规范依赖，setup.py 列出所有 `install_requires`

### P4-B：CI / 自动化
- **状态**：⬜ 待办
- **方案**：
  - 加 GitHub Actions：每次 push 跑 `colcon build` + 启动语法检查
  - 加 pre-commit：Python black/isort、CMake format

### P4-C：文档完善
- **状态**：⬜ 待办
- **方案**：
  - 每个包加 `README.md`，说明用途/参数/依赖
  - 顶层 README 加架构图（本文档可作为素材）
  - onekey.sh 加 README 说明每个菜单的真实调用链

### P4-D：日志规范
- **状态**：⬜ 待办
- **问题**：各节点日志风格不统一（有的是 `[INFO] xxx`，有的是 `printf` 风格）
- **方案**：统一用 ROS2 的 `RCLCPP_INFO` / `RCLCPP_WARN` 等宏

### P4-E：参数校验
- **状态**：⬜ 待办
- **问题**：很多参数只有 `description`，没有 `choices` 或值范围校验
- **方案**：给关键参数加 `choices` 限定

### P4-F：测试覆盖
- **状态**：⬜ 待办（最低优先级）
- **方案**：核心节点加单元测试，启动文件加集成测试

---

## 七、改动进度总览

| 优先级 | 总数 | ✅ 已完成 | 🚧 进行中 | ⬜ 待办 |
|---|---|---|---|---|
| P0（Namespace） | 5 | 5 | 0 | 0 |
| P1（Namespace 补全） | 5 | 0 | 0 | 5 |
| P2（死代码清理） | 6 | 0 | 0 | 6 |
| P3（架构优化） | 6 | 0 | 0 | 6 |
| P4（工程质量） | 6 | 0 | 0 | 6 |
| **合计** | **28** | **5** | **0** | **23** |

---

## 八、建议的下一步

按"风险低、收益高"的顺序：

1. **P2-C** 清理空格备份文件（5 分钟，无风险）
2. **P1-D** 修 rtabmap.launch.py 默认值（2 行改动）
3. **P2-A** 删 navigation2 历史 launch（约 10 个文件删除）
4. **P2-B** 删 maxarm / my_pkg / test_pkg（需要确认无外部引用）
5. **P3-A** 抽公共 launch 参数（影响 15 个文件，需要先打地基）
6. **P1-A/B/C** Namespace 架构补全（依赖 P0 已完成的经验）

每完成一组，建议：
- commit 一个 PR
- 真机验证
- 更新本文件状态

---

## 九、修订记录

| 日期 | 修订内容 |
|---|---|
| 2026-06-13 | 初版：完成架构分析、Namespace 分析、P0 修复、形成完整路线图 |