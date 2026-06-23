"""Launch VLN client with base + camera drivers for Spark-I robot."""
import os
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace


def generate_launch_description():
    # ── Package paths ──
    spark_base_dir = get_package_share_directory('spark_base')
    camera_driver_transfer_dir = get_package_share_directory('camera_driver_transfer')

    # ── Arguments ──
    args = {}

    # VLN params
    args['vln_l40_url'] = DeclareLaunchArgument('l40_url', default_value='http://localhost:18001')
    args['vln_l40_host'] = DeclareLaunchArgument('l40_host', default_value='120.209.70.195')
    args['vln_l40_ssh_port'] = DeclareLaunchArgument('l40_ssh_port', default_value='30456')
    args['vln_l40_remote_port'] = DeclareLaunchArgument('l40_remote_port', default_value='8443')
    args['vln_l40_local_port'] = DeclareLaunchArgument('l40_local_port', default_value='18001')
    args['vln_linear_speed'] = DeclareLaunchArgument('linear_speed', default_value='0.2')
    args['vln_angular_speed'] = DeclareLaunchArgument('angular_speed', default_value='0.5')
    args['vln_step_interval'] = DeclareLaunchArgument('step_interval', default_value='1.5')

    # Toggle switches
    args['start_base'] = DeclareLaunchArgument('start_base', default_value='true', choices=['true', 'false'])
    args['start_camera'] = DeclareLaunchArgument('start_camera', default_value='true', choices=['true', 'false'])
    args['start_vln'] = DeclareLaunchArgument('start_vln', default_value='true', choices=['true', 'false'])

    # Base params
    args['serial_port'] = DeclareLaunchArgument('serial_port', default_value='/dev/sparkBase')
    args['namespace'] = DeclareLaunchArgument('namespace', default_value='')

    # ── Resolve ──
    lcf = LaunchConfiguration  # alias

    # ── 1. Chassis driver ──
    spark_base_node = GroupAction([
        PushRosNamespace(lcf('namespace')),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(spark_base_dir, 'launch', 'spark_base.launch.py')),
            condition=IfCondition(lcf('start_base')),
            launch_arguments={'serial_port': lcf('serial_port'), 'namespace': lcf('namespace')}.items())
    ])

    # ── 2. Camera driver ──
    spark_camera_node = GroupAction([
        PushRosNamespace(lcf('namespace')),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(camera_driver_transfer_dir, 'launch', 'start_camera.launch.py')),
            condition=IfCondition(lcf('start_camera')),
            launch_arguments={'namespace': lcf('namespace')}.items())
    ])

    # ── 3. VLN client ──
    vln_node = Node(
        package='spark_vln',
        executable="/home/spark/Music/spark_humble/install/spark_vln/bin/vln_client",
        name='vln_client',
        output='screen',
        condition=IfCondition(lcf('start_vln')),
        namespace=lcf('namespace'),
        parameters=[{
            'l40_url': lcf('l40_url'),
            'l40_host': lcf('l40_host'),
            'l40_ssh_port': lcf('l40_ssh_port'),
            'l40_remote_port': lcf('l40_remote_port'),
            'l40_local_port': lcf('l40_local_port'),
            'linear_speed': lcf('linear_speed'),
            'angular_speed': lcf('angular_speed'),
            'step_interval': lcf('step_interval'),
        }],
    )

    return LaunchDescription(list(args.values()) + [
        spark_base_node,
        spark_camera_node,
        vln_node,
    ])
