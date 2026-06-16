# Copyright (c) 2026 NXROBO
#
# /* Author: haijie.huo */
# /* email: haijie.huo@nxrobo.com */
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
# 
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription

from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
import launch_ros.actions
from launch_ros.actions import Node

def generate_launch_description():
    # -------------------- 1.功能包路径定义 --------------------
    swiftpro_dir = get_package_share_directory('swiftpro')

    # -------------------- 2.参数声明 --------------------
    declared_arguments = []
    declared_arguments.append(DeclareLaunchArgument(
        'namespace', 
        default_value='',
        description='The name of namespace'
    )) 

    # -------------------- 3.参数引用 --------------------
    namespace = LaunchConfiguration('namespace')  

    swiftpro_write_node = launch_ros.actions.Node(
        package='swiftpro',
        executable='swiftpro_write_node',  
        output='screen',
        namespace = namespace,
        emulate_tty=True,
        )
    swiftpro_rviz_node = launch_ros.actions.Node(
        package='swiftpro',
        executable='swiftpro_rviz_node',  
        output='screen',
        namespace = namespace,
        emulate_tty=True,
        )

    nodes = [
        swiftpro_write_node,
        swiftpro_rviz_node,
    ]
    return LaunchDescription(declared_arguments + nodes)