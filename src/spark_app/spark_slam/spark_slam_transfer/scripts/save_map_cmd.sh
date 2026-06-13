#!/bin/bash
#!SPARK技术讨论与反馈群：8346256

# gnome-terminal --title="save_map_cmd"  -- bash -c "ros2 run spark_slam_transfer save_map_action.sh"

#!/bin/bash
# save_map_cmd.sh

# 接收命名空间参数
NAMESPACE="${1:-}"

echo "=== Save Map Command ==="
echo "Namespace: ${NAMESPACE:-default}"

# 如果有命名空间，传递给内部脚本
if [ -n "$NAMESPACE" ] && [ "$NAMESPACE" != "/" ]; then
    gnome-terminal --title="save_map_cmd [$NAMESPACE]" -- bash -c "ros2 run spark_slam_transfer save_map_action.sh $NAMESPACE"
else
    gnome-terminal --title="save_map_cmd" -- bash -c "ros2 run spark_slam_transfer save_map_action.sh"
fi