#!/bin/bash
#!SPARK技术讨论与反馈群：8346256
# Green_font_prefix="\033[32m" && Red_font_prefix="\033[31m" && Green_background_prefix="\033[42;37m" && Red_background_prefix="\033[41;37m" && Font_color_suffix="\033[0m"
# Info="${Green_font_prefix}[信息]${Font_color_suffix}"
# echo -e "${Info} 地图将会被保存到工作空间下的 install/spark_navigation2/share/spark_navigation2/map/目录下"
# echo -e "${Info} 是否开始保存当前的地图？"
# echo -e "${Info} 确定保存请按任意键，退出请输入：Ctrl + c    " 
# echo && stty erase '^H' && read -p "按任意键开始：" 
# PROJECTPATH=$(cd `dirname $0`; pwd)
# gnome-terminal --title="save_map_action"  -- bash -c "ros2 run nav2_map_server map_saver_cli -f ${PROJECTPATH}/../../../spark_navigation2/share/spark_navigation2/map/map --ros-args -p save_map_timeout:=1000.00"


#!/bin/bash
# save_map_action.sh

# 接收命名空间参数
NAMESPACE="${1:-}"

# 颜色定义
Green_font_prefix="\033[32m"
Red_font_prefix="\033[31m"
Font_color_suffix="\033[0m"
Info="${Green_font_prefix}[信息]${Font_color_suffix}"

echo -e "${Info} 地图保存程序启动"
echo -e "${Info} 原始命名空间: ${NAMESPACE:-（无）}"
echo -e "${Info} 地图将会被保存到工作空间下的 install/spark_navigation2/share/spark_navigation2/map/目录下"
echo -e "${Info} 是否开始保存当前的地图？"
echo -e "${Info} 确定保存请按任意键，退出请输入：Ctrl + c    " 
echo && stty erase '^H' && read -p "按任意键开始：" 

# -------------------- 核心修改部分 START --------------------
# 1. 清理命名空间：去除前后的/，避免文件名包含无效斜杠
CLEANED_NAMESPACE=$(echo "$NAMESPACE" | sed -e 's/^\/\+//' -e 's/\/\+$//')

# 2. 动态构建地图基础名称
if [ -n "$CLEANED_NAMESPACE" ]; then
    MAP_BASE_NAME="${CLEANED_NAMESPACE}_map"  # 有命名空间：n1_map
else
    MAP_BASE_NAME="map"  # 无命名空间：保持默认map
fi

# 3. 重构地图保存路径（目录不变，文件名改为动态生成的MAP_BASE_NAME）
PROJECTPATH=$(cd `dirname $0`; pwd)
MAP_DIR="${PROJECTPATH}/../../../spark_navigation2/share/spark_navigation2/map"
MAP_PATH="${MAP_DIR}/${MAP_BASE_NAME}"

# 确保地图目录存在（避免目录缺失导致保存失败）
mkdir -p "${MAP_DIR}"
# -------------------- 核心修改部分 END --------------------

echo -e "${Info} 清理后命名空间: ${CLEANED_NAMESPACE:-（无）}"
echo -e "${Info} 地图基础名称: ${MAP_BASE_NAME}"
echo -e "${Info} 地图保存路径: ${MAP_PATH}"

# 构建命令
SAVE_CMD="ros2 run nav2_map_server map_saver_cli -f $MAP_PATH --ros-args -p save_map_timeout:=1000.00"

# 添加命名空间
if [ -n "$CLEANED_NAMESPACE" ] && [ "$CLEANED_NAMESPACE" != "/" ]; then
    SAVE_CMD="$SAVE_CMD -r __ns:=/${CLEANED_NAMESPACE}"
    echo -e "${Info} 使用命名空间: /${CLEANED_NAMESPACE}"
fi

echo -e "${Info} 执行命令: $SAVE_CMD"
echo ""

# 在新终端中执行
gnome-terminal --title="保存地图 ${CLEANED_NAMESPACE:+[$CLEANED_NAMESPACE]}" -- bash -c "
    echo '开始保存地图...';
    echo '清理后命名空间: ${CLEANED_NAMESPACE:-（无）}';
    echo '地图基础名称: ${MAP_BASE_NAME}';
    echo '保存路径: ${MAP_PATH}';
    echo '';
    $SAVE_CMD;
    echo '';
    echo '地图保存完成！生成文件：${MAP_BASE_NAME}.pgm 和 ${MAP_BASE_NAME}.yaml';
    echo '按 Enter 键关闭窗口...';
    read
"