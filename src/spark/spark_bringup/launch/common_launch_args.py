# Copyright (c) 2026 NXROBO
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

"""
spark_bringup 公共 launch 参数模块。

所有应用 launch 文件通过 import 此模块来声明共用参数，
避免在 ~15 个 launch 文件里重复定义 camera_type_tel / lidar_type_tel /
enable_arm_tel / arm_type_tel / namespace。
"""

from launch.actions import DeclareLaunchArgument


def declare_common_arguments():
    """返回应用层共用的 5 个 launch 参数声明列表。"""
    return [
        DeclareLaunchArgument(
            'camera_type_tel',
            default_value='d435',
            choices=['d435', 'astra_pro'],
            description='camera type'
        ),
        DeclareLaunchArgument(
            'lidar_type_tel',
            default_value='ydlidar_g6',
            choices=['ydlidar_g2', 'ydlidar_g6'],
            description='lidar type'
        ),
        DeclareLaunchArgument(
            'enable_arm_tel',
            default_value='false',
            choices=['true', 'false'],
            description='Whether to run arm'
        ),
        DeclareLaunchArgument(
            'arm_type_tel',
            default_value='uarm',
            choices=['uarm', 'sagittarius_arm'],
            description='arm type'
        ),
        DeclareLaunchArgument(
            'namespace',
            default_value='',
            description='The namespace for multi-robot'
        ),
    ]
