# Copyright (c) 2022 NXROBO
#
# /* Author: litian.zhuang */
# /* email: litian.zhuang@nxrobo.com */
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
                            IncludeLaunchDescription, SetEnvironmentVariable)
from launch.conditions import IfCondition, LaunchConfigurationEquals
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace
from colorama import init, Fore, Style  

#摄像头列表字典
camera_type_dict = {"2bc5:0403": "astrapro", "2bc5:0401": "astra", "8086:0b07": "d435"}

#执行命令行，返回输出值
def execCmd(cmd):
    r = os.popen(cmd)
    text = r.read()
    r.close()
    return text

#执行命令行，返回输出值  
def get_camera_type():
    for i in camera_type_dict:
        # print(i, camera_type_dict[i])
        cmd = "lsusb -d " + i
        # print(cmd)
        result = execCmd(cmd)

        if len(result) !=0:
            print(Fore.YELLOW + "camera is " + Style.RESET_ALL + Fore.GREEN + camera_type_dict[i] + Style.RESET_ALL)  #
            return camera_type_dict[i]
    print(Fore.RED + "ERROR: can not find camera,set d435 as default!" + Style.RESET_ALL)
    return "d435"    



def generate_launch_description():
    # -------------------- 1.功能包路径定义 --------------------
    camera_driver_transfer_dir = get_package_share_directory('camera_driver_transfer')
    default_camera_name = get_camera_type()

    # -------------------- 2.参数声明 --------------------
    declared_arguments = []
    declared_arguments.append(DeclareLaunchArgument(
        'dp_rgist', 
        default_value='false',
        choices=['true', 'false'],
        description='Whether to run dp_rgist'
    ))
        
    declared_arguments.append(DeclareLaunchArgument(
        'start_camera_rviz', 
        default_value='false',
        choices=['true', 'false'],
        description='Whether to run start_camera_rviz'
    ))

    declared_arguments.append(DeclareLaunchArgument(
        'camera_type_tel', 
        default_value=default_camera_name,
        description='camera type'
    ))
    declared_arguments.append(DeclareLaunchArgument(
        'namespace', 
        default_value='',
        description='The name of namespace'
    ))  

    

    # -------------------- 3.参数引用 --------------------
    camera_type_tel = LaunchConfiguration('camera_type_tel')
    dp_rgist = LaunchConfiguration('dp_rgist')   
    start_camera_rviz = LaunchConfiguration('start_camera_rviz')
    namespace = LaunchConfiguration('namespace')    
    stdout_linebuf_envvar = SetEnvironmentVariable(
        'RCUTILS_LOGGING_BUFFERED_STREAM', '1')

    # -------------------- 4.机器人选择对应相机驱动 --------------------
    camera_type_launch = (camera_driver_transfer_dir, '/launch/', camera_type_tel, '.launch.py')
    camera_launch = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(camera_type_launch),
            launch_arguments={'namespace': namespace,}.items())

    nodes = [
        camera_launch,
    ]
    return LaunchDescription(declared_arguments + nodes)

