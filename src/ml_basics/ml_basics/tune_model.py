#!/usr/bin/env python3
"""
2.1 垃圾分类模型调参：对比决策树 vs 随机森林，选出最佳模型。
数据: ml_basics/data/train_img/ (5类×80张=400张)
"""
import os, sys
import numpy as np
import joblib
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

# 导入训练脚本中的数据加载和特征提取
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from waste_train_tree import load_real_dataset

# 1. 加载数据
scripts_path = os.path.dirname(os.path.abspath(__file__))
train_data_dir = scripts_path + '/../data/train_img'
X, y, class_names, image_paths_load = load_real_dataset(train_data_dir)

# 2. 划分训练/测试集 (stratify 保持类别均衡)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y)

print(f"\n训练集: {len(X_train)}  测试集: {len(X_test)}")
print("=" * 60)

# 3. 多模型对比
results = []

# --- 决策树：不同深度 ---
for depth in [3, 5, 7, 10, None]:
    dt = DecisionTreeClassifier(
        criterion='gini', max_depth=depth,
        random_state=42, min_samples_split=5, min_samples_leaf=2)
    dt.fit(X_train, y_train)
    train_acc = dt.score(X_train, y_train)
    test_acc = dt.score(X_test, y_test)
    cv_scores = cross_val_score(dt, X, y, cv=5)
    name = f"DecisionTree(max_depth={depth})"
    results.append((name, test_acc, train_acc, cv_scores.mean(), dt))
    print(f"{name:<30} train={train_acc:.3f}  test={test_acc:.3f}  cv={cv_scores.mean():.3f}+/-{cv_scores.std():.3f}")

# --- 决策树：gini vs entropy ---
for crit in ['gini', 'entropy']:
    dt = DecisionTreeClassifier(
        criterion=crit, max_depth=7,
        random_state=42, min_samples_split=5, min_samples_leaf=2)
    dt.fit(X_train, y_train)
    test_acc = dt.score(X_test, y_test)
    cv_scores = cross_val_score(dt, X, y, cv=5)
    name = f"DecisionTree(criterion={crit})"
    results.append((name, test_acc, dt.score(X_train, y_train), cv_scores.mean(), dt))
    print(f"{name:<30} train={dt.score(X_train, y_train):.3f}  test={test_acc:.3f}  cv={cv_scores.mean():.3f}")

# --- 随机森林：不同树数量 ---
for n_est in [50, 100, 200]:
    rf = RandomForestClassifier(
        n_estimators=n_est, max_depth=7, random_state=42,
        min_samples_split=5, min_samples_leaf=2, n_jobs=-1)
    rf.fit(X_train, y_train)
    test_acc = rf.score(X_test, y_test)
    cv_scores = cross_val_score(rf, X, y, cv=5)
    name = f"RandomForest(n={n_est}, depth=7)"
    results.append((name, test_acc, rf.score(X_train, y_train), cv_scores.mean(), rf))
    print(f"{name:<30} train={rf.score(X_train, y_train):.3f}  test={test_acc:.3f}  cv={cv_scores.mean():.3f}+/-{cv_scores.std():.3f}")

# --- 随机森林：不同深度 ---
for depth in [5, 10, None]:
    rf = RandomForestClassifier(
        n_estimators=100, max_depth=depth, random_state=42,
        min_samples_split=5, min_samples_leaf=2, n_jobs=-1)
    rf.fit(X_train, y_train)
    test_acc = rf.score(X_test, y_test)
    cv_scores = cross_val_score(rf, X, y, cv=5)
    name = f"RandomForest(n=100, depth={depth})"
    results.append((name, test_acc, rf.score(X_train, y_train), cv_scores.mean(), rf))
    print(f"{name:<30} train={rf.score(X_train, y_train):.3f}  test={test_acc:.3f}  cv={cv_scores.mean():.3f}")

# 4. 选出最佳模型（按测试集准确率）
print("\n" + "=" * 60)
results.sort(key=lambda x: x[1], reverse=True)
best = results[0]
print(f"\n最佳模型: {best[0]}")
print(f"  测试准确率: {best[1]:.4f}")
print(f"  5折交叉验证: {best[3]:.4f} +/- {best[1]-best[1]:.4f}")
print(f"  训练准确率: {best[2]:.4f}  (过拟合检查)")

# 5. 保存最佳模型
model_path = scripts_path + '/../models/waste_classifier.pkl'
os.makedirs(os.path.dirname(model_path), exist_ok=True)
joblib.dump(best[4], model_path)
print(f"\n最佳模型已保存: {model_path}")

# 6. 打印详细分类报告
best_model = best[4]
y_pred = best_model.predict(X_test)
print("\n" + classification_report(y_test, y_pred, target_names=class_names))

# 7. 打印排名
print("\n模型排名 (按测试准确率):")
for i, (name, test_acc, train_acc, cv_acc, _) in enumerate(results[:5]):
    print(f"  {i+1}. {name:<35} test={test_acc:.4f}  train={train_acc:.4f}  cv={cv_acc:.4f}")
