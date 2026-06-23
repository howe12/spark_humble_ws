#!/usr/bin/env python3
"""
YOLO-World 动态类别切换演示

YOLO-World 最强大的功能：运行时切换检测目标，无需重新训练！

按键切换预设场景：
    1 = 办公室：人 + 笔记本电脑 + 杯子 + 键盘
    2 = 厨房：人 + 杯子 + 瓶子 + 碗 + 刀
    3 = 工厂：人 + 安全帽 + 手套 + 扳手
    4 = 全部（COCO 默认 80 类）
    q = 退出

用法：
    python3 yolo_world_dynamic.py            # 摄像头
    python3 yolo_world_dynamic.py video.mp4  # 视频文件

模型：yolov8s-world.pt（首次运行自动下载）
"""

import sys
import cv2
from ultralytics import YOLOWorld


# ── 预设场景 ──
SCENES = {
    ord('1'): ('办公室', ['person', 'laptop', 'cup', 'keyboard', 'mouse', 'chair']),
    ord('2'): ('厨房', ['person', 'cup', 'bottle', 'bowl', 'knife', 'spoon', 'plate']),
    ord('3'): ('工厂', ['person', 'hard hat', 'glove', 'wrench', 'robot', 'box']),
    ord('4'): ('COCO默认', None),  # None = 不设限制
}


def main():
    model = YOLOWorld('yolov8s-world.pt')

    arg = sys.argv[1] if len(sys.argv) > 1 else '0'
    src = int(arg) if arg.isdigit() else arg
    cap = cv2.VideoCapture(src)
    if isinstance(src, int):
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print('无法打开视频源')
        return

    current_scene = 'COCO默认'
    model.set_classes(None)

    print('YOLO-World 动态演示')
    print('  1=办公室  2=厨房  3=工厂  4=全部  q=退出')
    print(f'  当前: {current_scene}')

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame, conf=0.3, verbose=False)
        annotated = results[0].plot()

        # 左侧场景名
        cv2.putText(annotated, f'Scene: {current_scene}', (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        # 右下角按键提示
        cv2.putText(annotated, '1:Office 2:Kitchen 3:Factory 4:All q:Quit',
                    (10, annotated.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

        cv2.imshow('YOLO-World Dynamic', annotated)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key in SCENES:
            name, classes = SCENES[key]
            current_scene = name
            model.set_classes(classes)
            print(f'  切换: {name} → {classes if classes else "全部"}')

    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
