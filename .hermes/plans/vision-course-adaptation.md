# Spark 课程适配计划 —— ros2_vision

> **For Hermes:** 按照 task 逐步执行，每完成一个 task 就 commit 并更新 changelog。

**目标：** 将 leo_agv 课程（46 篇）适配到 spark 机器人平台，创建 `src/ros2_vision/` 工作区，编写 spark 实践版文档。

**架构：** 
- 代码层：`src/ros2_vision/` 下创建课程专属功能包，与 spark 主体隔离
- 文档层：每个适配后的文档写入目标飞书文件夹
- 版本控制：所有改动在 spark_humble 仓库的独立分支进行

**Tech Stack:** ROS2 Humble, OpenCV, Python, 飞书 Docx API

**源课程文件夹:** `ByYdfkST2lQfkzd9CkAcdisenlc` (46 篇)
**目标文件夹:** `S5GBfrjgPlIOQddB0oWcCFjrnVb`

---

## Phase 1: 基础设施 + 试水验证

### Task 1.1: 创建 ros2_vision 工作区骨架

**目标:** 在工作空间中建立 `src/ros2_vision/` 目录和第一个功能包

**Files:**
- Create: `src/ros2_vision/README.md`
- Create: `src/ros2_vision/spark_vision_basics/` (Python 包，对应课程 02-1)

**验证:** `colcon build --packages-select spark_vision_basics` 通过

---

### Task 1.2: 适配第一篇文档 (02-1 图像基本处理)

**目标:** 读取源文档，将 leo 代码替换为 spark 版本，写入目标飞书文件夹

**要点:**
- 包名：`leo_vision` → `spark_vision_basics`
- 路径：`leo_agv/src/leo_class/leo_vision_class/` → `spark_humble/src/ros2_vision/spark_vision_basics/`
- 相机：通用 USB 相机 → spark 的 D435/Astra（通过 `camera_driver_transfer` 已有 launch）
- 新增：介绍 spark 的相机启动方式（`ros2 launch camera_driver_transfer start_camera.launch.py`）

**验证:** 
1. 在 spark 上实际运行文档中的代码
2. 确认 D435 能正常读取图像
3. 文档已写入目标飞书文件夹

---

### Task 1.3: 用户审查试水结果

**目标:** 用户确认第一篇适配效果后，再继续后续模块

**决策点:** 
- 格式满意？→ 继续 Phase 2
- 需要调整？→ 修改后再继续

---

## Phase 2: 02 图像处理模块批量适配 (14篇)

### 适配映射表

| 源文档 | Spark 实践文档 | 对应功能包 |
|--------|---------------|-----------|
| 02-1 图像基本处理 | ✅ 已完成 (Task 1.2) | spark_vision_basics |
| 02-2 颜色处理 | 待适配 | spark_vision_basics |
| 02-3 滤波处理 | 待适配 | spark_vision_basics |
| 02-4 边缘检测 | 待适配 | spark_vision_basics |
| 02-5 形态学操作 | 待适配 | spark_vision_basics |
| 02-6 几何变换 | 待适配 | spark_vision_basics |
| 02-7 直方图与金字塔 | 待适配 | spark_vision_basics |
| 02-8 角点检测 | 待适配 | spark_vision_basics |
| 02-9 特征检测与描述子 | 待适配 | spark_vision_basics |
| 02-10 特征匹配 | 待适配 | spark_vision_basics |
| 02-11 相机标定 | 待适配 | spark_vision_basics |
| 02-12 单目测距与光流 | 待适配 | spark_vision_basics |
| 02-13 传统目标识别 | 待适配 | spark_vision_basics |
| 02-14 图像拼接 | 待适配 | spark_vision_basics |

### 每篇适配步骤

**Step A - 读取源文档：** 通过飞书 API 读取完整内容
**Step B - 识别差异点：** 标记所有 leo 特定代码（包名、路径、topic、硬件引用）
**Step C - 替换为 spark 版本：** 
  - 包名映射: `leo_vision` → `spark_vision_basics`
  - 路径映射: `leo_agv/src/leo_class/leo_vision_class/` → `spark_humble/src/ros2_vision/spark_vision_basics/`
  - 相机: 直接用 `cv2.VideoCapture` 保持不变，或通过 spark 已有 topic 订阅
  - 新增提示: 哪里可以直接用 spark 现有 launch
