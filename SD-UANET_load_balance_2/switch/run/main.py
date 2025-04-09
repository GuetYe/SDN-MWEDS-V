'''
Author: 孙石泉 786721684@qq.com
Date: 2024-01-21 10:51:38
LastEditTime: 2024-02-29 20:40:10
LastEditors: 孙石泉
Description: ovs交换机运行的py文件，获取自身状态(cpu利用率、内存利用率)，上报到控制器
注意：
1.openwrt系统安装python的包
下载getpip：curl -O https://bootstrap.pypa.io/get-pip.py
运行get-pip.py（根据情况，需要网络）：python get-pip.py

2.OVS交换机后台运行python脚本：python -u main.py > output.log 1 2 &   
                             python -u /root/SD-UANET_load_balance/switch/run/main.py 1 2 > /dev/null 2>&1 &  
                        (可以不加> output.log，交换机只有128M的Flash。将标准输出和标准错误输出都重定向到/dev/null，丢弃掉)

停止后台运行的python脚本线程：ps查询脚本的进程号   kill +进程号

FilePath: \SD-UANET_load_balance\switch\run\main.py
'''


import sys

sys.path.append('../')  # 添加工作目录，使得VSCode能够导入其他目录的python文件

from switch_operation.get_state import Host_Utils
from switch_operation.report_state import PacketSelfState
import time


if __name__ == "__main__":
    time.sleep(5)
    host_utils = Host_Utils()
    host_ip = host_utils.get_host_IP()  # 获取主机IP
    #根据交换机的编号自己改变
    host_num = 4
    report = PacketSelfState(host_ip=host_ip)  # 实例化上报
    print("my host ip is:", host_ip)
    while True:
        # IO_load = host_utils.get_host_IO_load()
        Cpu_Uti = host_utils.get_host_cpu_utilization()
        # print("my Cpu_Uti is:", Cpu_Uti)
        Mem_uti = host_utils.get_host_memory_utilization()
        # print("my Mem_uti is:", Mem_uti)
        # # 多属性决策中，数据可以是大于1的吗？ 用磁盘空闲率不太好
        # Remain_Capacity = host_utils.get_host_Disk_remaining_capacity()
        report.report_state(Cpu_Uti=Cpu_Uti, Mem_uti=Mem_uti, host_num=host_num)
        time.sleep(5)  # 5秒上传一次

