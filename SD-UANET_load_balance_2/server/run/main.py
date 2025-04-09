'''
Author: 孙石泉 786721684@qq.com
Date: 2024-01-21 10:51:38
LastEditTime: 2024-04-05 09:43:00
LastEditors: 孙石泉
Description: samba服务器运行的py文件，获取自身状态，上报到控制器
FilePath: \SD-UANET_load_balance\server\run\main.py
'''


import sys

sys.path.append('../')  # 添加工作目录，使得VSCode能够导入其他目录的python文件

from server_operation.get_state import Host_Utils
from server_operation.report_state import PacketSelfState
import time


if __name__ == "__main__":
    time.sleep(30)
    host_utils = Host_Utils()
    host_ip = host_utils.get_host_IP()  # 获取主机IP
    report = PacketSelfState(host_ip=host_ip)  # 实例化上报
    print("my host ip is:", host_ip)
    while True:
        IO_load = host_utils.get_host_IO_load()
        Cpu_Uti = host_utils.get_host_cpu_utilization()
        Mem_uti = host_utils.get_host_memory_utilization()
        # 多属性决策中，数据可以是大于1的吗？ 用磁盘空闲率不太好
        Remain_Capacity = host_utils.get_host_Disk_remaining_capacity()
        report.report_state(IO_load=IO_load, Cpu_Uti=Cpu_Uti, Mem_uti=Mem_uti, Remain_Capacity=Remain_Capacity)
        time.sleep(20)  # 20秒上传一次

