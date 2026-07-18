#!/usr/bin/env python3.10
"""Post-build hook: ensure ROS2 executables exist in lib/<pkg>/"""
import os, sys
from pathlib import Path

install_dir = Path('/home/spark/Music/spark_humble/install/ml_basics')
bin_dir = install_dir / 'bin'
lib_dir = install_dir / 'lib' / 'ml_basics'

if not bin_dir.exists():
    print(f'sensor_monitor: no bin/ dir, skipping')
    sys.exit(0)

lib_dir.mkdir(parents=True, exist_ok=True)

for script in bin_dir.iterdir():
    target = lib_dir / script.name
    rel = os.path.relpath(script, lib_dir)
    if not target.exists():
        os.symlink(rel, target)
        print(f'  symlink: lib/ml_basics/{script.name} -> {rel}')

print(f'sensor_monitor: {len(list(lib_dir.iterdir()))} executables ready')
