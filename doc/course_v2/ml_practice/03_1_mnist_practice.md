# 【实践版】3.1 积木块神经网络构建

## 参考版结构对照

参考文档「3.1 深度学习实战-积木块神经网络构建」(`MZ0ed0swjoz7LWxqTitcoTXenWd`) 是纯 PyTorch 实验（MNIST 手写数字识别），无 ROS 依赖。实践版保留全部核心代码，仅做环境适配。

| 参考版内容 | 实践版处理 |
|-----------|-----------|
| PyTorch 版本 | 🟡 更新为 torch≥2.0（兼容 Python 3.11） |
| matplotlib 显示 | 🔴 改为 Agg 后端 + savefig (headless) |
| 代码本身 | ✅ 无需修改（原版无 ROS 依赖） |

## 🔴 关键修改

### 修改 1：Headless 适配

Spark 是无显示器机器人，`plt.show()` 无效。改为 `matplotlib.use('Agg')` + `plt.savefig()`。

### 修改 2：PyTorch 版本

原文档对应 ROS1 Noetic (Python 3.8)。实践环境 Python 3.11 + torch 2.7.1，API 完全兼容。

---

## 📝 程序执行流程

```
python3 mnist_nn.py
  → torchvision.datasets.MNIST 下载/加载 (缓存于 /tmp/mnist_data/)
  → DataLoader: batch_size=64, shuffle=True
  → 网络: Linear(784,128) → ReLU → Linear(128,10)
  → 损失: CrossEntropyLoss
  → 优化: SGD(lr=0.01, momentum=0.9)
  → 训练 5 epochs
  → 测试准确率 ~97%
  → 保存训练曲线: /tmp/mnist_nn_training_curves.png
```

### 运行命令

```bash
cd ~/Music/spark_humble
python3 src/ml_basics/ml_basics/mnist_nn.py
```

### 预期输出

```
Epoch 1/5: loss=0.2753, train_acc=91.94%, test_acc=96.03%
Epoch 2/5: loss=0.1131, train_acc=96.71%, test_acc=97.31%
Epoch 3/5: loss=0.0778, train_acc=97.70%, test_acc=97.43%
Epoch 4/5: loss=0.0598, train_acc=98.23%, test_acc=97.72%
Epoch 5/5: loss=0.0467, train_acc=98.65%, test_acc=97.67%
```

> 完整代码见 `src/ml_basics/ml_basics/mnist_nn.py`

## 📋 验证记录

- PyTorch 2.7.1 (CPU), Python 3.11
- ✅ 准确率 97.67%，训练曲线正常生成
- 代码路径: `src/ml_basics/ml_basics/mnist_nn.py`
