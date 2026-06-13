# Copyright (c) 2025 NXROBO
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

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,LogInfo
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, TextSubstitution, Command
from launch.actions import TimerAction

def generate_launch_description():
    # -------------------- 1.功能包路径定义 --------------------
    base_map_dir = os.path.join(get_package_share_directory('spark_navigation2'),'map')
    nav2_params_file = os.path.join(get_package_share_directory('spark_navigation2'),'param','spark_navigation.yaml')
    nav2_launch_file_dir = os.path.join(get_package_share_directory('nav2_bringup'), 'launch')
    rviz_config_dir = os.path.join(get_package_share_directory('spark_navigation2'),'rviz','spark_navigation2.rviz')
    
    # -------------------- 2.参数声明 --------------------
    declared_arguments = []
    declared_arguments.append(DeclareLaunchArgument(
        'namespace', 
        default_value='',
        description='The name of namespace'
    ))   
    declared_arguments.append(DeclareLaunchArgument( 
        'base_map_dir',
        default_value=base_map_dir,
        description='Full path to map file to load'
    ))
    declared_arguments.append(DeclareLaunchArgument( 
        'map_name',
        default_value='map',
        description='Full path to map file to load'
    ))
    declared_arguments.append(DeclareLaunchArgument( 
        'nav2_params_file',
        default_value=nav2_params_file,
        description='Full path to param file to load'
    ))
    declared_arguments.append(DeclareLaunchArgument(    
        'use_sim_time',
        default_value='false',
        description='Use simulation (Gazebo) clock if true'
    ))

    # -------------------- 3.参数引用 --------------------
    use_sim_time = LaunchConfiguration('use_sim_time')
    base_map_dir = LaunchConfiguration('base_map_dir')
    map_name = LaunchConfiguration('map_name')
    param_dir = LaunchConfiguration('nav2_params_file')
    namespace = LaunchConfiguration('namespace')


    # 用Command拼接
    full_map_filename = Command(
        [
            "python3 -c \"",
            "map_name = '", map_name, "'; ",  # 读取map_name值（如map）
            "print(f'{map_name}.yaml', end='')", 
            "\""
        ]
    )

    # -------------------- 核心修改：用PathJoinSubstitution替代os.path.join --------------------
    # 效果等价于：os.path.join(base_map_dir, map_name)，但兼容LaunchConfiguration
    map_path = PathJoinSubstitution([base_map_dir, full_map_filename])
    log_map_path = LogInfo(msg=["[运行时] 最终map_path：", map_path])
    # log_map_name = LogInfo(msg=["[运行时] 实际map_name值：", full_map_filename])

    # -------------------- 4.导航 --------------------
    nav2_launch = IncludeLaunchDescription(PythonLaunchDescriptionSource([nav2_launch_file_dir, '/bringup_launch.py']),
            launch_arguments={
                'map': map_path,
                'use_sim_time': use_sim_time,
                'nav2_params_file': param_dir,
                'namespace': namespace}.items()
        )

    # -------------------- 5.rviz --------------------
    rviz2_node = Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            namespace=namespace,
            arguments=['-d', rviz_config_dir],
            parameters=[{'use_sim_time': use_sim_time}],
            output='screen')

    spark_delay_navigation2 = TimerAction(period=5.0, actions=[nav2_launch])

    nodes = [
        spark_delay_navigation2,
        rviz2_node,
    ]
    return LaunchDescription(declared_arguments + [log_map_path] + nodes )
