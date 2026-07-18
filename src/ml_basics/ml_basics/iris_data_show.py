# ================================================
# 鸢尾花数据集特征分布可视化程序
# ================================================
# 功能：使用matplotlib绘制鸢尾花数据集的四个特征分布直方图
# 技术栈：Python、NumPy、Pandas、Matplotlib、Scikit-learn
# 数据集：sklearn内置的iris数据集（包含150个样本，3个类别，4个特征）
# ================================================

# 导入必要的库
import numpy as np              # 用于科学计算和数组操作
import pandas as pd             # 用于数据处理和分析
# 解决numpy版本兼容性问题（当使用较新版本numpy时，旧代码中np.int等可能已被废弃）
np.int = int
np.float = float
np.bool = bool
import matplotlib.pyplot as plt # 用于数据可视化
import seaborn as sns           # 用于统计数据可视化（本代码未直接使用，但作为常用库导入）
from sklearn.datasets import load_iris  # 从sklearn导入内置的鸢尾花数据集

# 加载鸢尾花数据集
iris = load_iris()  # 返回一个包含数据集信息的Bunch对象

# 创建DataFrame数据结构，便于数据处理和分析
# iris.data包含150个样本的4个特征值
# iris.feature_names是4个特征的名称列表
df = pd.DataFrame(iris.data, columns=iris.feature_names)

# 添加目标类别列
# iris.target包含每个样本的类别标签（0, 1, 2）
df['target'] = iris.target

# 添加类别名称列
# 使用lambda函数将数字标签转换为对应的类别名称（setosa, versicolor, virginica）
# iris.target_names是类别名称列表
df['species'] = df['target'].apply(lambda x: iris.target_names[x])

# 绘制四个特征的分布直方图
plt.figure(figsize=(12, 8))  # 创建一个12x8英寸的绘图窗口

# 遍历四个特征
for i, feature in enumerate(iris.feature_names):
    plt.subplot(2, 2, i+1)  # 创建2x2网格布局的子图，当前子图索引为i+1
    
    # 为每个鸢尾花类别绘制该特征的直方图
    for species in iris.target_names:
        # 筛选当前类别的数据
        species_data = df[df['species'] == species]
        # 绘制直方图，alpha=0.5设置透明度以允许图形重叠
        plt.hist(species_data[feature], alpha=0.5, label=species)
    
    plt.title(feature)  # 设置子图标题为特征名称
    plt.legend()        # 显示图例，区分不同类别

plt.tight_layout()  # 自动调整子图间距，避免重叠
plt.show()          # 显示绘制的图形