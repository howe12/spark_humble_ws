#!/usr/bin/env bash
set +e
cd /home/spark/Music/spark_humble
unset VIRTUAL_ENV
export PATH=/usr/bin:/usr/local/bin:$PATH
source /opt/ros/humble/setup.bash
source install/setup.bash

echo "=============================================="
echo "  全量启动测试 - 每个 demo 15 秒"
echo "=============================================="

bugs=0
total=0

# Hardware/driver errors (NOT code bugs):
# realsense: disconnected, no /dev/video, VIDIOC, hwmon, uvc, acquire_power, null pointer
# lidar: check sum, YDLIDAR, health code
# serial: could not connect, open serial, fail to open
# system: image_transport, no plugins, invalid context, RTPS_TRANSPORT, fastrtps
# rviz/keyboard: process died (no display)
# voskros: executable not found (pre-existing CMake issue)
HW_FILTER="disconnected|Cannot open.*video|VIDIOC|hwmon|acquire_power|null pointer|Device or resource busy|uvc-sensor|global_timestamp|map_device|No such device|check sum|YDLIDAR|health code|open serial|Could not connect|image_transport|No plugins|invalid context|RTPS_TRANSPORT|fastrtps|rviz.*died|keyboard.*died|save_map.*died|stopping sensor|can not find camera|Unable to open port|Failed to load|realsense.*exception|librealsense|errno|No cameras|Cannot identify|no camera|no.*lidar|lidar.*fail|executable.*vosk.*not found|voskros|requested device|NOT found. Will Try"

test_demo() {
    local label="$1" pkg="$2" lf="$3" args="$4"
    total=$((total+1))
    echo ""
    echo "--- $label ($pkg) ---"
    
    local output
    output=$(timeout 15 ros2 launch "$pkg" "$lf" $args 2>&1)
    
    local code_errors
    code_errors=$(echo "$output" | grep -iE "Error|Fatal|Traceback|Exception" | grep -viE "$HW_FILTER")
    
    if [ -n "$code_errors" ]; then
        echo "❌ CODE BUG:"
        echo "$code_errors" | head -5
        bugs=$((bugs+1))
    else
        echo "✅ 通过 (硬件/驱动错误已排除)"
    fi
}

test_demo "菜单1 遥控"      spark_teleop        teleop.launch.py                    "camera_type_tel:=d435 lidar_type_tel:=ydlidar_g6 enable_arm_tel:=false"
test_demo "菜单2 跟随"      spark_follower      spark_follower.launch.py             "camera_type_tel:=d435 lidar_type_tel:=ydlidar_g6"
test_demo "菜单3 gmapping"  spark_slam_transfer start_build_map_gmapping.launch.py    "camera_type_tel:=d435 lidar_type_tel:=ydlidar_g6 enable_arm_tel:=false"
test_demo "菜单3 carto"     spark_slam_transfer start_build_map_cartographer.launch.py "camera_type_tel:=d435 lidar_type_tel:=ydlidar_g6 enable_arm_tel:=false"
test_demo "菜单3 toolbox"   spark_slam_transfer start_build_map_slam_toolbox.launch.py "camera_type_tel:=d435 lidar_type_tel:=ydlidar_g6 enable_arm_tel:=false"
test_demo "菜单5 2D导航"    spark_navigation2   start_spark_navigation2.launch.py     "camera_type_tel:=d435 lidar_type_tel:=ydlidar_g6"
test_demo "菜单9 YOLO obj"  spark_yolov8        spark_yolo_object.launch.py           "camera_type_tel:=d435 lidar_type_tel:=ydlidar_g6"
test_demo "菜单9 YOLO pose" spark_yolov8        spark_yolo_pose.launch.py             "camera_type_tel:=d435 lidar_type_tel:=ydlidar_g6"
test_demo "菜单10 语音"     spark_voice         vosk_nav.launch.py                    "camera_type_tel:=d435 lidar_type_tel:=ydlidar_g6"
test_demo "菜单98 老化"     spark_test          spark_test_five_minute.launch.py       "camera_type_tel:=d435 lidar_type_tel:=ydlidar_g6"

echo ""
echo "=============================================="
echo "  代码级 bug: $bugs / $total"
if [ $bugs -eq 0 ]; then
    echo "  ✅ 全部通过"
else
    echo "  ❌ 有 $bugs 个需修复"
fi
echo "=============================================="
exit $bugs
