'''
Author: Sun Shiquan email:786721684@qq.com
Date: 2025-01-01 09:32:51
LastEditTime: 2025-02-20 21:22:18
LastEditors: Sun Shiquan
Description: 

'''




import sys
import platform
import re
import sys
sys.path.append('../')
from switch_operation.log_module import logger

my_client_platform = platform.system()  # 读取客户端平台类型
if my_client_platform == 'Windows':  # Windows平台下加载模块的方法
    sys.path.append('../')
    import config.setting as setting
    from scapy.all import sniff
elif my_client_platform == 'Linux':  # Linux平台下加载模块的方法
    sys.path.append('../uav_jetson/config')
    from scapy.sendrecv import sniff
    import config.setting as setting


class ReceivePacket:
    def __init__(self) -> None:
        self.result = ""

    def parsing_packet(self, packet):
        eth_src_mac = packet.src
        # 来自控制器的包
        if eth_src_mac == setting.CONTROLLER_MAC:
            arp_src_ip = packet.payload.psrc
            logger.info("<receive_result> -->  arp_src_ip:%s" % arp_src_ip)
        else:
            return
        if arp_src_ip in setting.CONTROLLER_IP:  # 必须筛选包的源IP为控制器
            arp_packet_load = str(packet.payload.load)
            # 使用re模块搜索结果
            self.result = re.findall(pattern='\[.+\]', string=arp_packet_load, )
            if self.result:
                logger.info("result[0] is:%s" % self.result[0])
            else:
                logger.info("<receive_result.py> The target position returned by the controller cannot be found")

    def catch_pack(self):
        self.result = ""  # 清空属性
        # count等0表示一直监听，要想监听数据包，需要首先安装winpcap或npcap  iface=setting.SNIFF_IFACE,
        # 一定要指定接口iface才可以接受包

        sniff(filter='arp', prn=self.parsing_packet, count=0, timeout= setting.SNIFF_TIMEOUT, iface="sdn_mesh_5g")


if __name__ == '__main__':
    a = ReceivePacket()
    a.catch_pack()
    logger.info(a.receive_dict)






