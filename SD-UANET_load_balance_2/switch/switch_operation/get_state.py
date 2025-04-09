'''
Author: 孙石泉 786721684@qq.com
Date: 2024-01-21 10:47:28
LastEditTime: 2024-04-06 19:56:01
LastEditors: 孙石泉
Description: 获取服务器的CPU使用率，磁盘容量，等等...
FilePath: \SD-UANET_load_balance\switch\switch_operation\get_state.py
'''

import sys

sys.path.append('../')  # 添加工作目录，使得VSCode能够导入其他目录的python文件
import re
import subprocess
import config.setting as setting


class Host_Utils(object):
    """
    获取服务器的磁盘IO、CPU使用率、内存使用率、磁盘剩余容量状态
    """

    def __init__(self):
        # # 正则表达式寻找关键字符
        # if setting.RASPBERRY:
        #     self.get_host_io_load_method = re.compile(r'sda\s+(\S+\s+)+(?P<Load>\S+)\s*$', re.S)
        # elif setting.TINKERBOARD:
        #     self.get_host_io_load_method = re.compile(r'sda(.)+sda(\s+\d+.\d+){14}\s+(?P<Load>\d+.\d+?)\n', re.S)
        
        self.get_host_ip_method = re.compile(r'br0\s.*?\bsrc\s+(?P<ip>\d+\.\d+\.\d+\.\d+)')
        self.get_host_cpu_free_util_method = re.compile(r'CPU:(\s+\S+)*?\s+nic\s+(?P<CpuFreeUtil>\d+)%\s+idle')
        self.get_host_total_memory_method = re.compile(r'MemTotal:\s+(?P<MemTotal>\d+)\s+kB')
        self.get_host_free_memory_method = re.compile(r'MemFree:\s+(?P<MemFree>\d+)\s+kB')
        # self.get_host_Disk_remain_capa_method = re.compile(r'\/dev\/sda.+\s(\d+\s+){3}(?P<RemainCapacity>\d+?)\%')

    def get_host_IP(self):
        """
        # description: 获取主机的IP
        # param {*} self-传入类本身属性
        # return {*} 主机IP
        """
        host_ip = "10.0.0.251" #任意一个不存在的ip
        original_data = subprocess.check_output("ip route show", shell=True).decode('utf-8')
        # print("ip_original_data is:", original_data)
        try:
            host_ip = self.get_host_ip_method.search(original_data).group("ip")
        except Exception as e:
            print("<get_state.py> get NAS's IP fail")
        return host_ip

    # def get_host_IO_load(self):
    #     """
    #     # description: 获取主机的磁盘IO负载情况，注意，默认读取磁盘号为sda的磁盘
    #     # param {*} self-传入类本身属性
    #     # return {*} 主机磁盘IO负载率(浮点型，保留2位小数)
    #     """
    #     # 调用subprocess模块，将命令放到shell终端中执行，返回结果即是终端的执行结果
    #     # -x：显示详细信息  -t：显示终端和CPU的信息
    #     # 获取的信息util：一秒中有百分之多少的时间用于I/O操作，即被IO消耗的CPU百分比
    #     original_data = subprocess.check_output("iostat -x 1 -t 1", shell=True).decode('utf-8')
    #     # 1991意思是从第1991个位置开始搜索，因为命令设置了读取三次信息，会有三次测量的消息返回
    #     # 必须测量1次以上，通过iostat才能计算出IO的实时负载情况 
    #     # print("IO匹配结果", self.get_host_io_load_method.search(original_data))
    #     IO_load = round(float(self.get_host_io_load_method.search(original_data).group('Load')), 2)

    #     return IO_load

    def get_host_cpu_utilization(self):
        """
        # description: 获取主机的cpu使用率
        # param {*} self-传入类本身属性
        # return {*} 主机cpu使用率(浮点型，保留2位小数)
        """
        Cpu_Util = 1
        # 获取的信息id：空闲CPU百分比
        original_data = subprocess.check_output("top -bn 1", shell=True).decode('utf-8')
        try:
            Cpu_Free_Util = self.get_host_cpu_free_util_method.search(original_data).group('CpuFreeUtil')  # 获得CPU空闲百分比
            # print("Cpu_Free_Util is:", Cpu_Free_Util)
            Cpu_Util = round(1.0 - (float(Cpu_Free_Util) * 0.01), 2)
        except Exception as e:
            print("<get_state.py> get NAS's cpu_util fail")
            
        return Cpu_Util

    def get_host_memory_utilization(self):
        """
        description: 获取主机的内存使用率
        param {*} self-传入类本身属性
        return {*} 主机内存使用率(浮点型，保留2位小数)
        """
        Mem_uti = 1
        original_data = subprocess.check_output("cat /proc/meminfo", shell=True).decode('utf-8')
        try:
            MemTota = self.get_host_total_memory_method.search(original_data).group('MemTotal')
            MemFree = self.get_host_free_memory_method.search(original_data).group('MemFree')
            Mem_uti = round((float(MemTota) - float(MemFree)) / float(MemTota), 2)  # 使用率 = (总大小 - 空闲) / 总大小
        except Exception as e:
            print("<get_state.py> get NAS's memory_util fail")

        return Mem_uti

    # def get_host_Disk_remaining_capacity(self):
    #     """
    #     description: 获取远程主机的剩余磁盘容量(共享的NAS盘)
    #     param {*} self-传入类本身属性
    #     return {*} 主机剩余磁盘容量的百分比(浮点型)
    #     """
    #     original_data = subprocess.check_output("df -lm", shell=True).decode('utf-8')
    #     Remain_Capacity = 1.0 - \
    #                     (float(self.get_host_Disk_remain_capa_method.search(original_data).group('RemainCapacity')) * 0.01)

    #     return Remain_Capacity


if __name__ == '__main__':
    host = Host_Utils()
    # print("IO---", host.get_host_IO_load())
    print("CPU---", host.get_host_cpu_utilization())
    print("MEM---", host.get_host_memory_utilization())
    # print("Disk---", host.get_host_Disk_remaining_capacity())

