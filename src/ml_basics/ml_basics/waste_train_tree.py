#!/usr/bin/env python3
"""
ROS2-adapted Waste Classification Decision Tree Training Script.

This script trains a DecisionTreeClassifier on geometric, color, and texture
features extracted from waste item images. It is adapted from the original ROS1
code for use in ROS2 Humble environments. The feature extractor (RGBWasteClassifier)
provides 12 features per image: 5 geometric, 5 color, and 2 texture features.

Usage:
    cd src/ml_basics/ml_basics && python3 waste_train_tree.py

The script loads images from '../data/train_img/' (or falls back to synthetic data),
trains a decision tree, evaluates it, and saves the model.
All generated images are saved to ../pictures/.
"""

import os
import sys
import cv2
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for headless environments
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import seaborn as sns
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

# ── Output directories ──
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PICTURES_DIR = os.path.join(_SCRIPT_DIR, '..', 'pictures')
MODELS_DIR = os.path.join(_SCRIPT_DIR, '..', 'models')
os.makedirs(PICTURES_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)


# =============================================================================
# GLCM (Gray-Level Co-occurrence Matrix) — Vectorized implementation
# =============================================================================

def _compute_glcm_vectorized(gray_img, levels=16, distances=None, angles=None):
    """
    Compute GLCM features (contrast, energy, homogeneity, correlation) using
    vectorized numpy operations — no Python for-loops over pixels.

    Args:
        gray_img: 2D uint8 grayscale image.
        levels:   Number of gray levels for quantization (default 16).
        distances: List of pixel distances (default [1]).
        angles:    List of angles in radians (default [0, pi/4, pi/2, 3*pi/4]).

    Returns:
        Dictionary with averaged GLCM properties: 'contrast', 'energy',
        'homogeneity', 'correlation'.
    """
    if distances is None:
        distances = [1]
    if angles is None:
        angles = [0, np.pi / 4, np.pi / 2, 3 * np.pi / 4]

    # Quantize to fewer gray levels
    bins = np.linspace(0, 256, levels + 1)
    quantized = np.digitize(gray_img, bins) - 1
    quantized = np.clip(quantized, 0, levels - 1)

    rows, cols = quantized.shape
    props = {'contrast': 0.0, 'energy': 0.0, 'homogeneity': 0.0, 'correlation': 0.0}
    pair_count = 0

    for d in distances:
        for angle in angles:
            # Compute offsets
            dr = int(round(d * np.sin(angle)))
            dc = int(round(d * np.cos(angle)))

            # Build co-occurrence matrix via vectorized indexing
            # Pairs: (r, c) -> (r+dr, c+dc)
            r_from = max(0, -dr)
            r_to = min(rows, rows - dr)
            c_from = max(0, -dc)
            c_to = min(cols, cols - dc)

            r_src = np.arange(r_from, r_to)
            c_src = np.arange(c_from, c_to)

            # Use meshgrid for all valid source coordinates
            rr, cc = np.meshgrid(r_src, c_src, indexing='ij')
            rr_flat = rr.ravel()
            cc_flat = cc.ravel()

            src_vals = quantized[rr_flat, cc_flat]
            dst_vals = quantized[rr_flat + dr, cc_flat + dc]

            # Count co-occurrences (vectorized bincount using 2D index)
            pair_idx = src_vals * levels + dst_vals
            glcm_flat = np.bincount(pair_idx, minlength=levels * levels)
            glcm = glcm_flat.reshape(levels, levels).astype(np.float64)

            # Normalize
            total = glcm.sum()
            if total == 0:
                continue
            glcm /= total

            i = np.arange(levels, dtype=np.float64)
            j = np.arange(levels, dtype=np.float64)
            ii, jj = np.meshgrid(i, j, indexing='ij')

            diff = np.abs(ii - jj)
            props['contrast'] += np.sum(glcm * diff ** 2)
            props['energy'] += np.sum(glcm ** 2)
            mask = (ii + jj) > 0
            props['homogeneity'] += np.sum(np.where(mask, glcm / (1 + diff), 0))
            pair_count += 1

    if pair_count > 0:
        for k in props:
            props[k] /= pair_count
    return props


# =============================================================================
# RGBWasteClassifier — 12-feature extractor (geometric + color + texture)
# =============================================================================

