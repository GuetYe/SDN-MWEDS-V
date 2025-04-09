'''
Author: Sun Shiquan email:786721684@qq.com
Date: 2024-12-29 10:24:09
LastEditTime: 2025-02-21 12:16:16
LastEditors: Sun Shiquan

'''

import sys
import platform

import serial
import time
sys.path.append('../')
from switch_operation.position_send import UAVPosition
from switch_operation.receive_result import ReceivePacket
from switch_operation.log_module import logger
from switch_operation import uwb
import config.setting as setting
from switch_operation import nm_drone


uav_platform = platform.system()  # 读取客户端平台类型




if __name__ == '__main__':

    
    # ！windows平台自行输入IP地址！，Linux平台自动识别
    host_ip = '10.0.0.121'
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
    board_serial = serial.Serial('/dev/ttyS0', 57600, timeout=1)

    # # jetson连接凌霄无人机，设置串口号(/dev/ttyUSB0 不变)，波特率；起飞(高度默认1m)
    # NM = nm_drone.NM_drone("/dev/ttyS2", 500000)
    # # 程控模式
    # NM.mode_select(3)
    # NM.unlock()
    # time.sleep(8)
    # NM.takeoff(100)

    while True:
        
        ans = uwb.get_coordinates(board_serial)
        uav_ans = [1.0, 2.0]  #初始化无人机位置
        if ans:
            uav_ans[0] = ans[0]
            uav_ans[1] = ans[1]
        #获取到了交换机的位置坐标
        if uav_ans != []:
            UAVPosition_instantiation = UAVPosition(host_ip)  # 构造请求实例
            UAVPosition_instantiation.send_position(uav_ans)  # 发送请求至控制器
            logger.info("board sended uav's position to controller")


            logger.info("Listening for target position of the uav, pleace wait %s s." % setting.SNIFF_TIMEOUT)
            receive = ReceivePacket()  # 实例化一个数据包接收类
            receive.catch_pack()  # 监听主机收到的数据包(仅监听arp数据包)

            if not receive.result:  # 检查是否接收到控制器的决策结果
                logger.info("Unable to get target position from the controller")
            else:
                logger.info("The target position was successfully obtained")
            # # 控制无人机飞行到目标位置
            # nm_drone.move_to_target(uav_ans, receive.result)


   