**Step D - 写入目标飞书文件夹：** 通过飞书 API 创建文档
**Step E - 验证：** 在 spark 上跑一遍代码

---

## Phase 3: 03-06 模块适配

### 03 3D/深度 (8篇) → spark_depth

| 源文档 | 关键适配点 |
|--------|-----------|
| 03-1 点云与深度相机 | 用 spark 的 D435 + realsense-ros |
| 03-2 深度目标跟随 | 对接 spark_follower |
| 03-3 深度物体抓取 | 对接 spark_carry + uArm |
| 03-4 AprilTag | 通用，补充 spark 相机 topic |
| 03-5 多相机融合 | spark 只有单相机，标注差异 |
| 03-6 深度方案对比 | 补充 spark 实际深度方案 |
| 03-7 ORB-SLAM3 | 对接 spark_slam |
| 03-8 NeRF 入门 | 通用，spark_torch 可跑 |

### 04 目标检测 (9篇) → 复用 spark_yolov8 / spark_object_detector

大部分 YOLO/SAM/RT-DETR 代码通用，主要改：
- launch 方式
- topic 订阅
- 图像输入来源（spark 相机 topic）

### 05 点云/3D (4篇) → spark_torch + spark_slam

### 06 VLM/前沿 (5篇) → ros2-tensorflow + spark_torch

---

## Leo → Spark 通用翻译规则

| 维度 | Leo (课程原文) | Spark (适配后) |
|------|---------------|---------------|
| **工作空间路径** | `~/leo_agv/` | `~/spark_humble/` |
| **源码目录** | `src/leo_class/leo_vision_class/` | `src/ros2_vision/spark_vision_basics/` |
| **功能包前缀** | `leo_*` | `spark_*` 或 `ros2_vision/*` |
| **相机驱动** | `cv2.VideoCapture(0)` | 优先用已有 launch: `ros2 launch camera_driver_transfer start_camera.launch.py` |
| **相机 topic** | `/camera/image_raw` | 实际 topic（通过 launch 确定） |
| **底盘控制** | `leo_agv` 控制指令 | spark_base 串口指令（不涉及视觉课的可以不改） |
| **编译命令** | `colcon build` | `colcon build --packages-select <pkg>` |
| **图形显示** | 假设有显示器 | 标注：无头环境需 X forwarding 或 `xvfb` |

---

## 文件结构（计划）

```
spark_humble/
├── src/
│   ├── ros2_vision/              ← 新建
│   │   ├── README.md             ← 课程工作区说明
│   │   ├── spark_vision_basics/  ← 02 模块 (14篇)
│   │   │   ├── spark_vision_basics/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── img_read.py       (02-1)
│   │   │   │   ├── color_process.py  (02-2)
│   │   │   │   ├── filter_demo.py    (02-3)
│   │   │   │   └── ...
│   │   │   ├── pictures/             ← 课程图片资源
│   │   │   ├── launch/
│   │   │   ├── package.xml
│   │   │   └── setup.py
│   │   ├── spark_depth/          ← 03 模块 (8篇)
│   │   ├── spark_perception/     ← 04-06 (复用现有包)
│   │   └── ...
│   ├── spark/                    ← 已有
│   ├── spark_app/                ← 已有
│   └── spark_driver/             ← 已有
├── docs/
│   └── course_adaptation/        ← 适配日志
└── log/
    └── changelog/
        └── vision-course-adaptation.md
```

---

## 风险与约束

1. 🟡 飞书 API 写文档需要 `docx:document:create` 权限，当前未验证
2. 🟡 部分课程依赖 leo 机器人的特定硬件（如深度相机实时跟随），spark 需要替代方案
3. 🟢 OpenCV 核心代码完全通用，改动量小
4. 🟢 YOLO/SAM 等模型代码与平台无关

---

## 下一步

确认计划后，从 **Task 1.1** 开始执行。
