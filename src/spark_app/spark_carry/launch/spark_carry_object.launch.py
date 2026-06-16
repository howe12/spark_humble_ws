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
                            IncludeLaunchDescription, TimerAction)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
import launch_ros.actions
from launch_ros.actions import Node
from launch.substitutions import PythonExpression
from spark_bringup.common_launch_args import declare_common_arguments



def generate_launch_description():
    # -------------------- 1.功能包路径定义 --------------------
    swiftpro_driver_dir = get_package_share_directory('swiftpro')
    spark_carry_dir = get_package_share_directory('spark_carry')
    spark_bringup_dir = get_package_share_directory('spark_bringup')

    # -------------------- 2.参数声明 --------------------
    # LaunchConfiguration refs before DeclareLaunchArgument (color_topic_name uses camera_type_tel)
    enable_arm_tel = LaunchConfiguration('enable_arm_tel')
    arm_type_tel = LaunchConfiguration('arm_type_tel')
    camera_type_tel = LaunchConfiguration('camera_type_tel')
    lidar_type_tel = LaunchConfiguration('lidar_type_tel')  
    namespace = LaunchConfiguration('namespace')  
    use_sim_time = LaunchConfiguration('use_sim_time')
    start_slam_rviz = LaunchConfiguration('start_slam_rviz')  
    start_bringup_rviz = LaunchConfiguration('start_bringup_rviz')  
    localization = LaunchConfiguration('localization')
    color_topic_name = LaunchConfiguration('color_topic_name')
    
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
    declared_arguments.append(DeclareLaunchArgument(
        'color_topic_name', default_value=PythonExpression(["'camera/color/image_raw' if '", camera_type_tel, "' == 'd435' else 'camera/rgb/image_raw'"]),
        description='Launch in localization mode.'
    ))
    
   
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

    # -------------------- 5.机械臂控制程序 --------------------
    uarm_launch = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(swiftpro_driver_dir, 'launch',
                                                       'pro_control_nomoveit.launch.py')),
            launch_arguments={
                                'namespace': namespace,
                             }.items())

    # -------------------- 6.机械臂控制程序 --------------------
    hsv_processor_node = launch_ros.actions.Node(
        package='spark_carry',
        executable='hsv_processor',  
        namespace=namespace,
        output='screen',
    )    

    # -------------------- 7.机械臂抓取物体 --------------------
    grasp_object_node = launch_ros.actions.Node(
        package='spark_carry',
        executable='grasp_object', 
        namespace=namespace, 
        output='screen',
    )

    # 设置延时启动节点
    delay_hsv_processor_node = TimerAction(period=5.0,actions=[hsv_processor_node])


    nodes = [
        spark_bringup_launch,
        uarm_launch,
        delay_hsv_processor_node,
        grasp_object_node
    ]
    return LaunchDescription(declared_arguments + nodes)