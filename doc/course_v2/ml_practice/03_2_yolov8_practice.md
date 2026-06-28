# 【实践版】3.2 YOLOv8 配置课程

## 参考版结构对照

参考文档「3.2 深度学习-YOLOv8 配置课程」(`S1x8dtWN7o1ikwxzhqWcbzbpnzy`) 是 YOLOv8 安装/配置/推理教程，无 ROS 节点。实践版保留全部核心流程，更新版本号。

| 参考版内容 | 实践版处理 |
|-----------|-----------|
| Python 3.8 | 🟡 → Python 3.11 |
| ultralytics 版本 | 🟡 → ultralytics≥8.0 |
| pip install 命令 | 🔴 pip → pip3 |

---

## 📝 程序执行流程

```
python3 yolov8_demo.py
  → 检查 ultralytics 是否安装
  → 下载测试图片 (zidane.jpg, 来自 Ultralytics 官方)
  → 加载 yolov8n.pt (nano, 6.5MB)
  → 推理 → 打印检测结果
  → 保存结果图: /tmp/yolov8_result.jpg
```

### 运行命令

```bash
cd ~/Music/spark_humble/src/ml_basics/ml_basics
python3 yolov8_demo.py
```

### 预期输出

```
ultralytics 已安装 ✓
下载测试图片: zidane.jpg
模型: yolov8n.pt

检测到 3 个目标:
  [1] person  置信度: 0.806
  [2] person  置信度: 0.794
  [3] tie     置信度: 0.370

结果保存: /tmp/yolov8_result.jpg
```

> 完整代码见 `src/ml_basics/ml_basics/yolov8_demo.py`

## 📋 验证记录

- ultralytics 8.x, Python 3.11
- ✅ 3 目标检测通过，结果图正常生成
- 模型: yolov8n.pt (6.5MB, 自动下载)
