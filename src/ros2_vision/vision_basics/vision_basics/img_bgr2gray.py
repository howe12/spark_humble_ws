# 本地图像灰度转换
import cv2
import sys

# 读取彩色图像
scripts_path = sys.path[0]  # 当前脚本的目录
image = cv2.imread(scripts_path + "/../pictures/test_image.png")

# 将彩色图像转换为灰度图像
gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# 显示灰度图像
cv2.imshow('Gray Image', gray_image)

# 等待用户输入键盘事件
cv2.waitKey()

# 销毁所有已经创建的 OpenCV 窗口
cv2.destroyAllWindows()
