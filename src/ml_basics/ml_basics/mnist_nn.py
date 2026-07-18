#!/usr/bin/env python3
"""
Lesson 3.1 - 深度学习实战：CNN 手写数字识别

网络结构（与参考文档 4.4.2 完全一致）:
  Conv2d(1,16,3) → ReLU → MaxPool(2) → Conv2d(16,32,3) → ReLU → MaxPool(2)
  → Flatten → Linear(1568,128) → ReLU → Linear(128,10)

同时训练 MLP 作为对比基线。

输出:
  - pictures/mnist_cnn_curves.png  — CNN 训练曲线
  - models/mnist_cnn.pth            — CNN 模型权重（供实时推理加载）
"""

import os
import sys

# ── 路径 ──
_script_dir = os.path.dirname(os.path.abspath(__file__))
_pkg_dir = os.path.join(_script_dir, '..')
MODEL_DIR = os.path.join(_pkg_dir, 'models')
PICTURE_DIR = os.path.join(_pkg_dir, 'pictures')
DATA_DIR = os.path.join(_pkg_dir, 'data')
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(PICTURE_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import torch
import torch.nn as nn
import torchvision
import torchvision.transforms as transforms
from torch.utils.data import DataLoader


# ======================== 超参数 ========================
BATCH_SIZE = 64
LEARNING_RATE = 0.01
MOMENTUM = 0.9
NUM_EPOCHS = 5
HIDDEN_SIZE = 128
INPUT_SIZE = 28 * 28
NUM_CLASSES = 10
DATA_ROOT = DATA_DIR


class SimpleCNN(nn.Module):
    """CNN 手写数字识别网络（与参考文档 4.4.2 一致）

    Conv2d(1,16,3) → ReLU → MaxPool(2)
    → Conv2d(16,32,3) → ReLU → MaxPool(2)
    → Flatten → Linear(1568,128) → ReLU → Linear(128,10)
    """

    def __init__(self):
        super(SimpleCNN, self).__init__()
        self.conv1 = nn.Conv2d(1, 16, 3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.conv2 = nn.Conv2d(16, 32, 3, padding=1)
        self.pool2 = nn.MaxPool2d(2, 2)
        self.fc1 = nn.Linear(32 * 7 * 7, 128)
        self.fc2 = nn.Linear(128, NUM_CLASSES)

    def forward(self, x):
        x = self.pool(torch.relu(self.conv1(x)))
        x = self.pool2(torch.relu(self.conv2(x)))
        x = x.view(x.size(0), -1)
        x = torch.relu(self.fc1(x))
        x = self.fc2(x)
        return x


class MLP(nn.Module):
    """MLP 对比基线: Linear(784,128) → ReLU → Linear(128,10)"""

    def __init__(self):
        super(MLP, self).__init__()
        self.fc1 = nn.Linear(INPUT_SIZE, HIDDEN_SIZE)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(HIDDEN_SIZE, NUM_CLASSES)

    def forward(self, x):
        x = x.view(x.size(0), -1)
        x = self.relu(self.fc1(x))
        x = self.fc2(x)
        return x


def get_dataloaders():
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,)),
    ])
    trainset = torchvision.datasets.MNIST(
        root=DATA_ROOT, train=True, download=True, transform=transform)
    testset = torchvision.datasets.MNIST(
        root=DATA_ROOT, train=False, download=True, transform=transform)
    trainloader = DataLoader(trainset, batch_size=BATCH_SIZE, shuffle=True)
    testloader = DataLoader(testset, batch_size=BATCH_SIZE, shuffle=False)
    return trainloader, testloader, len(trainset), len(testset)


