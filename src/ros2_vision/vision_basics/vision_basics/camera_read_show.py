# 读取相机
import cv2

# 打开相机（设备 ID 根据 lsusb 查询到的 Device 编号修改）
# 例如：Bus 004 Device 004 → 设备 ID 为 4
cap = cv2.VideoCapture(4)

# 检查视频捕获对象是否成功打开
while cap.isOpened():
    # 读取帧
    ret, frame = cap.read()
    if not ret:
        print("无法读取相机画面，请检查设备连接和 ID 号")
        break

    # 设置&修改分辨率
    dsize = (1080, 720)
    resize_frame = cv2.resize(frame, dsize)

    cv2.imshow("resize_frame", resize_frame)

    c = cv2.waitKey(1)
    if c == 27:
        break

cap.release()
cv2.destroyAllWindows()
