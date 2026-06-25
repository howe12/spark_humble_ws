# Spark实践版 — 03-4 基于视觉标签的识别定位（ArUco + AprilTag）

适配说明：理论参考版使用 AprilTag，实践版使用 cv2.aruco 作基础教学，**新增 AprilTag (apriltag 库) 实践程序作为进阶补充**。
代码路径：`src/ros2_vision/vision_basics/`

---

## 参考版结构 & 实践版插入点

参考版共 6 章，理论部分以 AprilTag 为主线。

### 第 1 章 — 视觉标签入门

参考版内容：什么是视觉标签、AprilTag vs QR码、应用场景。

实践版插入：
- `tag_detect.py` — ArUco 标记检测 + PnP → 插入「1.4 视觉标签原理」之后
- `apriltag_detect.py` 🔴 — **AprilTag (apriltag 库) 检测** → 插入「1.5 AprilTag 标记族」之后，作为 ArUco 的对照实践

### 第 2~4 章 — 检测原理 / 位姿估计 / TF

实践版插入：
- `tag_pose.py` — ArUco 多标记位姿对比 → 插入「3.3 PnP 算法」之后
- `ros2_tag_detect.py` — ROS2 实时 ArUco 检测 + TF → 插入「4.2 TF 发布」之后
- `ros2_apriltag_detect.py` 🔴 — **ROS2 实时 AprilTag 检测 + TF** → 插入「4.2 TF 发布」之后

### 第 5 章 — 对比实验

实践版插入：
- `apriltag_compare.py` 🔴 — **ArUco vs AprilTag 并排对比** → 替换「5.1 不同标记族对比」，用真实代码验证两种库的 API 差异

---

## 参考版关键问题

- **理论讲 AprilTag，实践用 ArUco**：ArUco 是 OpenCV 内置（零依赖），原理相同（角点→PnP→6D位姿），适合入门。现在补充 AprilTag 实践，学生可对比两种库的 API、鲁棒性和适用场景
- **AprilTag 标记族不同**：tag36h11 有 6×6=36 个数据位，比 ArUco DICT_4X4_50 (16位) 更多，ID 范围更大、纠错更强
- **API 设计哲学不同**：ArUco 返回 `(corners, ids, rejected)` 元组，AprilTag 返回 `[Detection(tag_id, center, corners, hamming, ...)]` 对象列表

---

## 程序清单

### 本地图像程序

- `tag_detect.py` — ArUco 标记生成 + 检测 + PnP（OpenCV 内置）
- `tag_pose.py` — ArUco 多标记位姿估计对比（4 个标记并排）
- `apriltag_detect.py` 🔴 — **AprilTag 检测 + PnP**（apriltag 库, tag36h11）
- `apriltag_compare.py` 🔴 — **ArUco vs AprilTag 并排对比**（API 差异演示）

### ROS2 相机程序

- `ros2_tag_detect.py` — ArUco 实时检测 + PnP + TF 广播
- `ros2_apriltag_detect.py` 🔴 — **AprilTag 实时检测 + PnP + TF 广播**（apriltag 库）

---

# 🔴 新增：AprilTag 实践补充

## AprilTag vs ArUco 对比速查

| 特性 | ArUco (cv2.aruco) | AprilTag (apriltag 库) |
|------|-------------------|------------------------|
| 安装 | OpenCV 内置，零依赖 | `pip install apriltag` |
| 标记族 | DICT_4X4_50 (16位) | tag36h11 (36位) |
| ID 范围 | 0-49 | 0-586 |
| 检测 API | `detectMarkers(gray)` → 元组 | `detect(gray)` → Detection 列表 |
| 可视化 | `drawDetectedMarkers()` 内置 | 需手动用 cv2 画 |
| 位姿估计 | `solvePnP()` 相同 | `solvePnP()` 相同 (需手动传入角点) |
| 旋转鲁棒 | 中等 | 更强 (更复杂编码) |
| 质量指标 | 无 | hamming, decision_margin |

## AprilTag 的 Detection 对象

```python
import apriltag
detector = apriltag.Detector(apriltag.DetectorOptions(families='tag36h11'))
result = detector.detect(gray_image)

for r in result:
    r.tag_id           # int: 标记 ID
    r.center           # (float, float): 中心坐标
    r.corners          # 4×2 np.array: 四个角点 (左上, 右上, 右下, 左下)
    r.hamming          # int: 汉明距离 (0=完美匹配)
    r.decision_margin  # float: 决策裕度 (越大越确信, >30 为可靠)
    r.homography       # 3×3 np.array: 单应矩阵 (可用于位姿初值)
```

## 关键 API 差异示例

