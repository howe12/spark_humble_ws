#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1.1 机器学习概述 — 线性回归房价预测

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

# 查看原始数据
print("原始数据:")
print(df)

# 分离特征和目标变量
X = df[['area', 'bedrooms', 'bathrooms']]
y = df['price']

# 数据分割
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 初始化线性回归模型
model = LinearRegression()

# 训练模型
model.fit(X_train, y_train)

# 预测
y_pred = model.predict(X_test)

# 评估模型
mse = mean_squared_error(y_test, y_pred)
rmse = np.sqrt(mse)
print(f"\n模型评估:")
print(f"  MSE  = {mse:.2f}")
print(f"  RMSE = {rmse:.2f}  (相对于 20-38 万的房价，误差约 {rmse/250000*100:.1f}%)")

# 查看模型系数
print(f"\n模型参数:")
print(f"  系数 (w1,w2,w3): {model.coef_}")
print(f"  截距 (b):        {model.intercept_:.2f}")
print(f"  公式: price = {model.coef_[0]:.2f}*area + {model.coef_[1]:.2f}*bedrooms + {model.coef_[2]:.2f}*bathrooms + {model.intercept_:.2f}")

# 预测新数据
new_data = pd.DataFrame({
    'area': [1550],
    'bedrooms': [3],
    'bathrooms': [2]
})
predicted_price = model.predict(new_data)
print(f"\n新数据预测:")
print(f"  area=1550, bedrooms=3, bathrooms=2")
print(f"  预测价格: {predicted_price[0]:.0f} 元")