def train_epoch(model, loader, criterion, optimizer):
    model.train()
    running_loss = 0.0
    correct, total = 0, 0
    for images, labels in loader:
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        running_loss += loss.item()
        _, predicted = torch.max(outputs, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()
    return running_loss / len(loader), 100.0 * correct / total


@torch.no_grad()
def evaluate(model, loader):
    model.eval()
    correct, total = 0, 0
    for images, labels in loader:
        outputs = model(images)
        _, predicted = torch.max(outputs, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()
    return 100.0 * correct / total


def plot_curves(history, save_path, title='Training Curves'):
    epochs = range(1, len(history['train_loss']) + 1)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    ax1.plot(epochs, history['train_loss'], 'b-o', label='Train Loss')
    ax1.set_xlabel('Epoch'); ax1.set_ylabel('Loss')
    ax1.set_title(f'{title} - Loss'); ax1.legend(); ax1.grid(True)
    ax2.plot(epochs, history['train_acc'], 'b-o', label='Train Acc')
    ax2.plot(epochs, history['test_acc'], 'r-s', label='Test Acc')
    ax2.set_xlabel('Epoch'); ax2.set_ylabel('Accuracy (%)')
    ax2.set_title(f'{title} - Accuracy'); ax2.legend(); ax2.grid(True)
    plt.tight_layout()
    plt.savefig(save_path, dpi=120)
    plt.close()
    print(f"[Plot] Saved to: {save_path}")


def train_model(model, trainloader, testloader, name):
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.SGD(model.parameters(), lr=LEARNING_RATE, momentum=MOMENTUM)
    history = {'train_loss': [], 'train_acc': [], 'test_acc': []}

    for epoch in range(NUM_EPOCHS):
        train_loss, train_acc = train_epoch(model, trainloader, criterion, optimizer)
        test_acc = evaluate(model, testloader)
        history['train_loss'].append(train_loss)
        history['train_acc'].append(train_acc)
        history['test_acc'].append(test_acc)
        print(f"  [{name}] Epoch {epoch+1}/{NUM_EPOCHS}  "
              f"Loss: {train_loss:.4f}  Train: {train_acc:.2f}%  Test: {test_acc:.2f}%")
    return history


def main():
    print("=" * 60)
    print("Lesson 3.1 — CNN 手写数字识别 (与参考文档 4.4.2 一致)")
    print("=" * 60)

    print("\n[1/4] 加载 MNIST 数据集...")
    trainloader, testloader, n_train, n_test = get_dataloaders()
    print(f"      训练集: {n_train}  测试集: {n_test}")

    # ── 训练 CNN ──
    print("\n[2/4] 训练 CNN (SimpleCNN)...")
    cnn = SimpleCNN()
    n_params = sum(p.numel() for p in cnn.parameters())
    print(f"      结构: Conv→Pool→Conv→Pool→FC→FC")
    print(f"      参数量: {n_params:,}")
    cnn_history = train_model(cnn, trainloader, testloader, "CNN")
    cnn_acc = cnn_history['test_acc'][-1]

    # ── 训练 MLP 对比 ──
    print("\n[3/4] 训练 MLP 对比基线...")
    mlp = MLP()
    n_params_mlp = sum(p.numel() for p in mlp.parameters())
    print(f"      参数量: {n_params_mlp:,}")
    mlp_history = train_model(mlp, trainloader, testloader, "MLP")
    mlp_acc = mlp_history['test_acc'][-1]

    # ── 对比 ──
    print(f"\n[4/4] 对比结果:")
    print(f"      CNN 测试准确率: {cnn_acc:.2f}%  (参数量 {n_params:,})")
    print(f"      MLP 测试准确率: {mlp_acc:.2f}%  (参数量 {n_params_mlp:,})")
    print(f"      CNN vs MLP:     {'+' if cnn_acc > mlp_acc else ''}{cnn_acc - mlp_acc:+.2f}%")

    # 保存曲线
    plot_curves(cnn_history,
                os.path.join(PICTURE_DIR, 'mnist_cnn_curves.png'),
                title='CNN Training')
    plot_curves(mlp_history,
                os.path.join(PICTURE_DIR, 'mnist_mlp_curves.png'),
                title='MLP Training')

    # 保存 CNN 模型（供实时推理加载）
    cnn_path = os.path.join(MODEL_DIR, 'mnist_cnn.pth')
    torch.save(cnn.state_dict(), cnn_path)
    print(f"\n[Model] CNN 权重已保存: {cnn_path}")


if __name__ == '__main__':
    main()
