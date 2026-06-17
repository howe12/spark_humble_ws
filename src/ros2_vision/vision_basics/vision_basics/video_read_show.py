import cv2
import sys

# 1. 获取脚本目录
scripts_path = sys.path[0]
# 2. 打开视频文件（请将你的视频文件放在 pictures 文件夹中，并修改文件名）
cap = cv2.VideoCapture(scripts_path + '/../pictures/demo_video.mp4')

# 如果视频打不开，尝试用相机
if not cap.isOpened():
    print("未找到视频文件，尝试打开相机...")
    cap = cv2.VideoCapture(0)

# 3. 循环读取每一帧
while cap.isOpened():
    # 读取一帧
    ret, frame = cap.read()
    if not ret:
        break
    # 调整帧大小
    dsize = (1080, 720)
    resize_frame = cv2.resize(frame, dsize)
    # 显示帧
    cv2.imshow("frame", resize_frame)
    # 等待 1ms 检测按键
    c = cv2.waitKey(1)
    # 按下 Esc 键退出
    if c == 27:
        break

# 4. 释放资源
cap.release()
# 5. 关闭所有窗口
cv2.destroyAllWindows()
