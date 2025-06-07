'''
Author: Sun Shiquan email:786721684@qq.com
Date: 2024-12-29 10:24:09
LastEditTime: 2025-05-09 22:12:38
LastEditors: Sun Shiquan

'''

import sys
# import platform

import serial
from time import sleep
sys.path.append('../')
from switch_operation.position_send import UAVPosition
from switch_operation.receive_result import ReceivePacket
from switch_operation.log_module import logger
from switch_operation import uwb
import config.setting as setting
from switch_operation import nm_drone


# uav_platform = platform.system()  # 读取客户端平台类型


# def recv(serial):
#     # while True:

#     #     data = serial.read_all().decode()  # str
#     #     sleep(1) #接收UWB串口数据时延迟1s
#     #     if data == '':
#     #         continue
#     #     else:
#     #         break
#     #     sleep(0.02)
#     # return data
def recv(serial):
    while True:
        line = serial.readline()
        try:
            text = line.decode('utf-8').strip()
        except UnicodeDecodeError:
            print("接收数据编码错误，忽略该行")
            continue
        
        if text.startswith('mc'):
            print("收到以 mc 开头的数据:", text)
            sleep(1)
            return text
        else:
            print("非 mc 开头数据，忽略:", text)
            # 继续等待

if __name__ == '__main__':

    
    # ！windows平台自行输入IP地址！，Linux平台自动识别
    host_ip = '10.0.0.107'
    # if uav_platform == 'Windows':
    #     host_ip = UAVPosition.get_wlan_ip_windows()
    #     # host_ip = "10.0.0.213"
    # elif uav_platform == 'Linux':
    #     host_ip = UAVPosition.get_host_IP_linux()
    # else:
    #     logger.info("The client platform is another platform")
    logger.info("uav_switch_ip is:%s" % host_ip)

    # 获取UAV的坐标信息(UWB定位)
    # 打开串口
    board_serial = serial.Serial('/dev/ttyS1', 57600, timeout=1)

    # # jetson连接凌霄无人机，设置串口号(/dev/ttyUSB0 不变)，波特率；起飞(高度默认1m)
    NM = nm_drone.NM_drone("/dev/ttyS2", 115200)
    # 程控模式
    # NM.mode_select(3)
    # sleep(1)
    # NM.unlock()
    # sleep(3)
    # NM.takeoff(150)
    UAVPosition_instantiation = UAVPosition(host_ip)  # 构造请求实例
    # uav_current_position = None
    # uav_target_position = None
    while True:
        # ans = []
        # ans = recv(board_serial)
        # logger.info("ans:%s" % ans)
        uav_current_position = None
        uav_target_position = None
        
        datauwb = uwb.get_uwbdata(board_serial)  # 每次都重新获取一次原始UWB数据
        if not datauwb:
            continue
        # UAVPosition_instantiation.send_position(datauwb)

        
        # ans = uwb.get_coordinates(board_serial)
        # ans = [2.0, 1.0]
        # uav_ans = [1.0, 2.0]  #初始化无人机位置
        # if ans:
        #     uav_ans[0] = ans[0] # x
        #     uav_ans[1] = ans[1] # y
        # 获取到了交换机的位置坐标
        # if datauwb != []:
        #     for each_send_num in range(5):
        #         datauwb = uwb.get_uwbdata(board_serial)  # 每次都重新获取一次原始UWB数据
        #         if not datauwb:
        #             continue
        #         UAVPosition_instantiation.send_position(datauwb)
        #         logger.info("Board sent number %s UWB raw data to controller: %s" % (each_send_num, datauwb))
        if datauwb != []:
            UAVPosition_instantiation.send_position(datauwb)
            logger.info("Board sent UWB raw data to controller: %s" % (datauwb))



            logger.info("Listening for target position of the uav, pleace wait %s s." % setting.SNIFF_TIMEOUT)
            receive = ReceivePacket()  # 实例化一个数据包接收类
            receive.catch_pack()  # 监听主机收到的数据包(仅监听arp数据包)

            if not receive.receive_dict:
                uav_current_position = [4.01, 4.24]
                uav_target_position = [1.56, 4.4]

            # if receive.receive_dict and "target_position" in receive.receive_dict:
            if receive.receive_dict:
                uav_current_position = receive.receive_dict["current_position"]
                uav_target_position = receive.receive_dict["target_position"]

                logger.info("The current position was successfully obtained %s" % uav_current_position)
                logger.info("The target position was successfully obtained %s" % uav_target_position)
                # # 控制无人机飞行到目标位置
                NM.move_to_target(uav_current_position, uav_target_position)
                
            else:
                logger.info("Unable to get current_position and target position from the controller")

            


   