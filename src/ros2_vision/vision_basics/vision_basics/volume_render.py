#!/usr/bin/env python3
"""03-8 NeRF 入门: 1D 体渲染数值演示

用 Beer-Lambert 定律模拟光在介质中的传播:
  T(s) = exp(-∫σ(t)dt)  — 透射率
  C = Σ T_i × (1 - exp(-σ_i×δ_i)) × c_i  — 累积颜色

生成 1D"场景"（几个障碍物），离散采样，计算累积颜色。
帮助理解 NeRF 体渲染公式的物理含义。
"""

import numpy as np

# --- 1. 定义 1D"场景": 位置 0~10 上的密度函数 ---
# 模拟: 空区域 σ≈0, 障碍物处 σ 大
positions = np.linspace(0, 10, 100)
sigma = np.zeros(100)
sigma[20:25] = 2.0   # 障碍物 1: 位置 2.0~2.5
sigma[50:55] = 3.0   # 障碍物 2: 位置 5.0~5.5 (更密)
sigma[80:85] = 1.0   # 障碍物 3: 位置 8.0~8.5 (半透明)

# 颜色 (假设所有区域白色)
colors = np.ones((100, 3))

# --- 2. 离散体渲染 ---
delta = positions[1] - positions[0]  # 采样间距
N = len(positions)

# 初始化
T = np.ones(N)        # 透射率 T(t) = exp(-Σσ·δ)
T[0] = 1.0
C_accum = np.zeros(3) # 累积颜色

print("=" * 60)
print("1D 体渲染: 光从右向左传播 (t=10 → t=0)")
print("=" * 60)
print(f"采样点数: {N}, 间距 δ={delta:.3f}")
print(f"\n{'t':<8} {'σ':<8} {'T(t)':<10} {'α=1-e^{-σδ}':<14} {'贡献':<10}")
print("-" * 60)

for i in range(1, N):
    # 透射率: T_i = exp(-Σ_{j<i} σ_j · δ)
    T[i] = T[i-1] * np.exp(-sigma[i-1] * delta)

    # 该段的"不透明度" (吸收率)
    alpha = 1.0 - np.exp(-sigma[i] * delta)

    # 该段对颜色的贡献 = T_i × alpha × c_i
    contrib = T[i] * alpha * colors[i]

    C_accum += contrib

    if sigma[i] > 0.1 or i % 20 == 0:
        print(f"{positions[i]:<8.2f} {sigma[i]:<8.1f} {T[i]:<10.4f} "
              f"{alpha:<14.4f} {contrib[0]:<10.6f}")

print("-" * 60)
print(f"\n累积颜色: ({C_accum[0]:.4f}, {C_accum[1]:.4f}, {C_accum[2]:.4f})")
print(f"\n物理含义:")
print(f"  1. 空区域 (σ≈0): T 不变, α≈0, 不贡献颜色")
print(f"  2. 稠密区域 (σ=3): α≈1, 光几乎被阻挡")
print(f"  3. 第一个障碍物贡献最大 (T 最大)")
print(f"  4. 后面的障碍物被遮挡 (T 很小)")
print(f"\n这就是 NeRF 沿每条光线做体渲染的原理——")
print(f"只是 NeRF 用 MLP 预测 σ 和 c, 而非手动设定。")
