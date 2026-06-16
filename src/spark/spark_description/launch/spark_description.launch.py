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
from launch import LaunchDescription,LaunchContext
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from typing import List, Optional, Text, Union
from launch import SomeSubstitutionsType
from launch.substitutions import (
    Command,
    FindExecutable,
    LaunchConfiguration,
    PathJoinSubstitution,
    TextSubstitution,
)
from launch_ros.substitutions import FindPackageShare
import xacro
from launch.conditions import IfCondition, UnlessCondition
from launch_ros.descriptions import ParameterValue


def generate_launch_description():
    # -------------------- 1.功能包路径定义 --------------------
    rviz_config_dir = os.path.join(get_package_share_directory('spark_description'), 'rviz', 'urdf.rviz')


    # -------------------- 2.参数声明 --------------------
    declared_arg = []
    declared_arg.append(
         DeclareLaunchArgument(
            'start_description_rviz', 
            default_value='true',
            choices=['true', 'false'],
            description='Whether to start_description_rviz'
        )   
    )
    declared_arg.append(  
    DeclareLaunchArgument(
            'enable_arm_tel',
            default_value=TextSubstitution(text='false'),
            description=('Whether to enable arm'),
        )
    )
    declared_arg.append(
        DeclareLaunchArgument(
            'arm_type_tel',
            default_value='uarm',
            description=(
                'name of the robot (typically equal to `robot_model`, but could be anything).'
            ),
        )
    )
    declared_arg.append(
        DeclareLaunchArgument(
            'camera_type_tel',
            default_value='d435',
            description='model type of the spark Arm such as `d435` or `astra`.',
        )
    )
    declared_arg.append(
        DeclareLaunchArgument(
            'lidar_type_tel',
            default_value='ydlidar_g6',
            description='model type of the spark lidar such as `ydlidar_g6` or `ydlidar_g2`.',
        )
    )
    declared_arg.append(DeclareLaunchArgument(
            'namespace',
            default_value='',
            description='The name of namespace'
    ))
    declared_arg.append(DeclareLaunchArgument(
            'frame_prefix',
            default_value='',
            description='TF frame prefix for multi-robot scenarios (e.g. "robot1/"). Default empty for single-robot.'
    ))

    # -------------------- 3.参数引用 --------------------
    enable_arm_tel = LaunchConfiguration('enable_arm_tel')
    arm_type_tel = LaunchConfiguration('arm_type_tel')
    camera_type_tel = LaunchConfiguration('camera_type_tel')
    lidar_type_tel = LaunchConfiguration('lidar_type_tel')
    robot_description = LaunchConfiguration('robot_description')
    start_description_rviz = LaunchConfiguration('start_description_rviz')
    namespace = LaunchConfiguration('namespace')
    frame_prefix = LaunchConfiguration('frame_prefix')  

    remappings = [('/tf', 'tf'),
                ('/tf_static', 'tf_static')]


    # -------------------- 4.模型引用 --------------------
    pkg_path = os.path.join(get_package_share_directory('spark_description'))
    xacro_file = os.path.join(pkg_path,'urdf','spark_340.urdf.xacro')

    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            xacro_file,
            ' ',
            "enable_arm_tel:=",
            enable_arm_tel,
            " ",
            "arm_type_tel:=",
            arm_type_tel,
            " ",
            "camera_type_tel:=",
            camera_type_tel,
            " ",
            "lidar_type_tel:=",
            lidar_type_tel,
            " ",
            'namespace:=',
            namespace,
            ' ',
        ])

    robot_description = {"robot_description": robot_description_content}


    # -------------------- 5.robot_state --------------------
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        namespace=LaunchConfiguration('namespace'),
        parameters=[{
            'robot_description': robot_description_content,
            'frame_prefix': LaunchConfiguration('frame_prefix'),
        }],
        output={'both': 'log'},
        remappings=remappings,
    )

    # -------------------- 6.rviz2_node --------------------
    rviz2_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        condition=IfCondition(start_description_rviz),
        arguments=[
            '-d', rviz_config_dir,
        ],
        output={'both': 'log'},
    )

    nodes_to_start = [
        robot_state_publisher_node,
        rviz2_node,
    ]

    return LaunchDescription(declared_arg + nodes_to_start)