class RGBWasteClassifier:
    def __init__(self):
        # Feature thresholds
        self.thresholds = {
            'min_contour_area': 100,
            'circularity_threshold': 0.7,
            'aspect_ratio_threshold': 2.0,
            'solidity_threshold': 0.85,
        }

    def get_features(self, rgb_image):
        """
        Extract features from RGB image.
        Returns: [aspect_ratio, solidity, circularity, rectangularity, complexity,
                  mean_hue, mean_sat, white_ratio, highlight_ratio, color_consistency,
                  texture_contrast, texture_energy]  (12 features)
        """
        # 1. Preprocessing
        gray = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2HSV)

        # 2. Adaptive thresholding
        thresh = cv2.adaptiveThreshold(gray, 255,
                                      cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                      cv2.THRESH_BINARY_INV, 11, 2)

        # 3. Morphological operations
        kernel = np.ones((3, 3), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

        # 4. Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return np.zeros(12)

        # Find the largest contour
        cnt = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(cnt)

        if area < self.thresholds['min_contour_area']:
            return np.zeros(12)

        # 5. Extract features
        geometric_features = self._extract_geometric_features(cnt)
        color_features = self._extract_color_features(rgb_image, hsv, cnt)
        texture_features = self._extract_texture_features(gray, cnt)

        # Combine all features
        all_features = geometric_features + color_features + texture_features
        return np.array(all_features)

    def _extract_geometric_features(self, contour):
        """Extract geometric features (5)"""
        features = []

        # 1. Aspect ratio
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = float(max(w, h)) / min(w, h) if min(w, h) > 0 else 0

        # 2. Solidity
        area = cv2.contourArea(contour)
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        solidity = float(area) / hull_area if hull_area > 0 else 0

        # 3. Circularity
        perimeter = cv2.arcLength(contour, True)
        circularity = 0
        if perimeter > 0:
            circularity = (4 * np.pi * area) / (perimeter * perimeter)

        # 4. Rectangularity
        rect_area = w * h
        rectangularity = float(area) / rect_area if rect_area > 0 else 0

        # 5. Contour complexity
        complexity = len(contour) / perimeter if perimeter > 0 else 0

        return [aspect_ratio, solidity, circularity, rectangularity, complexity]

    def _extract_color_features(self, rgb_image, hsv_image, contour):
        """Extract color features (5)"""
        # Create mask
        mask = np.zeros(rgb_image.shape[:2], dtype=np.uint8)
        cv2.drawContours(mask, [contour], 0, 255, -1)

        # 1. Mean hue and saturation
        mean_val = cv2.mean(hsv_image, mask=mask)
        mean_hue = mean_val[0] / 180.0  # Normalize to [0,1]
        mean_sat = mean_val[1] / 255.0  # Normalize to [0,1]

        # 2. White area ratio
        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 30, 255])
        white_mask = cv2.inRange(hsv_image, lower_white, upper_white)
        white_ratio = np.sum(white_mask > 0) / np.sum(mask > 0) if np.sum(mask > 0) > 0 else 0

        # 3. Highlight ratio
        highlight_mask = cv2.inRange(rgb_image, (200, 200, 200), (255, 255, 255))
        highlight_ratio = np.sum(highlight_mask > 0) / np.sum(mask > 0) if np.sum(mask > 0) > 0 else 0

        # 4. Color consistency
        hsv_roi = hsv_image[mask > 0]
        if len(hsv_roi) > 0:
            color_std = np.std(hsv_roi, axis=0)
            color_consistency = 1.0 / (1.0 + np.mean(color_std) / 255.0)
        else:
            color_consistency = 0

        return [mean_hue, mean_sat, white_ratio, highlight_ratio, color_consistency]

    def _extract_texture_features(self, gray_image, contour):
        """
        Extract texture features (2): GLCM contrast + GLCM energy
        Using vectorized numpy GLCM computation, avoiding Python per-pixel loops
        """
        # Create ROI mask
        mask = np.zeros(gray_image.shape, dtype=np.uint8)
        cv2.drawContours(mask, [contour], 0, 255, -1)

        gray_roi = gray_image[mask > 0]

        if len(gray_roi) < 25:
            return [0.0, 0.0]

        # Get ROI bounding box and crop to speed up GLCM
        x, y, w, h = cv2.boundingRect(contour)
        roi_crop = gray_image[y:y + h, x:x + w]
        mask_crop = mask[y:y + h, x:x + w]

        # Set outside-ROI to 0
        roi_masked = roi_crop.copy()
        roi_masked[mask_crop == 0] = 0

        # Use vectorized GLCM computation
        glcm_props = _compute_glcm_vectorized(roi_masked, levels=16,
                                               distances=[1, 2],
                                               angles=[0, np.pi / 4, np.pi / 2, 3 * np.pi / 4])

        texture_contrast = glcm_props['contrast']
        texture_energy = glcm_props['energy']

        # Normalize
        texture_contrast_norm = np.clip(texture_contrast / 50.0, 0.0, 1.0)
        texture_energy_norm = np.clip(texture_energy * 10.0, 0.0, 1.0)

        return [texture_contrast_norm, texture_energy_norm]


