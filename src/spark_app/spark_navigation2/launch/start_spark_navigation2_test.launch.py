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
from launch.conditions import IfCondition
from launch.actions import TimerAction

def generate_launch_description():
    # -------------------- 1.功能包路径定义 --------------------
    spark_navigation2_dir = get_package_share_directory('spark_navigation2')
    spark_bringup_dir = get_package_share_directory('spark_bringup')
    spark_slam_dir = get_package_share_directory('slam_toolbox')
    base_map_dir = os.path.join(get_package_share_directory('spark_navigation2'),'map')

    # -------------------- 2.参数声明 --------------------
    declared_arguments = []
    declared_arguments.append(DeclareLaunchArgument(
        'camera_type_tel', 
        default_value='d435',
        description='camera type'
    ))
    declared_arguments.append(DeclareLaunchArgument(
        'lidar_type_tel', 
        default_value='ydlidar_g6',
        description='lidar type'
    ))
    declared_arguments.append(DeclareLaunchArgument(
        'enable_arm_tel', 
        default_value='false',
        choices=['true', 'false'],
        description='Whether to run arm'
    ))
    declared_arguments.append(DeclareLaunchArgument(
        'arm_type_tel', 
        default_value='uarm',
        choices=['uarm', 'sagittarius_arm'],
        description='arm name'
    ))
    declared_arguments.append(DeclareLaunchArgument(
        'namespace', 
        default_value='',
        description='The name of namespace'
    ))   
    declared_arguments.append(DeclareLaunchArgument(
        'start_bringup_rviz', 
        default_value='false',
        choices=['true', 'false'],
        description='Whether to start_bringup_rviz'
    )) 
    # declared_arguments.append(DeclareLaunchArgument( 
    #     'base_map_dir',
    #     default_value=base_map_dir,
    #     description='Full path to map file to load'
    # ))
    # declared_arguments.append(DeclareLaunchArgument( 
    #     'map_name',
    #     default_value='map1',
    #     description='Full path to map file to load'
    # ))

    # -------------------- 3.参数引用 --------------------
    enable_arm_tel = LaunchConfiguration('enable_arm_tel')
    arm_type_tel = LaunchConfiguration('arm_type_tel')
    camera_type_tel = LaunchConfiguration('camera_type_tel')
    lidar_type_tel = LaunchConfiguration('lidar_type_tel')  
    namespace = LaunchConfiguration('namespace')  
    start_bringup_rviz = LaunchConfiguration('start_bringup_rviz')
    base_map_dir = LaunchConfiguration('base_map_dir')
    map_name = LaunchConfiguration('map_name')  

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

    # -------------------- 5.机器人导航程序 --------------------
    spark_navigation2_launch = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(spark_navigation2_dir, 'launch',
                                                       'navigation2.launch.py')),
                                            launch_arguments={
                                                              'namespace': namespace,
                                                            #   'base_map_dir': base_map_dir,
                                                            #   'map_name': map_name,
                                                             }.items())

        
    # -------------------- 6.机器人SLAM程序 --------------------
    spark_slam_launch = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(spark_slam_dir, 'launch',
                                                       'online_sync_launch.py')),
                                            launch_arguments={'namespace': namespace,}.items())
            

    spark_delay_navigation2 = TimerAction(period=5.0, actions=[spark_navigation2_launch])
    spark_delay_slam_action = TimerAction(period=8.0, actions=[spark_slam_launch])
    

    nodes = [
        spark_bringup_launch,
        spark_delay_navigation2,
        # spark_delay_slam_action,
    ]
    return LaunchDescription(declared_arguments + nodes)
