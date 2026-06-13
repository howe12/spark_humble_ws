'''
@file:    MaxArm.py
@company: Hiwonder
@author:  CuZn
@date:    2024-02-26
@description: 接收 MaxArm消息 的通讯类
'''

#!/usr/bin/env python3
# encoding: utf-8
# MaxArm python sdk

import enum
import time
import struct
import serial

'''
0xAA 0x55 | func | data_len | data | check
'''

# CRC校验
def checksum_crc8(data , check_in = 0):
    check = check_in
    for b in data:
        check = check + b
    check = ~check
    return check & 0x00FF



# 功能号枚举
class PACKET_FUNCTION(enum.IntEnum): 
    FUNC_SET_ANGLE = 0x01
    FUNC_SET_XYZ = 0x03
    FUNC_SET_PWMSERVO = 0x05
    FUNC_SET_SUCTIONNOZZLE = 0x07
    FUNC_READ_ANGLE = 0x11
    FUNC_READ_XYZ = 0x13


'''
树莓派与MaxArm的通信类
'''
class MaxArm_ctl:
  
    # 构造函数
    def __init__(self, device = "/dev/ttyUSB0", baudrate=115200):
        self.__uart = serial.Serial(
                                        port=device,
                                        baudrate=baudrate,
                                        bytesize=serial.EIGHTBITS,
                                        parity=serial.PARITY_NONE,
                                        stopbits=serial.STOPBITS_ONE,
                                    )
    
    
    def map_func(self, value, from_min, from_max, to_min, to_max):
        # 将value从输入范围映射到输出范围
        return int((value - from_min) * (to_max - to_min) / (from_max - from_min) + to_min)
    
    
    '''
    用户使用函数 
    '''
    def serial_send(self , data):
        self.__uart.write(data)

    
    def set_angles(self, angles, time):
        # 将角度值映射到0~1000的范围
        mapped_angles = [self.map_func(angle, 0, 180, 0, 1000) for angle in angles]

        # 将角度值拆分为小端格式的两个字节
        angles_bytes = []
        for angle in mapped_angles:
            angle_bytes = struct.pack('<H', angle)
            angles_bytes.extend(angle_bytes)

        # 将时间拆分为小端格式的两个字节
        time_bytes = struct.pack('<H', time)

        # 构建要发送的数据帧
        data = bytearray([0xAA, 0x55, PACKET_FUNCTION.FUNC_SET_ANGLE, 0x08])
        data.extend(angles_bytes)  # 添加角度数据
        data.extend(time_bytes)    # 添加时间
        checksum = checksum_crc8(data[2:]) # 计算校验位
        data.append(checksum)  # 添加校验位

        # 发送数据帧
        self.serial_send(data)
        
        
    def set_xyz(self , pos , time):        
        # 将位置数据和时间打包为字节串
        pos_bytes = struct.pack('<hhh', *pos)
        time_bytes = struct.pack('<H', time)

        # 构建要发送的数据帧
        msg = bytearray([0xAA, 0x55, PACKET_FUNCTION.FUNC_SET_XYZ, 0x08])
        msg.extend(pos_bytes)
        msg.extend(time_bytes)
        
        # 计算校验位
        checksum = checksum_crc8(msg[2:]) # 计算校验位
        
        msg.append(checksum)

        # 发送数据帧
        self.serial_send(msg)
#        print(msg)


    def set_pwmservo(self , angle , time):
        angle = min(angle, 180)
        pul = self.map_func(angle, 0, 180, 500, 2500)

        # 构建要发送的数据帧
        data = bytearray([0xAA, 0x55, PACKET_FUNCTION.FUNC_SET_PWMSERVO, 0x04, pul & 0xFF, (pul >> 8) & 0xFF, time & 0xFF, (time >> 8) & 0xFF])

        # 计算校验位
        checksum = checksum_crc8(data[2:])
        data.append(checksum)

        # 发送数据帧
        self.serial_send(data)
#       print(data)


    def set_SuctioNnozzle(self , func):
        if func not in [1,2,3]:
            return
        # 构建要发送的数据帧
        data = bytearray([0xAA, 0x55, PACKET_FUNCTION.FUNC_SET_SUCTIONNOZZLE, 0x01, func & 0xFF])

        crc = checksum_crc8(data[2:])
        data.append(crc)
        self.serial_send(data)
#        print(data)
        
        
    def read_angles(self):
        # 构建要发送的读取角度的命令帧
        command = bytearray([0xAA, 0x55, 0x11, 0x00 , 0xEE])
        # 发送读取角度的命令帧
        self.serial_send(command)
        
        time.sleep(0.1)
        
        # 从串口接收数据
        response = self.__uart.read(11)
        
#        print(response)
        
        # 调用解析函数处理接收到的数据
        rec = self.rec_handle(response , 0x11)
        
        if rec:
            angles = struct.unpack('<hhh', rec)
        else:
            return
        return angles
        
    
    def read_xyz(self):
        # 构建要发送的读取角度的命令帧
        command = bytearray([0xAA, 0x55, 0x13, 0x00 , 0xEC])
        # 发送读取角度的命令帧
        self.serial_send(command)
        
        time.sleep(0.1)
        
        # 从串口接收数据
        response = self.__uart.read(11)
        
#        print(response)
        
        # 调用解析函数处理接收到的数据
        rec = self.rec_handle(response , 0x13)
        
        if rec:
            # print(len(rec))
            xyz = struct.unpack('<hhh', rec)
        else:
            return
        return xyz


    def rec_handle(self , datas_in , func):
        step = 1
        len = 0
        rt_data = {0,0,0}
        count = 0
        
        btye_data = bytearray([])
        for data in datas_in:
            if step == 1:
                if data == 0xAA:
                    btye_data.clear()
                    step = 2
            elif step == 2:
                if data == 0x55:
                    step = 3
                else:
                    step = 1
            elif step == 3:
                if data == func:
                    btye_data.append(data)
                    step = 4
                else:
                    step = 1
            elif step == 4:
                if data == 6:
                    btye_data.append(data)
                    len = data
                    step = 5
                else:
                    step = 1
            elif step == 5:
                btye_data.append(data)
                len -= 1
                if len == 0:
                    step = 6
            elif step == 6:
                if checksum_crc8(btye_data) == data:
                    return btye_data[2:8]
                else:
                    return
                    
                    
                    
                



