# 【实践版】2.2 NLP 文本指令机器人控制

## 参考版结构对照

参考文档「2.2 文本指令机器人控制」(`CadudmKUWoMzu3x5tmUcZepgn8b`) 包含 4 个 ROS1 节点组成的 NLP 流水线，实践版全部迁移至 ROS2。

| 参考版 (ROS1) | 实践版 (ROS2) | 变更 |
|---------------|---------------|------|
| text_preprocessor.py | nlp_preprocessor.py | 去 rospy，用 logging |
| intent_classifier_node.py | nlp_intent_classifier.py | rospy→rclpy |
| param_parser_node.py | nlp_param_parser.py | rospy→rclpy |
| cmd_control_node.py | nlp_cmd_control.py | rospy→rclpy |
| catkin_create_pkg | ml_basics 统一管理 | 构建系统切换 |

## 🔴 关键修改

### 修改 1：文本预处理去 ROS 依赖

原 `text_preprocessor.py` 虽然核心逻辑用 jieba 分词，但 import 了 rospy 用于日志。改为 Python 标准库 `logging`，完全脱离 ROS，可独立测试。

### 修改 2：意图分类器 ROS1→ROS2

TF-IDF + 规则匹配两层融合分类器。订阅 `/text_command`，发布 `/intent_result` + `/intent_confidence`。支持 8 种意图（前进/后退/左转/右转/停止/加速/减速/掉头），无预训练模型时自动用内置 54 条训练数据训练。

### 修改 3：参数解析器升级

在「意图 + 文本」双输入基础上，增强正则提取：支持带单位的距离（米/厘米）、角度（度/弧度）、速度（米每秒）、时间（秒/分钟），自动归一化到机器人坐标系。

### 修改 4：指令控制器 ROS1→ROS2

8 种意图 → `geometry_msgs/Twist` 映射，带持续发布定时器（20Hz）+ 自动停止定时器。机器人底盘话题 `/cmd_vel` 完全兼容原有 teleop 模块。

---

## ✅ 审查结论

| 检查项 | 结果 |
|--------|:--:|
| 4 节点编译 | ✅ colcon build 通过 |
| NLP 流水线连通性 | ✅ 话题链路一致 |
| jieba 分词兼容 | ✅ Python 3.11 |
| TF-IDF 训练 | ✅ 内置 54 条数据，即时可用 |
| 底盘接口兼容 | ✅ /cmd_vel (Twist)，与 teleop 相同 |

---

## 📝 程序执行流程（完整流水线）

```
用户输入文字 "前进 2 米"
  │
  ├─ [nlp_preprocessor.py]  jieba 分词 + 中文数字归一化
  │    → "前进 2 米"
  │
  ├─ [nlp_intent_classifier.py]  订阅 /text_command
  │    TF-IDF + 规则两层融合 → intent="forward", confidence=0.92
  │    发布: /intent_result, /intent_confidence
  │
  ├─ [nlp_param_parser.py]  订阅 /intent_result + /text_command
  │    正则提取: distance=2.0 (米), speed=0.2 (默认)
  │    发布: /cmd_params = "forward;distance=2.0;speed=0.2"
  │
  └─ [nlp_cmd_control.py]  订阅 /cmd_params
       查表: forward → linear=0.2, angular=0.0
       发布: /cmd_vel (Twist), /robot_status ("Executing: forward")
       自动停止: duration=2.0/0.2=10s 后发布 stop
```

---

## 📝 关键代码结构

**nlp_preprocessor.py** — 独立模块
- jieba 分词 + 短语检测（"往前走"→"前进"）
- 中文数字归一化（"两米"→2米, "半米"→0.5米）

**nlp_intent_classifier.py** — ROS2 节点
- 8 种意图: forward/backward/left/right/stop/speed_up/slow_down/turn_around
- 54 条内置训练语料（如 "前进"→forward, "往左拐"→left）

**nlp_param_parser.py** — ROS2 节点
- 正则提取: `距离(\d+)米`, `速度(\d+)`, `(\d+)秒`
- 按意图过滤参数（前进只需 distance/speed，转弯需 angle）

**nlp_cmd_control.py** — ROS2 节点
- intent → Twist 映射表
- 20Hz 持续发布定时器 + 自动停止定时器
- ROS2 参数: linear_speed, angular_speed, publish_rate

> 完整代码 4 个文件见 `src/ml_basics/ml_basics/nlp_*.py`

---

## 🚀 运行命令

```bash
# 终端 1: 启动 NLP 流水线
ros2 run ml_basics nlp_intent_classifier &
ros2 run ml_basics nlp_param_parser &
ros2 run ml_basics nlp_cmd_control &

# 终端 2: 测试文本预处理
echo "前进 2 米" | python3 src/ml_basics/ml_basics/nlp_preprocessor.py

# 终端 3: 发送测试指令
ros2 topic pub /text_command std_msgs/String "data: '前进 2 米'"

# 终端 4: 查看底盘指令
ros2 topic echo /cmd_vel
```

---

## 🔍 参考版评价

| 维度 | 评价 |
|------|------|
| 架构设计 | ✅ 4 节点流水线分层清晰（预处理→分类→解析→控制） |
| 代码合理性 | ✅ 扩展性好，新增意图只需修改 intent_velocity_map |
| 环境适配 | ❌ ROS1 Noetic → ROS2 Humble 全面改写 |
| 实践版改进 | 🟢 预处理去 ROS 依赖 + 参数解析增强 + 内置训练数据 |

---

## 📋 验证记录

- **测试时间**: 2026-06-25
- **ROS2 环境**: Humble, colcon build 通过
- **nlp_preprocessor.py**: ✅ jieba 分词测试通过
- **nlp_intent_classifier.py**: ✅ TF-IDF 分类器初始化成功
- **nlp_param_parser.py**: ✅ 参数解析初始化成功
- **nlp_cmd_control.py**: ✅ 节点初始化成功
- **端到端**: ⚠️ 需 Spark 底盘在线验证 /cmd_vel 实际控制
- **依赖**: jieba, scikit-learn, rclpy
