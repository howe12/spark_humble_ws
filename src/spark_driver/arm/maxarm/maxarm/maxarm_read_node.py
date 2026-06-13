#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from maxarm_msg.msg import Position

from maxarm.MaxArm_ctl import MaxArm_ctl
import time

class MaxArmReadNode(Node):
    def __init__(self):
        super().__init__('maxarm_read_node')
        self.get_logger().info('MaxArm读取节点已启动')
        
        # 机械臂状态读取端口
        self.ma = MaxArm_ctl(device = "/dev/ttyUSB2", baudrate=9600)

        # 机械臂末端当前位置坐标
        self.position_pub_ = self.create_publisher(Position, "read_maxarm_position", 1)

        # 机械臂总线舵机位置
        self.joint_pub_ = self.create_publisher(Position, "read_maxarm_joint", 1)

        # 定时器定时发布数据
        self.timer = self.create_timer(timer_period_sec=0.5, callback=self.timer_callback)

    def timer_callback(self):
        # 读取末端位置坐标
        xyz = self.ma.read_xyz()
        # print(xyz)
        pos_msg = Position()
        pos_msg.x = xyz[0]
        pos_msg.y = xyz[1]
        pos_msg.z = xyz[2]
        self.position_pub_.publish(pos_msg)
        # self.get_logger().debug(f'发布末端位置: x={pos_msg.x}, y={pos_msg.y}, z={pos_msg.z}')

        # time.sleep(1)
        # 读取舵机当前位置
        angles = self.ma.read_angles()
        joint_msg = Position()
        joint_msg.x = angles[0]
        joint_msg.y = angles[1]
        joint_msg.z = angles[2]
        self.joint_pub_.publish(joint_msg)
        # self.get_logger().debug(f'发布舵机位置: x={joint_msg.x}, y={joint_msg.y}, z={joint_msg.z}')


# 主函数
def main(args=None):
    rclpy.init(args=args)
    maxarm_read_node = MaxArmReadNode()
    try:
        rclpy.spin(maxarm_read_node)
    except KeyboardInterrupt:
        maxarm_read_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()