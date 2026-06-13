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
    spark_slam_dir = get_package_share_directory('slam_gmapping')
    spark_bringup_dir = get_package_share_directory('spark_bringup')

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
        'use_sim_time',
        default_value='false',
        description='Use simulation (Gazebo) clock if true'
    ))
    declared_arguments.append(DeclareLaunchArgument(
        'start_slam_rviz', 
        default_value='true',
        choices=['true', 'false'],
        description='Whether to start_slam_rviz'
    ))   
    declared_arguments.append(DeclareLaunchArgument(
        'start_bringup_rviz', 
        default_value='false',
        choices=['true', 'false'],
        description='Whether to start_bringup_rviz'
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
    slam_launch =  IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(spark_slam_dir, 'launch',
                                                       'slam_gmapping.launch.py')),
                                    launch_arguments={'namespace': namespace,}.items())

    # -------------------- 7.Map保存 --------------------
    spark_save_map_node = launch_ros.actions.Node(
        package='spark_slam_transfer',
        executable='save_map_cmd.sh',  
        output='screen',
        emulate_tty=True,
        arguments=[namespace],
        )

    # -------------------- 8.rviz --------------------
    rviz_config_dir = os.path.join(get_package_share_directory('spark_slam_transfer'),
                                   'rviz', 'spark_slam.rviz')
    spark_slam_rviz_node = launch_ros.actions.Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_dir],
        parameters=[{'use_sim_time': use_sim_time,
                     'namespace': namespace,}],
        output='screen',
        condition=IfCondition(start_slam_rviz),
        )

    spark_delay_slam_action = TimerAction(period=1.0, actions=[slam_launch])
    spark_delay_save_map_action = TimerAction(period=1.0, actions=[spark_save_map_node])

    nodes = [
        spark_bringup_launch,
        spark_teleop_node,
        spark_delay_slam_action,
        spark_delay_save_map_action,
        spark_slam_rviz_node
    ]
    return LaunchDescription(declared_arguments + nodes)