# =============================================================================
# Synthetic data generator (fallback when no real images available)
# =============================================================================

def generate_synthetic_dataset(num_samples_per_class=5, target_size=(200, 200)):
    """
    Generate synthetic waste-like images with simple colored shapes.
    5 classes × N samples each for fast testing.

    Classes: plastic_bottle (blue rectangles), can (silver circles),
             battery (black rectangles), seed (green ellipses), tissue (white rectangles)
    """
    class_names = ['plastic_bottle', 'can', 'battery', 'seed', 'tissue']
    rng = np.random.RandomState(42)

    X = []
    y = []
    image_paths = []  # Will be None for synthetic

    for class_id, class_name in enumerate(class_names):
        for sample_id in range(num_samples_per_class):
            img = np.zeros((target_size[0], target_size[1], 3), dtype=np.uint8)

            if class_name == 'plastic_bottle':
                # Blue rectangle with rounded shape
                color = (rng.randint(100, 200), rng.randint(50, 150), rng.randint(150, 255))  # BGR blue
                cx, cy = rng.randint(60, 140), rng.randint(60, 140)
                w, h = rng.randint(40, 80), rng.randint(80, 140)
                cv2.rectangle(img, (cx - w // 2, cy - h // 2),
                             (cx + w // 2, cy + h // 2), color, -1)

            elif class_name == 'can':
                # Silver/gray circle
                gray_val = rng.randint(120, 200)
                color = (gray_val, gray_val, gray_val)
                cx, cy = rng.randint(70, 130), rng.randint(70, 130)
                radius = rng.randint(30, 60)
                cv2.circle(img, (cx, cy), radius, color, -1)

            elif class_name == 'battery':
                # Black rectangle (small)
                color = (rng.randint(0, 50), rng.randint(0, 50), rng.randint(0, 50))
                cx, cy = rng.randint(70, 130), rng.randint(70, 130)
                w, h = rng.randint(20, 50), rng.randint(50, 90)
                cv2.rectangle(img, (cx - w // 2, cy - h // 2),
                             (cx + w // 2, cy + h // 2), color, -1)

            elif class_name == 'seed':
                # Green ellipse
                color = (rng.randint(0, 80), rng.randint(100, 255), rng.randint(0, 80))
                cx, cy = rng.randint(70, 130), rng.randint(70, 130)
                axes = (rng.randint(15, 35), rng.randint(25, 50))
                angle = rng.randint(0, 180)
                cv2.ellipse(img, (cx, cy), axes, angle, 0, 360, color, -1)

            elif class_name == 'tissue':
                # White rectangle
                white_val = rng.randint(200, 255)
                color = (white_val, white_val, white_val)
                cx, cy = rng.randint(60, 140), rng.randint(60, 140)
                w, h = rng.randint(60, 100), rng.randint(60, 100)
                cv2.rectangle(img, (cx - w // 2, cy - h // 2),
                             (cx + w // 2, cy + h // 2), color, -1)

            # Add noise
            noise = rng.randint(0, 30, img.shape, dtype=np.uint8)
            img = cv2.add(img, noise)

            # Extract features
            extractor = RGBWasteClassifier()
            features = extractor.get_features(img)

            X.append(features)
            y.append(class_id)
            image_paths.append(None)

    return np.array(X), np.array(y), class_names, image_paths


# =============================================================================
# Data loading (real images or synthetic fallback)
# =============================================================================

def load_real_dataset(data_dir='train_img', target_size=(200, 200)):
    """
    Load dataset from real image folders.
    Args:
        data_dir: Data directory containing per-class subfolders
        target_size: Uniform resize target
    Returns:
        X: Feature matrix (n_samples, n_features)
        y: Label vector
        class_names: List of class names
        image_paths: List of image paths
    """
    # Initialize feature extractor
    extractor = RGBWasteClassifier()

    # Get class folders
    class_folders = ['plastic_bottle', 'can', 'battery', 'seed', 'tissue']
    class_names = class_folders.copy()

    data = []
    labels = []
    image_paths = []

    print("正在从实际图像加载数据并提取特征...")
    print("-" * 50)

    for class_id, folder_name in enumerate(class_folders):
        folder_path = os.path.join(data_dir, folder_name)

        if not os.path.exists(folder_path):
            print(f"警告: 文件夹 {folder_path} 不存在，跳过")
            continue

        # Get all image files in the folder
        image_files = [f for f in os.listdir(folder_path)
                      if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))]

        if not image_files:
            print(f"警告: 文件夹 {folder_path} 中没有图像文件，跳过")
            continue

        print(f"处理类别: {folder_name} ({len(image_files)} 张图像)")

        for img_file in image_files:
            img_path = os.path.join(folder_path, img_file)

            try:
                # Read image
                img = cv2.imread(img_path)
                if img is None:
                    print(f"警告: 无法读取图像 {img_path}，跳过")
                    continue

                # Resize image
                img = cv2.resize(img, target_size)

                # Extract features
                features = extractor.get_features(img)

                # Add to dataset
                data.append(features)
                labels.append(class_id)
                image_paths.append(img_path)

            except Exception as e:
                print(f"处理图像 {img_path} 时出错: {e}")
                continue

    # Convert to numpy arrays
    if len(data) == 0:
        print("\n未从实际图像加载到数据，使用合成数据作为回退...")
        return generate_synthetic_dataset(num_samples_per_class=5, target_size=target_size)

    X = np.array(data)
    y = np.array(labels)

    print("\n" + "=" * 50)
    print("数据集加载完成!")
    print(f"总样本数: {len(X)}")
    print(f"特征维度: {X.shape[1]}")
    print(f"类别分布:")
    for i, class_name in enumerate(class_names):
        count = np.sum(y == i)
        print(f"  {class_name}: {count} 个样本")
    print("=" * 50)

    return X, y, class_names, image_paths


# =============================================================================
# Training + Evaluation
# =============================================================================

def train_decision_tree(X, y, class_names, max_depth=5, random_state=42):
    """
    Train a decision tree model.
    Returns:
        model: Trained decision tree model
        X_train, X_test, y_train, y_test: Split datasets
        indices_train, indices_test: Original indices for train/test
    """
    # Define feature names
    feature_names = [
        'Aspect_Ratio', 'Solidity', 'Circularity', 'Rectangularity', 'Complexity',
        'Mean_Hue', 'Mean_Sat', 'White_Ratio', 'Highlight_Ratio', 'Color_Consistency',
        'Texture_Contrast', 'Texture_Energy'
    ]

    # 1. Data split — manually handle indices to avoid sklearn deprecated 3rd positional arg
    all_indices = np.arange(len(X))
    X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
        X, y, all_indices, test_size=0.2, random_state=random_state, stratify=y
    )

    print("\n--- 数据集分割结果 ---")
    print(f"训练集大小: {len(X_train)}")
    print(f"测试集大小: {len(X_test)}")
    print("-" * 30)

    # 2. Initialize decision tree model
    model = DecisionTreeClassifier(
        criterion='gini',
        max_depth=max_depth,
        random_state=random_state,
        min_samples_split=5,
        min_samples_leaf=2
    )

    # 3. Train model
    print("正在训练决策树模型...")
    model.fit(X_train, y_train)
    print("模型训练完成!")

    return model, X_train, X_test, y_train, y_test, idx_train, idx_test, feature_names


def evaluate_model(model, X_test, y_test, class_names):
    """Evaluate model performance"""
    # Predict
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)

    # Calculate accuracy
    accuracy = accuracy_score(y_test, y_pred)

    print("\n" + "=" * 50)
    print("模型评估结果")
    print("=" * 50)

    # Classification report
    print("\n--- 分类报告 ---")
    print(classification_report(y_test, y_pred, target_names=class_names))

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)

    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=class_names, yticklabels=class_names)
    plt.title('confusion matrix')
    plt.ylabel('true label')
    plt.xlabel('predicted label')
    plt.tight_layout()
    out = os.path.join(PICTURES_DIR, 'confusion_matrix.png')
    plt.savefig(out, dpi=100)
    plt.close()
    print(f"混淆矩阵已保存为 {out}")

    return accuracy, y_pred, y_pred_proba


def visualize_decision_tree(model, feature_names, class_names):
    """Visualize decision tree"""
    plt.figure(figsize=(20, 12))
    plot_tree(model,
              filled=True,
              feature_names=feature_names,
              class_names=class_names,
              rounded=True,
              proportion=True,
              fontsize=10,
              max_depth=5)  # Limit display depth to avoid over-complexity
    plt.title("decision tree", fontsize=16)
    plt.tight_layout()
    out = os.path.join(PICTURES_DIR, 'decision_tree.png')
    plt.savefig(out, dpi=100)
    plt.close()
    print(f"决策树可视化已保存为 {out}")


def analyze_feature_importance(model, feature_names):
    """Analyze feature importance"""
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1]

    print("\n--- 特征重要性排序 ---")
    for i, idx in enumerate(indices):
        print(f"{i+1:2d}. {feature_names[idx]:20s}: {importances[idx]:.4f}")

    # Visualize feature importance
    plt.figure(figsize=(12, 6))
    plt.bar(range(len(importances)), importances[indices])
    plt.xticks(range(len(importances)), [feature_names[i] for i in indices], rotation=45, ha='right')
    plt.title('feature importance')
    plt.xlabel('feature')
    plt.ylabel('importance')
    plt.tight_layout()
    out = os.path.join(PICTURES_DIR, 'feature_importance.png')
    plt.savefig(out, dpi=100)
    plt.close()
    print(f"特征重要性图已保存为 {out}")


def visualize_sample_predictions(model, X, y, image_paths, class_names, n_samples=5):
    """Visualize sample predictions"""
    if n_samples > len(X):
        n_samples = len(X)
    if n_samples == 0:
        return

    idxs = np.random.choice(len(X), n_samples, replace=False)

    fig, axes = plt.subplots(1, n_samples, figsize=(20, 4))
    if n_samples == 1:
        axes = [axes]

    for i, idx in enumerate(idxs):
        # Load actual image if available, otherwise use color block
        if image_paths[idx] is not None:
            img = cv2.imread(image_paths[idx])
            if img is not None:
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            else:
                img_rgb = np.zeros((200, 200, 3), dtype=np.uint8)
        else:
            # Synthetic data shown as solid color blocks
            colors = [(255, 0, 0), (0, 0, 255), (0, 255, 0), (255, 255, 0), (255, 0, 255)]
            img_rgb = np.full((200, 200, 3), colors[int(y[idx]) % len(colors)], dtype=np.uint8)

        # Predict
        features = X[idx].reshape(1, -1)
        true_label = y[idx]
        pred_label = model.predict(features)[0]
        proba = model.predict_proba(features)[0]

        # Display image
        axes[i].imshow(img_rgb)
        axes[i].set_title(f"actual: {class_names[true_label]}\npredict: {class_names[pred_label]}")
        axes[i].axis('off')

        # Add prediction probabilities
        proba_text = "\n".join([f"{class_names[j]}: {proba[j]:.2f}" for j in range(len(class_names))])
        axes[i].text(0.5, -0.1, proba_text, transform=axes[i].transAxes,
                    ha='center', fontsize=8, verticalalignment='top')

    plt.tight_layout()
    out = os.path.join(PICTURES_DIR, 'sample_predictions.png')
    plt.savefig(out, dpi=100)
    plt.close()
    print(f"样本预测可视化已保存为 {out}")


def save_model(model, filename='waste_classifier.pkl'):
    """Save model"""
    import joblib
    out = os.path.join(MODELS_DIR, filename)
    joblib.dump(model, out)
    print(f"\n模型已保存为: {out}")


# =============================================================================
# Main
# =============================================================================

def main():
    # 1. Load real image dataset
    scripts_path = sys.path[0]  # Current script directory
    train_data_dir = scripts_path + '/../data/train_img'  # Training dataset directory
    X, y, class_names, image_paths = load_real_dataset(train_data_dir)

    if len(X) == 0:
        print("错误: 没有加载到任何数据!")
        return

    # 2. View feature data
    print("\n--- 提取的特征数据 (前5个样本) ---")
    feature_names = [
        'Aspect_Ratio', 'Solidity', 'Circularity', 'Rectangularity', 'Complexity',
        'Mean_Hue', 'Mean_Sat', 'White_Ratio', 'Highlight_Ratio', 'Color_Consistency',
        'Texture_Contrast', 'Texture_Energy'
    ]

    df_features = pd.DataFrame(X, columns=feature_names)
    df_features['Label'] = [class_names[label] for label in y]
    print(df_features.head())
    print("-" * 50)

    # 3. Train decision tree model
    model, X_train, X_test, y_train, y_test, indices_train, indices_test, feature_names = train_decision_tree(
        X, y, class_names, max_depth=5, random_state=42
    )

    # 4. Evaluate model
    accuracy, y_pred, y_pred_proba = evaluate_model(model, X_test, y_test, class_names)

    # 5. Analyze feature importance
    analyze_feature_importance(model, feature_names)

    # 6. Visualize decision tree
    visualize_decision_tree(model, feature_names, class_names)

    # 7. Visualize sample predictions
    print("\n--- 样本预测可视化 ---")
    test_image_paths = [image_paths[i] for i in indices_test]
    visualize_sample_predictions(model, X_test, y_test, test_image_paths, class_names,
                                  n_samples=min(5, len(X_test)))

    # 8. Save model
    save_model(model)

    # 9. Test new data prediction
    print("\n" + "=" * 50)
    print("测试新数据预测")
    print("=" * 50)

    # Randomly select a sample from the test set for prediction
    test_idx = np.random.randint(0, len(X_test))
    test_features = X_test[test_idx].reshape(1, -1)

    # Get corresponding original index and image path
    original_idx = indices_test[test_idx]
    test_img_path = image_paths[original_idx]

    predicted_id = model.predict(test_features)[0]
    predicted_proba = model.predict_proba(test_features)[0]
    true_label = y_test[test_idx]

    print(f"测试样本特征: {test_features[0]}")
    print(f"预测类别: {class_names[predicted_id]}")
    print("类别概率:")
    for i, prob in enumerate(predicted_proba):
        print(f"  {class_names[i]}: {prob:.4f}")

    # Display prediction image and result
    print("\n--- 显示预测图片与结果 ---")
    try:
        # Read and display image
        if test_img_path is not None:
            test_img = cv2.imread(test_img_path)
        else:
            test_img = None

        if test_img is not None:
            test_img_rgb = cv2.cvtColor(test_img, cv2.COLOR_BGR2RGB)
        else:
            # Synthetic data fallback
            colors = [(255, 0, 0), (0, 0, 255), (0, 255, 0), (255, 255, 0), (255, 0, 255)]
            test_img_rgb = np.full((200, 200, 3), colors[int(true_label) % len(colors)], dtype=np.uint8)

        plt.figure(figsize=(8, 6))
        plt.imshow(test_img_rgb)

        # Judge result
        is_correct = (predicted_id == true_label)
        result_color = 'green' if is_correct else 'red'
        result_text = "✓ true" if is_correct else "✗ false"

        # Create title
        title = (f"true: {class_names[true_label]}\n"
                f"predict: {class_names[predicted_id]} ({predicted_proba[predicted_id]:.2f})\n"
                f"result: {result_text}")

        plt.title(title, fontsize=14, color=result_color, fontweight='bold')
        plt.axis('off')

        # Add probability info in corner
        prob_text = "\n".join([f"{class_names[i]}: {p:.2f}"
                              for i, p in enumerate(predicted_proba)])
        plt.text(0.02, 0.98, prob_text, transform=plt.gca().transAxes,
                fontsize=9, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        plt.tight_layout()
        out = os.path.join(PICTURES_DIR, 'prediction_result.png')
        plt.savefig(out, dpi=100)
        plt.close()
        print(f"预测结果图已保存为 {out}")

    except Exception as e:
        print(f"显示图片时出错: {e}")

    # 10. Get decision path
    print("\n机器人思考过程 (决策路径):")
    node_indicator = model.decision_path(test_features)
    leaf_id = model.apply(test_features)[0]

    # Get the path from root to leaf node
    node_index = node_indicator.indices[node_indicator.indptr[0]:
                                        node_indicator.indptr[1]]

    # Print decision rules
    for node_id in node_index:
        if node_id == leaf_id:
            continue

        # Get decision rule for this node
        if model.tree_.feature[node_id] != -2:  # Not a leaf node
            feature_idx = model.tree_.feature[node_id]
            threshold = model.tree_.threshold[node_id]
            feature_name = feature_names[feature_idx]

            # Determine which branch the current sample takes
            if test_features[0][feature_idx] <= threshold:
                print(f"  {feature_name} <= {threshold:.3f} → 向左分支")
            else:
                print(f"  {feature_name} > {threshold:.3f} → 向右分支")

    print(f"  到达叶子节点，预测为: {class_names[predicted_id]}")

    print(f"\n{'='*50}")
    print(f"训练完成! 准确率: {accuracy:.4f}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
