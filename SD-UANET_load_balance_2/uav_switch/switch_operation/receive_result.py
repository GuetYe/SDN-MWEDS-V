'''
Author: Sun Shiquan email:786721684@qq.com
Date: 2025-01-01 09:32:51
LastEditTime: 2025-05-07 19:19:48
LastEditors: Sun Shiquan
Description: 

'''


import sys
import platform
import re
import sys
import ast


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
        self.receive_dict = {}

    def parsing_packet(self, packet):
        eth_src_mac = packet.src
        logger.info("<receive_result> -->  eth_src_mac:%s" % eth_src_mac)
        # 来自控制器的包
        if eth_src_mac == setting.CONTROLLER_MAC:
            arp_src_ip = packet.payload.psrc
            logger.info("<receive_result> -->  arp_src_ip:%s" % arp_src_ip)
        else:
            return
        if arp_src_ip in setting.CONTROLLER_IP:  # 必须筛选包的源IP为控制器
            arp_packet_load = str(packet.payload.load)
            # 使用re模块搜索结果
            result = re.findall(pattern='\{.+\}', string=arp_packet_load, )
            if result:
                logger.info("<receive_result> -->  result:%s" % result)
                # 提取字符串
                raw_str = result[0]

                # 如果有 array(...) 内容，要先转换成列表
                array_vals = re.findall(r'array\((\[.*?\])\)', raw_str)
                if array_vals:
                    raw_str = re.sub(r'array\(\[.*?\]\)', array_vals[0], raw_str)

                try:
                    self.receive_dict = ast.literal_eval(raw_str)
                    logger.info("<receive_result.py> The position data:%s" % self.receive_dict)
                except Exception as e:
                    logger.error(f"Failed to parse target position data: {e}")
                    self.receive_dict = None

            else:
                logger.info("<receive_result.py> The position returned by the controller cannot be found")
                self.receive_dict = None

    def catch_pack(self):
        self.receive_dict = {}  # 清空属性
        # count等0表示一直监听，要想监听数据包，需要首先安装winpcap或npcap  iface=setting.SNIFF_IFACE,
        # 一定要指定接口iface才可以接受包

        sniff(filter='arp', prn=self.parsing_packet, count=0, timeout=setting.SNIFF_TIMEOUT, iface="br0")


if __name__ == '__main__':
    a = ReceivePacket()
    a.catch_pack()
    logger.info(a.receive_dict)






