#!/usr/bin/python3.10
"""
RT-DETR 实时 Transformer 目标检测

RT-DETR 是百度提出的实时端到端 Transformer 检测器，直接通过 YOLO() 加载。
与 YOLOv8 的 API 完全一致——唯一区别是模型名。

用法：
    python3 rtdetr_detect.py              # 用 lena.png
    python3 rtdetr_detect.py image.jpg    # 自定义图片

模型：rtdetr-l.pt（首次运行自动下载，约 128MB）
"""

import os, sys, time
if 'DISPLAY' not in os.environ:
    os.environ['DISPLAY'] = ':0'

from ament_index_python.packages import get_package_share_directory
import cv2
from ultralytics import RTDETR

MODEL_DIR = os.path.join(get_package_share_directory('vision_basics'), 'model')
_base = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.join(_base, '..')


def get_model(name):
    local = os.path.join(MODEL_DIR, name)
    return local if os.path.exists(local) else name


def main():
    # RTDETR 加载本地模型
    model_path = get_model('rtdetr-l.pt')
    print(f'模型: {model_path}')
    model = RTDETR(model_path)
    print(f'任务: {model.task}')

    img_path = sys.argv[1] if len(sys.argv) > 1 else f'{PROJ_DIR}/pictures/lena.png'
    img = cv2.imread(img_path)
    print(f'图片: {os.path.basename(img_path)} ({img.shape[1]}×{img.shape[0]})')

    # 推理
    t0 = time.time()
    results = model(img, conf=0.25, verbose=False)
    ms = (time.time() - t0) * 1000

    r = results[0]
    n = len(r.boxes) if r.boxes is not None else 0
    print(f'检测: {n} 个目标, 推理 {ms:.0f}ms')

    annotated = r.plot()
    print(f'绘图完成: shape={annotated.shape}, dtype={annotated.dtype}, '
          f'min={annotated.min()}, max={annotated.max()}, mean={annotated.mean():.0f}')

    # r.plot() 返回 RGB，cv2.imshow 需要 BGR
    annotated_bgr = cv2.cvtColor(annotated, cv2.COLOR_RGB2BGR)

    # 同时保存到文件，方便验证
    out = os.path.join(os.path.dirname(__file__), 'rtdetr_result.png')
    cv2.imwrite(out, annotated_bgr)
    print(f'已保存: {out}')

    cv2.namedWindow('RT-DETR — press any key to exit', cv2.WINDOW_NORMAL)
    cv2.imshow('RT-DETR — press any key to exit', annotated_bgr)
    print('窗口已打开，按任意键退出...')
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
