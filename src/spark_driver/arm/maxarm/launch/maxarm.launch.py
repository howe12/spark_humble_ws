from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    """
    启动 MaxArm 机械臂的读取和写入节点
    """
    return LaunchDescription([
        # MaxArm 读取节点 - 读取机械臂状态并发布
        Node(
            package='maxarm',
            executable='maxarm_read_node',
            name='maxarm_read_node',
            output='screen',
            emulate_tty=True,
        ),
        
        # MaxArm 写入节点 - 接收控制命令并发送到机械臂
        Node(
            package='maxarm',
            executable='maxarm_write_node',
            name='maxarm_write_node',
            output='screen',
            emulate_tty=True,
        ),
    ])

