import pandas as pd
import numpy as np
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import classification_report, accuracy_score
from sklearn.tree import plot_tree
import matplotlib.pyplot as plt

# 1. 加载鸢尾花数据集
iris = load_iris()
X = iris.data
y = iris.target

# 查看数据结构和理论对应
print("=== 数据集特征（对应决策树中的属性a）===")
print("特征数量（维度）:", X.shape[1])
print("样本数量（|D|）:", X.shape[0])
print("类别数量（|Y|）:", len(np.unique(y)))
print("特征名称:", iris.feature_names)
print("类别名称:", iris.target_names)

# 2. 数据分割
# 理论对应：训练集用于学习决策树，测试集用于评估泛化能力
X_train, X_test, y_train, y_test = train_test_split(
    X, y, 
    test_size=0.2,  # 20%作为测试集
    random_state=42,  # 确保可重复性
    stratify=y  # 保持类别比例
)

# 3. 初始化决策树模型
# 参数与理论公式的对应：
# criterion='gini' -> 使用基尼指数进行划分选择
# max_depth=3 -> 限制树深度，防止过拟合
# random_state=42 -> 确保可重复性
model = DecisionTreeClassifier(
    criterion='gini',      # 基尼指数（对应CART算法）
    max_depth=3,          # 最大深度限制
    min_samples_split=2,  # 最小分裂样本数
    min_samples_leaf=1,   # 叶节点最小样本数
    random_state=42       # 随机种子
)

# 4. 训练模型
# 对应理论：递归地选择最优划分属性构建决策树
model.fit(X_train, y_train)

# 5. 预测与评估
y_pred = model.predict(X_test)

# 计算准确率
accuracy = accuracy_score(y_test, y_pred)
print(f"\n=== 模型评估 ===")
print(f"准确率: {accuracy:.4f}")

# 详细分类报告
print("\n分类报告:")
print(classification_report(y_test, y_pred, target_names=iris.target_names))

# 6. 可视化决策树
plt.figure(figsize=(12, 8))
plot_tree(
    model, 
    filled=True,  # 填充颜色表示类别
    feature_names=iris.feature_names,  # 特征名称
    class_names=iris.target_names,     # 类别名称
    rounded=True,                      # 圆角节点
    proportion=True                    # 显示样本比例
)
plt.title("Iris Classification Decision Tree（max_depth=3）")
plt.show()

# 7. 预测新数据示例
# 对应理论：从根节点开始，根据特征值沿决策树路径到达叶节点
new_data = np.array([[5.1, 3.5, 1.4, 0.2]])  # 一个新样本的特征向量
predicted_class = model.predict(new_data)
predicted_proba = model.predict_proba(new_data)

print(f"\n=== 新样本预测 ===")
print(f"输入特征: {new_data[0]}")
print(f"预测类别: {predicted_class[0]} ({iris.target_names[predicted_class[0]]})")
print(f"类别概率: {predicted_proba[0]}")