#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from maxarm_msg.msg import Status
from maxarm_msg.msg import Angles
from maxarm_msg.msg import Position

from maxarm.MaxArm_ctl import MaxArm_ctl
import time

class MaxArmWriteNode(Node):
    def __init__(self):
        super().__init__('maxarm_write_node')
        self.get_logger().info('MaxArm写入节点已启动')
        
        # 机械臂控制写入端口
        self.ma = MaxArm_ctl(device = "/dev/ttyUSB2", baudrate=9600)

        # 机械臂气泵控制
        self.pump_control_ = self.create_subscription(Status, 'maxarm_pump_control', self.pump_topic_callback, 10)
        
        # 机械臂关节舵机控制
        self.joint_servo_control_ = self.create_subscription(Position, 'maxarm_joint_control', self.joint_servo_topic_callback, 10)

        # 机械臂末端位置控制
        self.xyz_control_ = self.create_subscription(Position, 'maxarm_position_control', self.position_topic_callback, 10)

        # 机械臂末端舵机角度控制
        self.servo_control_ = self.create_subscription(Angles, 'maxarm_servo_control', self.servo_topic_callback, 10)


    # 气泵控制回调函数
    def pump_topic_callback(self, msg):
        if msg.data == True:
            self.ma.set_SuctioNnozzle(1) # 打开气泵
        elif msg.data == False:
            self.ma.set_SuctioNnozzle(2) # 打开电磁阀并关闭气泵
            time.sleep(0.2) # 等待0.2秒
            self.ma.set_SuctioNnozzle(3) # 关闭电磁阀

    # 关节舵机控制回调函数
    def joint_servo_topic_callback(self, pos):
        angles = [pos.x, pos.y, pos.z]
        self.ma.set_angles(angles , 1000)  # 发送角度到机械臂,运行时间为1000ms

    # 末端位置控制回调函数
    def position_topic_callback(self, pos):
        xyz = [pos.x, pos.y, pos.z] 
        self.ma.set_xyz(xyz , 1000)  # 发送坐标到机械臂,运行时间为1000ms

    # 末端舵机角度控制回调函数
    def servo_topic_callback(self, angle):
        self.ma.set_pwmservo(angle.angle, 1000) # 发送舵机角度到机械臂,运行时间为1000ms


# 主函数
def main(args=None):
    rclpy.init(args=args)
    maxarm_write_node = MaxArmWriteNode()
    try:
        rclpy.spin(maxarm_write_node)
    except KeyboardInterrupt:
        maxarm_write_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()