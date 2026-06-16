# Copyright 2024 NXROBO, Inc.
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
from launch.actions import (DeclareLaunchArgument, GroupAction,
                            IncludeLaunchDescription, SetEnvironmentVariable)
from launch.conditions import IfCondition, LaunchConfigurationEquals
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node, PushRosNamespace
from spark_bringup.common_launch_args import declare_common_arguments

def generate_launch_description():
    # -------------------- 1.功能包路径定义 --------------------
    spark_base_dir = get_package_share_directory('spark_base')
    spark_description_dir = get_package_share_directory('spark_description')
    camera_driver_transfer_dir = get_package_share_directory('camera_driver_transfer')
    lidar_driver_transfer_dir = get_package_share_directory('lidar_driver_transfer')
    
    stdout_linebuf_envvar = SetEnvironmentVariable(
        'RCUTILS_LOGGING_BUFFERED_STREAM', '1')
    # -------------------- 2.参数声明 --------------------
    declared_arguments = declare_common_arguments()

    # 添加所有参数声明到列表
    declared_arguments.append(DeclareLaunchArgument(
        'serial_port', 
        default_value='/dev/sparkBase',
        description='serial port name:/dev/sparkBase or /dev/ttyUSBx'
    ))
    declared_arguments.append(DeclareLaunchArgument(
        'start_base', 
        default_value='true',
        choices=['true', 'false'],
        description='Whether to run base'
    ))
    declared_arguments.append(DeclareLaunchArgument(
        'start_camera', 
        default_value='true',
        choices=['true', 'false'],
        description='Whether to run camera'
    ))
    declared_arguments.append(DeclareLaunchArgument(
        'start_lidar', 
        default_value='true',
        choices=['true', 'false'],
        description='Whether to run lidar'
    ))
    declared_arguments.append(DeclareLaunchArgument(
        'dp_rgist', 
        default_value='true',
        choices=['true', 'false'],
        description='Whether to run dp_rgist'
    ))
    declared_arguments.append(DeclareLaunchArgument(
        'start_bringup_rviz', 
        default_value='true',
        choices=['true', 'false'],
        description='Whether to start_bringup_rviz'
    ))   
    declared_arguments.append(DeclareLaunchArgument(
        'frame_prefix',
        default_value='',
        description='TF frame prefix for multi-robot (e.g. "robot1/"). Empty for single-robot.'
    ))

    # -------------------- 3.参数引用 --------------------
    serial_port = LaunchConfiguration('serial_port')
    enable_arm_tel = LaunchConfiguration('enable_arm_tel')
    arm_type_tel = LaunchConfiguration('arm_type_tel')
    start_base = LaunchConfiguration('start_base')
    start_camera = LaunchConfiguration('start_camera')
    start_lidar = LaunchConfiguration('start_lidar')
    camera_type_tel = LaunchConfiguration('camera_type_tel')
    lidar_type_tel = LaunchConfiguration('lidar_type_tel')
    dp_rgist = LaunchConfiguration('dp_rgist')
    start_bringup_rviz = LaunchConfiguration('start_bringup_rviz')
    namespace = LaunchConfiguration('namespace')
    frame_prefix = LaunchConfiguration('frame_prefix')
    # use_namespace = PythonExpression(["'True' if '", namespace, "' != '' else 'False'"])

    # -------------------- 4.机器人模型程序 --------------------
    robot_description_node = GroupAction([
        PushRosNamespace(namespace),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(spark_description_dir, 'launch',
                                                        'spark_description.launch.py')),
            launch_arguments={  'camera_type_tel': camera_type_tel,
                                'lidar_type_tel': lidar_type_tel,
                                'enable_arm_tel': enable_arm_tel,
                                'start_description_rviz' : 'false',
                                'arm_type_tel': arm_type_tel,
                                'namespace': namespace,
                                'frame_prefix': frame_prefix}.items())
    ])

    # -------------------- 5.机器人底盘驱动程序 --------------------
    spark_base_node = GroupAction([
        PushRosNamespace(namespace),
        IncludeLaunchDescription(
                PythonLaunchDescriptionSource(os.path.join(spark_base_dir, 'launch',
                                                           'spark_base.launch.py')),
                condition=IfCondition(start_base),
                launch_arguments={'serial_port': serial_port,
                                  'namespace': namespace,
                                  'frame_prefix': frame_prefix
                                    }.items())
    ])
    
    # -------------------- 6.机器人相机驱动程序 --------------------
    spark_camera_node = GroupAction([
        PushRosNamespace(namespace),
        IncludeLaunchDescription(
                PythonLaunchDescriptionSource(os.path.join(camera_driver_transfer_dir, 'launch',
                                                           'start_camera.launch.py')),
                condition=IfCondition(start_camera),
                launch_arguments={'dp_rgist': dp_rgist,
                                  'namespace': namespace,
                                  'camera_type_tel': camera_type_tel}.items())
    ])

    # -------------------- 7.机器人雷达驱动程序 --------------------
    spark_lidar_node = GroupAction([
        PushRosNamespace(namespace),
        IncludeLaunchDescription(
                PythonLaunchDescriptionSource(os.path.join(lidar_driver_transfer_dir, 'launch',
                                                           'start_lidar.launch.py')),
                condition=IfCondition(start_lidar),
                launch_arguments={'namespace': namespace,
                                  'lidar_type_tel': lidar_type_tel}.items())
    ])

    # -------------------- 8.Rviz可视化界面 --------------------
    rviz_config_dir = os.path.join(get_package_share_directory('spark_bringup'), 'rviz', 'urdf.rviz')
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output = 'screen',
        arguments=['-d', rviz_config_dir],
        namespace=namespace,
        condition=IfCondition(start_bringup_rviz),
        parameters=[{'use_sim_time': False}]
        )
    

    # Create the launch description and populate
    nodes = [
        robot_description_node,
        spark_base_node,
        spark_camera_node,
        spark_lidar_node,
        rviz_node
    ]

    return LaunchDescription(declared_arguments + nodes)
