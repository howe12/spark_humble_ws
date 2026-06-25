#!/usr/bin/env python3
"""
YOLO 模型信息速查

打印本地所有可用 YOLO 模型的元信息：大小、参数、任务类型。
不运行推理，只读模型头。

用法：
    python3 yolo_model_info.py
"""

import os
from ament_index_python.packages import get_package_share_directory
from ultralytics import YOLO

MODEL_DIR = os.path.join(get_package_share_directory('vision_basics'), 'model')


def main():
    if not os.path.isdir(MODEL_DIR):
        print(f'模型目录不存在: {MODEL_DIR}')
        return

    pts = sorted([f for f in os.listdir(MODEL_DIR) if f.endswith('.pt')])

    if not pts:
        print('模型目录为空')
        return

    print(f'模型目录: {MODEL_DIR}')
    print(f'共 {len(pts)} 个模型\n')
    print(f'{"文件":<22} {"任务":<10} {"大小MB":<8} {"参数M":<8}')
    print('-' * 50)

    total_mb = 0
    for pt in pts:
        path = os.path.join(MODEL_DIR, pt)
        size_mb = os.path.getsize(path) / 1e6
        total_mb += size_mb

        try:
            model = YOLO(path)
            task = model.task
            try:
                info = model.info()
                params_m = info.get('parameters', 0) / 1e6
            except Exception:
                params_m = 0
        except Exception:
            task = '?'
            params_m = 0

        print(f'{pt:<22} {task:<10} {size_mb:<8.1f} {params_m:<8.1f}')

    print('-' * 50)
    print(f'总计: {total_mb:.1f} MB')

    print('\n💡 要下载新模型（如 YOLO11n），运行：')
    print('   cd ~/Music/spark_humble/src/spark_app/spark_yolov8/model')
    print('   wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt')
    print()
    print('   或者在 Python 中：')
    print("   from ultralytics import YOLO; YOLO('yolo11n.pt')  # 自动下载")


if __name__ == '__main__':
    main()
