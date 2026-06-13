#!/bin/bash


# gnome-terminal --title="spark_control" --geometry 34x19+63+305 -- bash -c "ros2 run spark_teleop spark_teleop_node 0.14 0.5"

#!/bin/bash
# keyboard_control.sh

# 获取参数
NAMESPACE="${1:-}"
LIN_VEL="${2:-0.14}"
ANG_VEL="${3:-0.5}"

echo "=== 启动键盘控制节点 ==="
echo "命名空间: ${NAMESPACE:-（默认）}"
echo "线速度: $LIN_VEL m/s"
echo "角速度: $ANG_VEL rad/s"
echo "=========================="

# 构建完整的ros2命令
FULL_CMD="ros2 run spark_teleop spark_teleop_node $LIN_VEL $ANG_VEL"

# 添加命名空间（如果需要）
if [ -n "$NAMESPACE" ] && [ "$NAMESPACE" != "/" ]; then
    FULL_CMD="$FULL_CMD --ros-args -r __ns:=/$NAMESPACE"
fi

echo "执行命令: $FULL_CMD"
echo ""

# 在新终端中执行
gnome-terminal \
    --title="键盘控制 ${NAMESPACE:+[$NAMESPACE]}" \
    --geometry=60x20+100+100 \
    -- bash -c "echo '正在启动键盘控制节点...'; $FULL_CMD; echo ''; echo '节点已停止。按Enter键关闭窗口...'; read"