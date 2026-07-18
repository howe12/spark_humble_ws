#!/usr/bin/env python3
"""03-2 深度跟随 — 一键启动文件

启动: D435 点云 + 深度跟随节点 + (可选)Rviz

用法:
  # 完整启动 (相机 + 跟随)
  ros2 launch vision_basics depth_follow.launch.py

  # 指定参数
  ros2 launch vision_basics depth_follow.launch.py \
    desired_distance:=1.5 max_linear:=0.4 enable_rviz:=true
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition
from launch_ros.actions import Node


def generate_launch_description():
    # ── 跟随参数 ──
    desired_distance = LaunchConfiguration('desired_distance', default='1.5')
    max_linear = LaunchConfiguration('max_linear', default='0.5')
    max_angular = LaunchConfiguration('max_angular', default='1.0')
    kp_distance = LaunchConfiguration('kp_distance', default='0.5')
    ki_distance = LaunchConfiguration('ki_distance', default='0.05')
    kd_distance = LaunchConfiguration('kd_distance', default='0.02')
    kp_yaw = LaunchConfiguration('kp_yaw', default='2.0')
    enable_rviz = LaunchConfiguration('enable_rviz', default='false')

    declared_args = [
        DeclareLaunchArgument('desired_distance', default_value='1.5',
                              description='期望跟随距离 (m)'),
        DeclareLaunchArgument('max_linear', default_value='0.5',
                              description='最大线速度 (m/s)'),
        DeclareLaunchArgument('max_angular', default_value='1.0',
                              description='最大角速度 (rad/s)'),
        DeclareLaunchArgument('kp_distance', default_value='0.5',
                              description='距离比例系数'),
        DeclareLaunchArgument('ki_distance', default_value='0.05',
                              description='距离积分系数'),
        DeclareLaunchArgument('kd_distance', default_value='0.02',
                              description='距离微分系数'),
        DeclareLaunchArgument('kp_yaw', default_value='2.0',
                              description='偏航比例系数'),
        DeclareLaunchArgument('enable_rviz', default_value='false',
                              description='是否启动 Rviz'),
    ]

    # ── 深度跟随节点 ──
    depth_follow_node = Node(
        package='vision_basics',
        executable='ros2_depth_follow',
        name='depth_follow',
        output='screen',
        parameters=[{
            'desired_distance': desired_distance,
            'max_linear': max_linear,
            'max_angular': max_angular,
            'kp_distance': kp_distance,
            'ki_distance': ki_distance,
            'kd_distance': kd_distance,
            'kp_yaw': kp_yaw,
        }],
    )

    # ── Rviz (可选) ──
    rviz_config = os.path.join(
        get_package_share_directory('vision_basics'), 'rviz', 'depth_follow.rviz')
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        condition=IfCondition(enable_rviz),
    )

    return LaunchDescription(declared_args + [depth_follow_node, rviz_node])
