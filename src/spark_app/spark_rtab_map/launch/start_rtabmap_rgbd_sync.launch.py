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
from launch.actions import (DeclareLaunchArgument, GroupAction,
                            IncludeLaunchDescription)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
import launch_ros.actions
from launch_ros.actions import Node
from launch.conditions import IfCondition,UnlessCondition
from launch.actions import TimerAction
from spark_bringup.common_launch_args import declare_common_arguments

def generate_launch_description():
    # -------------------- 1.功能包路径定义 --------------------
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    nav2_launch_file_dir = get_package_share_directory('nav2_bringup')
    spark_rtab_map_dir = get_package_share_directory('spark_rtab_map')
    spark_bringup_dir = get_package_share_directory('spark_bringup')


    # -------------------- 2.参数声明 --------------------
    declared_arguments = declare_common_arguments()
    declared_arguments.append(DeclareLaunchArgument(
        'start_bringup_rviz', 
        default_value='false',
        choices=['true', 'false'],
        description='Whether to start_bringup_rviz'
    ))   
    declared_arguments.append(DeclareLaunchArgument(
        'localization', default_value='false',
        description='Launch in localization mode.'
    ))
    
    # -------------------- 3.参数引用 --------------------
    enable_arm_tel = LaunchConfiguration('enable_arm_tel')
    arm_type_tel = LaunchConfiguration('arm_type_tel')
    camera_type_tel = LaunchConfiguration('camera_type_tel')
    lidar_type_tel = LaunchConfiguration('lidar_type_tel')  
    namespace = LaunchConfiguration('namespace')  
    use_sim_time = LaunchConfiguration('use_sim_time')
    start_slam_rviz = LaunchConfiguration('start_slam_rviz')  
    start_bringup_rviz = LaunchConfiguration('start_bringup_rviz')  
    localization = LaunchConfiguration('localization')


    # -------------------- 4.机器人总驱动程序 --------------------
    spark_bringup_launch = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(spark_bringup_dir, 'launch',
                                                       'driver_bringup.launch.py')),
            launch_arguments={
                              'enable_arm_tel': enable_arm_tel,
                              'arm_type_tel': arm_type_tel,
                              'camera_type_tel' : camera_type_tel,
                              'lidar_type_tel': lidar_type_tel,
                              'namespace': namespace,
                              'start_bringup_rviz': start_bringup_rviz,
                              }.items())

    # -------------------- 5.机器人控制程序 --------------------
    spark_teleop_node = launch_ros.actions.Node(
        package='spark_teleop',
        executable='keyboard_control.sh',  
        output='screen',
        emulate_tty=True,
        arguments=[
            namespace,  # 传递命名空间作为第一个参数
            '0.14',     # 线速度
            '0.5',      # 角速度
        ],
        )

    # -------------------- 6.SLAM程序 --------------------
    # 注意：当节点在namespace下运行时，frame_id应该是相对路径'base_footprint'
    # 而不是绝对路径'/namespace/base_footprint'
    slam_launch =  IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(spark_rtab_map_dir, 'launch',
                                                       'spark_rtabmap_rgbd_sync.launch.py')),
            launch_arguments={'localization': localization,'namespace': namespace}.items())


    # -------------------- 7.导航程序 --------------------
    nav2_launch =  IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(nav2_launch_file_dir, 'launch',
                                                       'navigation_launch.py')),
            launch_arguments={'namespace': namespace,}.items())


    # -------------------- 8.rviz --------------------
    rviz_config_dir = os.path.join(get_package_share_directory('spark_rtab_map'),
                                   'rviz', 'spark_rtabmap.rviz')
    spark_slam_rviz_node = launch_ros.actions.Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        namespace=namespace,
        arguments=['-d', rviz_config_dir],
        parameters=[{'use_sim_time': use_sim_time,}],
        output='screen',
        condition=UnlessCondition(enable_arm_tel),
        )

    spark_delay_map_nav_action = TimerAction(period=5.0, actions=[nav2_launch])
    spark_delay_rviz_action = TimerAction(period=7.0, actions=[spark_slam_rviz_node])

    nodes = [
        spark_bringup_launch,
        spark_teleop_node,
        slam_launch,
        # spark_delay_map_nav_action,
        spark_delay_rviz_action
    ]
    return LaunchDescription(declared_arguments + nodes)

