# 【实践版】1.1 机器学习概述 — 线性回归房价预测

## 参考版结构对照

参考文档 `1.1 机器学习概述`（`EydNdrFifo6231x6CzhcPmp3ntc`）共 393 行，包含机器学习理论基础 + 一个 ROS1 节点的完整代码示例。本实践版聚焦于代码的可执行性，将理论部分保留为摘要，重点展示 ROS2 环境下的修改。

| 参考版章节 | 实践版处理 |
|-----------|-----------|
| 机器学习基本术语 | ⏭️ 跳过（纯理论） |
| 模型评估与选择 | ⏭️ 跳过（纯理论） |
| 性能度量 | ⏭️ 跳过（纯理论） |
| ROS 功能包创建 | 🔴 修改：catkin → colcon |
| linear_reg.py 完整程序 | 🔴 修改：去 ROS1 依赖 |
| 编译运行 | 🔴 修改：catkin_make → python3 直接运行 |

## 🔴 关键修改

### 修改 1：去掉 ROS1 包装

**问题**：原文档将纯 Python 脚本放入 catkin ROS1 包，用 `catkin_make` + `rosrun` 启动，但 `linear_reg.py` **没有任何一行 rospy 调用**。

```bash
# 原文档（ROS1）
cd ~/scorpio/src/scorpio_app
catkin_create_pkg ml_ros_core rospy std_msgs sensor_msgs nav_msgs geometry_msgs
# ... 写代码 ...
catkin_make
source devel/setup.bash
rosrun ml_ros_core linear_reg.py
```

```bash
# 实践版（ROS2 / 纯 Python）
cd ~/Music/spark_humble
python3 src/ml_basics/ml_basics/linear_reg.py
```

**说明**：脚本本身不依赖任何 ROS 功能（没有订阅/发布话题，没有调用 ROS 参数），因此无需放入 ROS 包。直接 `python3` 运行即可。

### 修改 2：Shebang 和文档字符串

```python
# 原始
#!/usr/bin/env python

# 修改后
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1.1 机器学习概述 — 线性回归房价预测
原始文档: 1.1 机器学习概述 (Feishu doc EydNdrFifo6231x6CzhcPmp3ntc)
迁移说明: 原为 ROS1 catkin 包中脚本，实际无任何 rospy 调用，
         改为纯 Python 独立脚本，python3 直接运行。
"""
```

### 修改 3：增强输出可读性

原脚本输出单行 MSE，实践版增加 RMSE 和模型公式输出：

```python
rmse = np.sqrt(mse)
print(f"  MSE  = {mse:.2f}")
print(f"  RMSE = {rmse:.2f}")
print(f"  公式: price = {model.coef_[0]:.2f}*area + ...")
```

---

## ✅ 审查结论

| 检查项 | 结果 |
|--------|------|
| 代码可执行性 | ✅ 直接 python3 运行 |
| 依赖兼容性 | ✅ pandas/numpy/sklearn 均兼容 Python 3.11 |
| ROS 依赖 | ✅ 无需 ROS（代码无 rospy 调用） |
| 输出正确性 | ✅ RMSE=15392，预测房价=311250（与原文档一致） |

---

## 📝 完整代码

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1.1 机器学习概述 — 线性回归房价预测
原始文档: 1.1 机器学习概述 (Feishu doc EydNdrFifo6231x6CzhcPmp3ntc)
迁移说明: 原为 ROS1 catkin 包中脚本，实际无任何 rospy 调用，
         改为纯 Python 独立脚本，python3 直接运行。
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

# 生成示例数据
data = {
    'area': [1000, 1500, 1200, 1800, 1600, 1400, 1700, 1900, 1300, 1100],
    'bedrooms': [2, 3, 2, 4, 3, 3, 4, 5, 2, 2],
    'bathrooms': [1, 2, 1, 2, 2, 1, 2, 3, 1, 1],
    'price': [200000, 300000, 250000, 350000, 320000, 280000, 330000, 380000, 240000, 220000]
}
df = pd.DataFrame(data)

print("原始数据:")
print(df)

X = df[['area', 'bedrooms', 'bathrooms']]
y = df['price']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = LinearRegression()
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
mse = mean_squared_error(y_test, y_pred)
rmse = np.sqrt(mse)
print(f"\n模型评估:")
print(f"  MSE  = {mse:.2f}")
print(f"  RMSE = {rmse:.2f}  (相对于 20-38 万的房价，误差约 {rmse/250000*100:.1f}%)")

print(f"\n模型参数:")
print(f"  系数 (w1,w2,w3): {model.coef_}")
print(f"  截距 (b):        {model.intercept_:.2f}")
print(f"  公式: price = {model.coef_[0]:.2f}*area + {model.coef_[1]:.2f}*bedrooms + {model.coef_[2]:.2f}*bathrooms + {model.intercept_:.2f}")

new_data = pd.DataFrame({'area': [1550], 'bedrooms': [3], 'bathrooms': [2]})
predicted_price = model.predict(new_data)
print(f"\n新数据预测:")
print(f"  area=1550, bedrooms=3, bathrooms=2")
print(f"  预测价格: {predicted_price[0]:.0f} 元")
```

---

## 🚀 运行命令

```bash
cd ~/Music/spark_humble
python3 src/ml_basics/ml_basics/linear_reg.py
```

## 📊 预期输出

```
原始数据:
   area  bedrooms  bathrooms   price
0  1000         2          1  200000
1  1500         3          2  300000
...

模型评估:
  MSE  = 236920013.85
  RMSE = 15392.21  (相对于 20-38 万的房价，误差约 6.2%)

模型参数:
  系数 (w1,w2,w3): [  193.42 -5263.16  6447.37]
  截距 (b):        14342.11
  公式: price = 193.42*area + -5263.16*bedrooms + 6447.37*bathrooms + 14342.11

新数据预测:
  area=1550, bedrooms=3, bathrooms=2
  预测价格: 311250 元
```

---

## 🔍 参考版评价

| 维度 | 评价 |
|------|------|
| 理论完整性 | ✅ 机器学习基础概念覆盖全面（监督/无监督、过拟合/欠拟合、交叉验证） |
| 代码合理性 | ⚠️ 纯 Python 脚本不应放入 catkin ROS1 包，增加不必要的构建复杂度 |
| 环境适配性 | ❌ ROS1 Noetic + Python 3.8 → 需改为 ROS2 Humble + Python 3.11 |
| 教学效果 | ✅ 房价预测示例直观，线性回归公式与系数解读清晰 |

---

## 📋 验证记录

- **测试时间**: 2026-06-25
- **Python 版本**: 3.11（系统 `/usr/bin/python3`）
- **依赖版本**: pandas 2.2.2, numpy 1.24.3, scikit-learn 1.5.2
- **运行结果**: ✅ 通过，输出与原文档完全一致
- **ROS 环境**: 无需 ROS（独立 Python 脚本）
- **硬件信息**: NXROBO Spark（无 GPU 依赖）
