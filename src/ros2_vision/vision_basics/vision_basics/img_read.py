# 读取图片
import cv2
import sys

# 获取当前脚本的目录（关键：让路径不依赖运行位置）
scripts_path = sys.path[0]
# 拼接图片路径（"../pictures" 表示上一级目录的 pictures 文件夹）
image = cv2.imread(scripts_path + "/../pictures/lena.png")
# 打印图像数据（NumPy 数组）
print(image)
# 打印图像尺寸
print("img_size =", image.shape)
