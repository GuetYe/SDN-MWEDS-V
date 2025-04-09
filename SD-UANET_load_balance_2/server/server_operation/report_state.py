'''
Author: 孙石泉 786721684@qq.com
Date: 2024-01-21 10:49:22
LastEditTime: 2024-04-04 16:37:39
LastEditors: 孙石泉
Description: 服务器上报状态到控制器
FilePath: \SD-UANET_load_balance\server\server_operation\report_state.py
'''


# Linux 请使用sudo pip3 install scapy或sudo pipx install scapy 安装scapy
# sudo apt-get install sysstat   安装查看IO负载的包
from scapy.layers.inet import IP, TCP
from scapy.sendrecv import send


# from scapy.all import show_interfaces  # Tinkerboard下不能用，自己找


class PacketSelfState:
    def __init__(self, host_ip) -> None:
        """
        # description: xxx
        # param {*} self-传入类自身属性
        # param {*} IO_load-磁盘IO负载
        # param {*} Cpu_Uti-CPU使用率
        # param {*} Mem_uti-内存使用率
        # param {*} Remain_Capacity-磁盘剩余容量
        # return {*}
        """
        self.src_ip = host_ip
        self.dst_ip = '10.0.0.254'  # 除了网络中已知的IP以外都行，目的是触发packin-in

    # def show_device_interfaces(self):
    #     """
    #     description: 显示该设备中的所有网卡信息
    #     param {*} self-传入类自身属性
    #     return {*} 列出的所有网卡
    #     """
    #     return show_interfaces()

    def report_state(self, IO_load, Cpu_Uti, Mem_uti, Remain_Capacity):
        """
        # description: 上报自身数据(广播形式，触发控制器packet_in)
        # param {*} self-传入类自身属性
        # return {*} None
        """
        # 1.构造IP数据包
        # 加入目的ip地址，进行单播传输
        ip_packet = IP(dst = self.dst_ip)
        ip_packet.src = self.src_ip
        ip_packet.dst = self.dst_ip

        # 2.构造TCP负载数据
        data = '[HostStats(IO_load=%f,Cpu_Uti=%f,Mem_uti=%f,Remain_Capacity=%f)]' % (
        IO_load, Cpu_Uti, Mem_uti, Remain_Capacity)

        # 3.将TCP负载数据添加到IP数据包中
        tcp_packet = TCP()
        ip_packet.payload = tcp_packet / data
        send(ip_packet)  # 广播数据。可以使用"iface"形参指定网卡发送。show_device_interfaces()函数可以显示所有网卡
        print("The data reported by the samba server is：\n IO_load:{} \n cpu_utilization：{} \n memory_utilization:{} \n Disk_remaining_capacity:{}"
              .format(IO_load, Cpu_Uti, Mem_uti, Remain_Capacity))


if __name__ == '__main__':
    example = PacketSelfState(host_ip='169.254.64.1')
    example.report_state(0.1, 0.2, 0.3, 0.4)