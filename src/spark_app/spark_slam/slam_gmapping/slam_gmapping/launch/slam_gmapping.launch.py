from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration
from launch.substitutions import EnvironmentVariable
import launch.actions
import launch_ros.actions
from launch.actions import (DeclareLaunchArgument, GroupAction,
                            IncludeLaunchDescription)


def generate_launch_description():
    declared_arguments = []
    declared_arguments.append(DeclareLaunchArgument(
        'namespace', 
        default_value='',
        description='The name of namespace'
    ))  

    namespace = launch.substitutions.LaunchConfiguration('namespace')  
    use_sim_time = launch.substitutions.LaunchConfiguration('use_sim_time', default='false')

    slam_node = launch_ros.actions.Node(
            package='slam_gmapping', 
            executable='slam_gmapping', 
            output='screen', 
            namespace = launch.substitutions.LaunchConfiguration('namespace'),
            parameters=[{'use_sim_time':use_sim_time,}]
            )
            
    nodes = [slam_node]
    return LaunchDescription(declared_arguments + nodes)