**ArUco 检测**：
```python
corners, ids, rejected = detector.detectMarkers(gray)
# corners: list of 4×2 arrays
# ids: N×1 array of tag IDs
cv2.aruco.drawDetectedMarkers(display, corners, ids)  # 内置画图
```

**AprilTag 检测**：
```python
result = detector.detect(gray)
# result: list of Detection objects
for r in result:
    for pt in r.corners.astype(int):
        cv2.circle(display, tuple(pt), 5, (0,255,0), -1)  # 手动画角点
    cv2.putText(display, f'ID:{r.tag_id}', ...)            # 手动画 ID
```

---

## 1. apriltag_detect.py — AprilTag 检测 + PnP

### 插入位置
参考版「1.5 AprilTag 标记族」之后，作为 ArUco (tag_detect.py) 的对照实践。

### 参考版描述
参考版用理论描述 AprilTag 的 tag36h11 标记族，但没有给出 Python 代码。

### 设计原因
补充 `apriltag` 库的实际代码，让学生体验:
1. `apriltag` 的 API 与 `cv2.aruco` 完全不同
2. AprilTag 返回的质量指标 (hamming, decision_margin) 是 ArUco 没有的
3. 标记族的重要性 — ArUco 标记不被 AprilTag 检测器识别

### 需要安装的依赖
```bash
pip3 install apriltag
```

### 完整代码
(见 `vision_basics/apriltag_detect.py`)

### 执行流程
1. 加载预生成的 AprilTag 标记图 (tag36h11, ID=0)
2. 创建 AprilTag 检测器 → `detect(gray)` → 得到 Detection 对象
3. 遍历结果：画角点 + 连线 + ID 文字
4. PnP 位姿估计 → 画坐标轴 (红X/绿Y/蓝Z)
5. 终端输出: tag_id, hamming, decision_margin, 3D位姿

---

## 2. apriltag_compare.py — ArUco vs AprilTag 并排对比

### 插入位置
参考版「5.1 不同标记族对比」，用真实代码替代理论表格。

### 设计原因
用同一个 ArUco 标记图，分别用 ArUco 和 AprilTag 检测器跑:
- **ArUco 能检测到 ArUco 标记** (标记族匹配)
- **AprilTag 检测不到 ArUco 标记** (ArUco 不在 tag36h11 族中)
- 让学生直观理解"标记族"的作用

### 完整代码
(见 `vision_basics/apriltag_compare.py`)

### 执行流程
1. 生成 ArUco 标记图 (DICT_6X6_250, ID=0)
2. **左窗口**：用 cv2.aruco 检测 → 大概率检测到
3. **右窗口**：用 apriltag 检测 → 检测不到（标记族不匹配）
4. 并排显示对比结果

---

## 3. ros2_apriltag_detect.py — ROS2 实时 AprilTag 检测 + TF

### 插入位置
参考版「4.2 TF 发布」之后，与 ros2_tag_detect.py 并列。

### 设计原因
与 ArUco 版 ROS2 节点完全对等的 AprilTag 版本:
- 相同的 TF 广播逻辑 (R→四元数)
- 相同的 PnP 算法 (cv2.solvePnP)
- 不同的检测器: `apriltag.Detector()` vs `cv2.aruco.ArucoDetector()`
- 额外显示: decision_margin (质量指标) 在 HUD 上

### 完整代码
(见 `vision_basics/ros2_apriltag_detect.py`)

### 执行流程
1. 订阅 D435 彩色图像 + CameraInfo
2. 灰度转换 → AprilTag 检测 (tag36h11)
3. 遍历 Detection 对象:
   - 手动画角点 (绿色圆点) + 连线
   - 画 ID + decision_margin
   - PnP 位姿估计 → 画坐标轴
   - 距离标注 + TF 广播 (apriltag_N)
4. cv2 实时显示 → ESC 退出

---

## 运行步骤

### AprilTag 本地程序

```bash
cd /home/spark/Music/spark_humble/src/ros2_vision/vision_basics/vision_basics
export DISPLAY=:0

# AprilTag 检测 (需预生成标记图)
python3 apriltag_detect.py

# ArUco vs AprilTag 对比
python3 apriltag_compare.py
```

### AprilTag ROS2 程序 (需 D435 相机)

```bash
cd /home/spark/Music/spark_humble
source install/setup.bash
export DISPLAY=:0

# 先启动相机
ros2 launch realsense2_camera rs_launch.py align_depth.enable:=true

# 运行 AprilTag 实时检测
ros2 run vision_basics ros2_apriltag_detect

# 对比 ArUco 版
ros2 run vision_basics ros2_tag_detect
```

### 编译

```bash
cd /home/spark/Music/spark_humble
colcon build --packages-select vision_basics
```

---

*课程制作：Spark 实践版 v2*
*更新日期：2026 年 7 月*
*新增：AprilTag 实践补充 (apriltag 库)*
