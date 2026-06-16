#!/usr/bin/env bash
# spark_humble 修改后自动化测试脚本
# 用法: cd /home/spark/Music/spark_humble && bash src/test_launch.sh
#
# 三层检查:
#   Layer 1: colcon build --packages-select (只编译改过的包)
#   Layer 2: 所有 onekey.sh 引用的 launch 文件 Python 语法检查
#   Layer 3: 给你输出的手动真机测试清单
set +e

PROJECTPATH=$(cd "$(dirname "$0")/.."; pwd)
PASS=0
FAIL=0
SKIP=0
ERRORS=""

GREEN='\033[32m'
RED='\033[31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "  Spark Humble 启动文件自动化检查"
echo "  $(date '+%Y-%m-%d %H:%M')"
echo "=========================================="

# ---- Layer 1: colcon build (changed packages only) ----
echo ""
echo -e "${YELLOW}[Layer 1] colcon build${NC}"
cd "$PROJECTPATH"
source /opt/ros/humble/setup.bash 2>/dev/null

# Only build spark_bringup + spark_rtab_map (the packages Wave 1 touched)
# Skip known-broken: openslam_gmapping, smach_msgs
BUILD_LOG=$(colcon build \
    --packages-select spark_bringup spark_rtab_map \
    --symlink-install 2>&1)
BUILD_RC=$?

if echo "$BUILD_LOG" | grep -q "Summary:.*packages finished"; then
    FINISHED=$(echo "$BUILD_LOG" | grep "Summary:" | grep -oP '\d+(?= packages finished)')
    FAILED=$(echo "$BUILD_LOG" | grep "Summary:" | grep -oP '\d+(?= package failed)' || echo "0")
    if [ "$FAILED" = "0" ] || [ -z "$FAILED" ]; then
        echo -e "${GREEN}✅ colcon build: $FINISHED packages finished${NC}"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}❌ colcon build: $FINISHED finished, $FAILED failed${NC}"
        FAIL=$((FAIL + 1))
        echo "$BUILD_LOG" | grep -A2 "Failed"
    fi
else
    echo -e "${RED}❌ colcon build failed${NC}"
    echo "$BUILD_LOG" | tail -10
    FAIL=$((FAIL + 1))
fi

source "$PROJECTPATH/install/setup.bash" 2>/dev/null

# ---- Layer 2: launch file syntax check ----
echo ""
echo -e "${YELLOW}[Layer 2] Launch 文件语法解析${NC}"

check_launch_syntax() {
    local rel_path="$1"
    local label="$2"
    local fullpath="$PROJECTPATH/$rel_path"
    
    if [ ! -f "$fullpath" ]; then
        echo -e "${RED}❌ $label — file missing: $rel_path${NC}"
        ERRORS="$ERRORS\n  $label: $rel_path missing"
        FAIL=$((FAIL + 1))
        return
    fi
    
    if python3 -c "
import ast, sys
try:
    with open('$fullpath') as f:
        ast.parse(f.read())
    sys.exit(0)
except SyntaxError as e:
    print(f'  SyntaxError: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1; then
        echo -e "${GREEN}✅ $label${NC}"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}❌ $label — syntax error${NC}"
        python3 -c "compile(open('$fullpath').read(), '$fullpath', 'exec')" 2>&1 | head -3
        ERRORS="$ERRORS\n  $label: syntax error in $rel_path"
        FAIL=$((FAIL + 1))
    fi
}

