#!/usr/bin/env python3
"""03-5 多相机融合: 视差→深度公式演示 Z = f×B/d

演示立体视觉核心公式的数值行为:
  - 视差 d 越大 → 深度 Z 越小（物体越近）
  - 视差 d 越小 → 深度 Z 越大（物体越远）
  - 1 像素视差误差在远处造成巨大深度误差

同时输出视差-深度对照表和精度分析。
"""

# D435 等效参数（真实 D435 内部有两个 IR 相机做立体匹配）
FOCAL = 613.0      # 焦距 (像素)
BASELINE = 0.050   # 基线 (米) — D435 的 IR 相机间距约 5cm

print("=" * 65)
print("立体视觉核心公式: Z = f × B / d")
print(f"  f (焦距) = {FOCAL:.0f} px")
print(f"  B (基线) = {BASELINE:.3f} m")
print(f"  d (视差) = 像素")
print("=" * 65)

# --- 视差 → 深度对照表 ---
disparities = [1, 2, 3, 5, 8, 12, 20, 30, 50, 80, 120]
print(f"\n{'视差 d (px)':<14} {'深度 Z (m)':<14} {'场景'}")
print("-" * 45)

for d in disparities:
    Z = FOCAL * BASELINE / d
    if Z < 0.5:
        scene = "极近 (<50cm)"
    elif Z < 1.5:
        scene = "近距 (<1.5m)"
    elif Z < 5:
        scene = "中距"
    elif Z < 15:
        scene = "远距"
    else:
        scene = "极远 (>15m)"
    print(f"{d:<14} {Z:<14.3f} {scene}")

# --- 精度分析: 1px 视差误差的影响 ---
print(f"\n{'='*65}")
print("精度分析: 如果视差有 ±1px 误差，深度误差多大？")
print(f"公式: ΔZ ≈ (Z² / (f×B)) × Δd    (Δd=1px)")
print(f"{'-'*50}")
print(f"{'深度 Z (m)':<14} {'误差 ΔZ (m)':<14} {'相对误差':<12}")
print("-" * 50)

for Z in [0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0]:
    delta_Z = Z**2 / (FOCAL * BASELINE) * 1.0
    rel_err = delta_Z / Z * 100
    print(f"{Z:<14.1f} {delta_Z:<14.4f} {rel_err:<11.1f}%")

print("\n结论:")
print("  1. 近处的深度精度高（0.5m → 误差仅 0.8%）")
print("  2. 远处的精度急剧下降（10m → 误差 32.6%）")
print("  3. 这就是为什么双目摄像头适合室内近距离测距")
print("  4. 要提高精度可增大基线 B 或焦距 f")
