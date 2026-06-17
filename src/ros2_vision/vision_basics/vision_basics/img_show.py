# 显示图片
import cv2
import sys

# 1. 获取当前脚本目录
scripts_path = sys.path[0]
# 2. 读取图片
image = cv2.imread(scripts_path + "/../pictures/test_image.png")
# 3. 创建窗口并显示图片
cv2.imshow("test_image", image)
# 4. 等待按键（参数 0 表示无限等待）
cv2.waitKey(0)
# 5. 关闭所有窗口
cv2.destroyAllWindows()