# onekey.sh 菜单 → 实际 launch 文件（直接用源码路径）
check_launch_syntax "src/spark/spark_teleop/launch/teleop.launch.py"                                    "菜单1  遥控"
check_launch_syntax "src/spark_app/spark_follower/launch/spark_follower.launch.py"                          "菜单2  跟随"
check_launch_syntax "src/spark_app/spark_slam/spark_slam_transfer/launch/start_build_map_gmapping.launch.py" "菜单3  建图-gmapping"
check_launch_syntax "src/spark_app/spark_slam/spark_slam_transfer/launch/start_build_map_cartographer.launch.py" "菜单3  建图-cartographer"
check_launch_syntax "src/spark_app/spark_slam/spark_slam_transfer/launch/start_build_map_slam_toolbox.launch.py" "菜单3  建图-toolbox"
check_launch_syntax "src/spark_app/spark_rtab_map/launch/start_rtabmap_rgbd_sync.launch.py"                "菜单4  3D建图"
check_launch_syntax "src/spark_app/spark_navigation2/launch/start_spark_navigation2.launch.py"              "菜单5  2D导航"
check_launch_syntax "src/spark_app/spark_rtab_map/launch/start_rtabmap_rgbd_sync.launch.py"                "菜单6  3D导航"
check_launch_syntax "src/spark_app/spark_carry/launch/spark_carry_cal.launch.py"                           "菜单7  标定"
check_launch_syntax "src/spark_app/spark_carry/launch/spark_carry_object_fix.launch.py"                    "菜单8  抓取"
check_launch_syntax "src/spark_app/spark_carry/launch/spark_carry_object.launch.py"                        "菜单8  抓取换位"
check_launch_syntax "src/spark_app/spark_yolov8/launch/spark_yolo_object.launch.py"                        "菜单9  YOLO物体"
check_launch_syntax "src/spark_app/spark_yolov8/launch/spark_yolo_pose.launch.py"                          "菜单9  YOLO姿态"
check_launch_syntax "src/spark_app/spark_voice/launch/vosk_nav.launch.py"                                  "菜单10 语音"
check_launch_syntax "src/spark/spark_test/launch/spark_test_five_minute.launch.py"                          "菜单98 老化5min"
check_launch_syntax "src/spark/spark_test/launch/spark_test_aging.launch.py"                                "菜单98 老化持续"
check_launch_syntax "src/spark_app/ros2-tensorflow/ros2-tensorflow/ros2_tensorflow/launch/spark_tensorflow_launch.py" "菜单9  TF"

# check the base bringup too
check_launch_syntax "src/spark/spark_bringup/launch/driver_bringup.launch.py"                             "底座  driver_bringup"

# ---- Layer 2b: quick param grep (no ros2 needed) ----
echo ""
echo -e "${YELLOW}[Layer 2b] 参数声明 grep 检查${NC}"

check_grep() {
    local file="$1"
    local pattern="$2"
    local label="$3"
    
    if grep -q "$pattern" "$PROJECTPATH/$file" 2>/dev/null; then
        echo -e "${GREEN}✅ $label${NC}"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}❌ $label — '$pattern' not found${NC}"
        ERRORS="$ERRORS\n  $label: '$pattern' not in $file"
        FAIL=$((FAIL + 1))
    fi
}

check_grep "src/spark/spark_bringup/launch/driver_bringup.launch.py" "camera_type_tel" "camera_type_tel in camera launch_args"
check_grep "src/spark/spark_bringup/launch/driver_bringup.launch.py" "lidar_type_tel"  "lidar_type_tel in lidar launch_args"
check_grep "src/spark_app/spark_rtab_map/launch/rtabmap.launch.py" "default_value=''" "rtabmap namespace=''"

# ---- Report ----
echo ""
echo "=========================================="
echo -e "  ${GREEN}✅ $PASS passed${NC}  ${RED}❌ $FAIL failed${NC}  ${YELLOW}⚠️  $SKIP skipped${NC}"
echo "=========================================="

if [ -n "$ERRORS" ]; then
    echo -e "\n${RED}失败详情:${NC}"
    echo -e "$ERRORS"
    echo ""
    echo "══════════════════════════════════════════"
    echo "  📋 Layer 3: 手动真机测试清单"
    echo "══════════════════════════════════════════"
    echo ""
    echo "请在实际机器人上运行以下菜单验证:"
    echo ""
    echo "  🔴 必须测:"
    echo "    bash src/onekey.sh → 菜单1 (遥控)"
    echo "    验证: 底盘能前后左右移动，相机/雷达数据正常"
    echo ""
    echo "  🟡 建议测:"
    echo "    bash src/onekey.sh → 菜单3 → gmapping (2D建图)"
    echo "    验证: 激光雷达建图正常，rviz 能看到 map topic"
    echo ""
    echo "  🟢 条件允许时测:"
    echo "    bash src/onekey.sh → 菜单5 (2D导航)"
    echo "    验证: 给定目标点后机器人能自主导航到达"
    exit 1
else
    echo ""
    echo "══════════════════════════════════════════"
    echo "  📋 Layer 3: 手动真机测试清单"
    echo "══════════════════════════════════════════"
    echo ""
    echo "自动化全部通过 ✅。请在机器人上验证以下最简路径:"
    echo ""
    echo "  🔴 必须测:"
    echo "    bash src/onekey.sh → 菜单1 (遥控)"
    echo "    预期: 底盘 wsad 移动正常，相机/雷达话题有数据"
    echo "    验证命令(另开终端):"
    echo "      ros2 topic list | grep -E 'odom|scan|color|camera'"
    echo ""
    echo "  本次改动涉及: driver_bringup 的 camera_type_tel/lidar_type_tel 参数传递"
    echo "  如果遥控正常，说明参数链路通了 ✅"
fi
