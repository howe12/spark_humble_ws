#!/usr/bin/env python3
"""03-8 NeRF 入门: 位置编码 — 为什么 MLP 需要频率编码

NeRF 用 sin/cos 高频函数编码坐标，解决 MLP 的"低频偏置"。
γ(x) = [x, sin(2^0πx), cos(2^0πx), sin(2^1πx), cos(2^1πx), ...]

本程序演示:
  1. 不同 L 等级的编码向量
  2. 编码后的"频率成分"——为何能表达高频细节
"""

import numpy as np

def positional_encoding(x, L):
    """NeRF 位置编码: γ(x) = [x, sin(2^i·π·x), cos(2^i·π·x), ...]"""
    gamma = [x]
    for i in range(L):
        gamma.append(np.sin(2**i * np.pi * x))
        gamma.append(np.cos(2**i * np.pi * x))
    return np.array(gamma)

print("=" * 60)
print("NeRF 位置编码 (Positional Encoding)")
print("γ(x) = [x, sin(2^0πx), cos(2^0πx), sin(2^1πx), cos(2^1πx), ...]")
print("=" * 60)

# --- 演示 1: 不同 L 等级的编码向量 ---
x = 0.3
print(f"\n对 x={x} 做不同 L 等级的编码:")
print(f"{'L':<4} {'输出维度':<10} {'编码向量前 6 维'}")
print("-" * 50)
for L in [1, 2, 4, 6, 10]:
    enc = positional_encoding(x, L)
    print(f"{L:<4} {len(enc):<10} {enc[:6]}")

# --- 演示 2: 编码后的频率成分 ---
print(f"\n{'='*60}")
print("编码后的频率成分 (L=4, 对 x∈[0,1] 均匀采样)")
print(f"{'='*60}")
xs = np.linspace(0, 1, 100)

for i in range(4):
    sin_vals = np.sin(2**i * np.pi * xs)
    cos_vals = np.cos(2**i * np.pi * xs)
    # 找 sin/cos 范围内的极值位置
    print(f"\n  频率 2^{i}: 周期={1/2**i:.3f}")
    print(f"    sin(2^{i}πx): [{sin_vals.min():.2f}, {sin_vals.max():.2f}] "
          f"— {2**i} 个完整周期")
    print(f"    cos(2^{i}πx): [{cos_vals.min():.2f}, {cos_vals.max():.2f}] "
          f"— {2**i} 个完整周期")

# --- 演示 3: 编码后的距离区分能力 ---
print(f"\n{'='*60}")
print("编码后的欧氏距离 (两个相近点的区分度)")
print(f"{'='*60}")

pairs = [(0.3, 0.31), (0.3, 0.35), (0.3, 0.5)]
for x1, x2 in pairs:
    raw_dist = abs(x1 - x2)
    enc1 = positional_encoding(x1, L=10)
    enc2 = positional_encoding(x2, L=10)
    enc_dist = np.linalg.norm(enc1 - enc2)
    amplification = enc_dist / raw_dist if raw_dist > 0 else 0
    print(f"  x={x1} vs {x2}: raw_dist={raw_dist:.3f} "
          f"→ enc_dist={enc_dist:.3f} (放大 {amplification:.0f}x)")

print(f"\n结论:")
print(f"  1. L 越大 → 编码向量越长 (原始位置:1D → 编码后:1+2L 维)")
print(f"  2. 编码把微小位置差异放大 (0.3→0.31 放大 ~6x)")
print(f"  3. MLP 在高维编码空间中更容易拟合高频细节")
print(f"  4. NeRF 用 L=10(位置)+L=4(方向) = 编码 3D→63D 位置, 2D→9D 方向")
