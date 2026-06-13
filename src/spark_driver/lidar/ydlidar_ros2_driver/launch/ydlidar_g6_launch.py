#!/usr/bin/python3
# Copyright 2020, EAIBOT
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

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch_ros.actions import LifecycleNode
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch.actions import LogInfo
from launch.conditions import IfCondition, LaunchConfigurationEquals

import lifecycle_msgs.msg
import os


def generate_launch_description():
    # -------------------- 1.功能包路径定义 --------------------
    share_dir = get_package_share_directory('ydlidar_ros2_driver')

    # -------------------- 2.参数声明 --------------------
    declared_arguments = []
    declared_arguments.append(DeclareLaunchArgument(
        'params_file',
        default_value=os.path.join(
        share_dir, 'params', 'ydlidar_g6.yaml'),
        description='FPath to the ROS2 parameters file to use.'
    ))
    declared_arguments.append(DeclareLaunchArgument(
        'start_lidar_rviz', 
        default_value='false',
        choices=['true', 'false'],
        description='Whether to run start_lidar_rviz'
    ))
    declared_arguments.append(DeclareLaunchArgument(
        'namespace', 
        default_value='',
        description='The name of namespace'
    ))  

    # -------------------- 3.参数引用 --------------------
    parameter_file = LaunchConfiguration('params_file')
    rviz_config_file = os.path.join(share_dir, 'config','ydlidar.rviz')
    start_lidar_rviz = LaunchConfiguration('start_lidar_rviz')   
    namespace = LaunchConfiguration('namespace')    


    # -------------------- 4.雷达节点 --------------------
    lidar_node = LifecycleNode(package='ydlidar_ros2_driver',
                                executable='ydlidar_ros2_driver_node',
                                name='ydlidar_ros2_driver_node',
                                output='screen',
                                emulate_tty=True,
                                namespace=namespace,
                                parameters=[parameter_file],
                                
                                )
    # -------------------- 5.rviz2节点 --------------------
    rviz2_node = Node(package='rviz2',
                    executable='rviz2',
                    name='rviz2',
                    condition=IfCondition(start_lidar_rviz),
                    arguments=['-d', rviz_config_file],
                    )
    
    nodes = [
        lidar_node,
        rviz2_node
    ]
    return LaunchDescription(declared_arguments + nodes)
