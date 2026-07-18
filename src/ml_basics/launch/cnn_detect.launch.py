# Copyright 2024 NXROBO
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""4.4.2 CNN 实时手写数字识别 — 启动文件

用法:
  # 完整启动 (含相机驱动)
  ros2 launch ml_basics cnn_detect.launch.py

  # 指定相机/雷达型号
  ros2 launch ml_basics cnn_detect.launch.py camera_type_tel:=d435 lidar_type_tel:=ydlidar_g6
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # ── 参数 ──
    camera_type_tel = LaunchConfiguration('camera_type_tel', default='d435')
    lidar_type_tel = LaunchConfiguration('lidar_type_tel', default='ydlidar_g6')
    namespace = LaunchConfiguration('namespace', default='')
    confidence_threshold = LaunchConfiguration('confidence_threshold', default='0.7')

    declared_args = [
        DeclareLaunchArgument('camera_type_tel', default_value='d435',
                              description='Camera type: d435 / astrapro / astra'),
        DeclareLaunchArgument('lidar_type_tel', default_value='ydlidar_g6',
                              description='Lidar type: ydlidar_g6 / ydlidar_g2'),
        DeclareLaunchArgument('namespace', default_value='',
                              description='ROS2 namespace'),
        DeclareLaunchArgument('confidence_threshold', default_value='0.7',
                              description='Minimum confidence to report a digit'),
    ]

    # ── 驱动 bringup (相机 + 底盘 + 雷达) ──
    spark_bringup_dir = get_package_share_directory('spark_bringup')
    driver_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(spark_bringup_dir, 'launch', 'driver_bringup.launch.py')),
        launch_arguments={
            'camera_type_tel': camera_type_tel,
            'lidar_type_tel': lidar_type_tel,
            'namespace': namespace,
            'enable_arm_tel': 'false',
            'start_base': 'false',
            'start_lidar': 'false',
        }.items(),
    )

    # ── CNN 检测节点 ──
    cnn_node = Node(
        package='ml_basics',
        executable='ros2_cnn_detect',
        name='cnn_detect',
        output='screen',
        namespace=namespace,
        parameters=[{
            'confidence_threshold': confidence_threshold,
        }],
    )

    return LaunchDescription(declared_args + [driver_bringup, cnn_node])
