'''
Author: 孙石泉 786721684@qq.com
Date: 2024-01-21 14:47:07
LastEditTime: 2025-02-18 21:55:33
LastEditors: Sun Shiquan
Description: 1.控制器获取samba服务器的状态信息  2.获取终端上传文件的请求并根据多属性决策得到分割方案，把分割方案发给终端
FilePath: \SD-UANET_load_balance_2\controller\ryu_operation\host_get_msg.py

'''

import sys

sys.path.append('../')  # 添加工作目录，使得VSCode能够导入其他目录的python文件
from ryu.base import app_manager
from ryu.base.app_manager import lookup_service_brick
from ryu.controller.handler import set_ev_cls, MAIN_DISPATCHER
from ryu.controller import ofp_event
from ryu.lib.packet import packet, ipv4, ethernet, arp
from ryu.lib.packet import ether_types

import config.setting as setting
import re
import time
from log_module import logger

class Host_Get_MSG(app_manager.RyuApp):
    def __init__(self, *_args, **_kwargs):
        super(Host_Get_MSG, self).__init__(*_args, **_kwargs)
        self.name = 'host_get_msg'
        self.structure = lookup_service_brick("structure")  # 导入其他RYU APP
        self.MADM = lookup_service_brick("MADM")
        # 获取samba服务器的状态信息的正则表达式
        self.search_server_stats_method = re.compile(
            r'.+HostStats\(IO_load=(?P<IO_load>\d+.\d+?),Cpu_Uti=(?P<Cpu_Uti>\d+.\d+?),Mem_uti=(?P<Mem_uti>\d+.\d+?),Remain_Capacity=(?P<Remain_Capacity>\d+.\d+?)\)\]')
        
        # 获取ovs交换机的状态信息的正则表达式
        self.search_switch_stats_method = re.compile(
            r'.+SwitchStats\(Cpu_Uti=(?P<Cpu_Uti>\d+.\d+?),Mem_uti=(?P<Mem_uti>\d+.\d+?),host_num=(?P<host_num>\d+)\)\]')
        
        self.search_request_method = re.compile(
            r'.+ClientRequest\(file_name=(?P<file_name>\S+.\S+?),file_size=(?P<file_size>\d+?)\)\]')
        
        self.search_uav_method = re.compile(r'.+UAVPosition\(UAV_target_position=\[(?P<position>(?:-?\d+\.\d+)(?:,\s*-?\d+\.\d+)*)\]\]')
        
        # 记录所有主机的当前状态{host_ip:[IO_load, Cpu_Uti, Mem_uti, Remain_Capacity], ...} self.all_host_stats = {}  
        self.all_host_stats = {}  
        # 保存ovs交换机的状态信息
        self.all_switch_stats = {}

        self.uav_datapath = None
        self.uav_port = None
        self.uav_mac = None
        self.uav_ip = None


    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        original_data = ev.msg.data
        
        data_str = str(original_data)
        known_host_list = []

        # 解析IPv4层
        pkt = packet.Packet(data=original_data)
        ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
        if ipv4_pkt == None:  # 其他消息，不进行下一步操作
            return
        src_host_ip = ipv4_pkt.src  # 取出上报的主机IP
        dst_cont_ip = ipv4_pkt.dst  # 取出上报的目的IP

        
        for key in self.structure.access_table.keys():  # {(dpid, in_port): (src_ip, src_mac)}
            for host_ip, host_mac in self.structure.access_table[key]:
                known_host_list.append(host_ip)
                
        # if src_host_ip not in known_host_list:  # 非已知主机消息（可能是ovs交换机的IP）
        #     return




        # 1.检测是否是主机上报的状态数据
        if self.search_server_stats_method.search(data_str) != None:  
            # logger.info("获取服务器的状态信息")
            IO_load = round(float(self.search_server_stats_method.search(data_str).group('IO_load')), 2)
            Cpu_Uti = round(float(self.search_server_stats_method.search(data_str).group('Cpu_Uti')), 2)
            Mem_uti = round(float(self.search_server_stats_method.search(data_str).group('Mem_uti')), 2)
            Remain_Capacity = round(float(self.search_server_stats_method.search(data_str).group('Remain_Capacity')), 2)

            # 解析IPv4层
            pkt = packet.Packet(data=original_data)
            ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
            src_host_ip = ipv4_pkt.src  # 取出上报状态的主机IP

            # 存储主机的状态信息
            self.all_host_stats[src_host_ip] = [IO_load, Cpu_Uti, Mem_uti, Remain_Capacity]
            logger.info("the samba server {}'s status info：{}".format(src_host_ip, self.all_host_stats[src_host_ip]))

        # 2.检测是否是OVS交换机的状态信息
        elif self.search_switch_stats_method.search(data_str) != None:
            # logger.info("获取OVS交换机的状态信息")
        
            Cpu_Uti = round(float(self.search_switch_stats_method.search(data_str).group('Cpu_Uti')), 2)
            Mem_uti = round(float(self.search_switch_stats_method.search(data_str).group('Mem_uti')), 2)
            host_num = self.search_switch_stats_method.search(data_str).group('host_num')
            # 解析IPv4层
            pkt = packet.Packet(data=original_data)
            ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
            src_host_ip = ipv4_pkt.src  # 取出上报状态的主机IP

            # 存储OVS交换机的状态信息
            self.all_switch_stats[host_num] = [Cpu_Uti, Mem_uti]
            logger.info("the OVS switch {}'s statue info：{}".format(host_num, self.all_switch_stats[host_num]))


        # 3.检测是否是Client的存储文件请求
        elif self.search_request_method.search(data_str) != None: 
            if dst_cont_ip in setting.CONTROLLER_IP:
                
                logger.info("request to transfer files!")

                if self.MADM is None:
                    self.MADM = lookup_service_brick("MADM")
                    # 1.取出上报的文件信息
                file_name = self.search_request_method.search(data_str).group('file_name')
                file_size = self.search_request_method.search(data_str).group('file_size')

                # 2.解析IPv4层
                pkt = packet.Packet(data=original_data)
                ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
                src_host_ip = ipv4_pkt.src  # 取出上报状态的主机IP

                # 3.检查该主机连接的交换机和端口是否已知，未知则不处理
                datapath = None
                port = None
                host_mac = None

                # # 原本：找到主机的信息
                # for host_key, host_value in self.structure.access_table.items():
                #     if src_host_ip == host_value[0]:
                #         datapath = self.structure.sw_datapaths_table[host_key[0]]  # 取出连接主机的交换机的datapath
                #         port = host_key[1]
                #         host_mac = host_value[1]
                #         break
                # 找到主机的信息
                for host_key in self.structure.access_table.keys():
                    for each_host_ip, each_host_mac in self.structure.access_table[host_key]:
                        if src_host_ip == each_host_ip:
                            datapath = self.structure.sw_datapaths_table[host_key[0]]  # 取出连接主机的交换机的datapath
                            port = host_key[1]
                            host_mac = each_host_mac
                            break  
            
                if datapath == None:
                    logger.info("the datapath doest't exist")
                    return
                logger.info("receive a transfer request from the client!")

                # 运行多属性决策算法，计算分割文件结果
                split_result = self.MADM.calculate(host_ip=src_host_ip, file_name=file_name, file_size=file_size)
                if split_result:
                    # 转发到申请的交换机的主机上
                    ofproto = datapath.ofproto
                    parser = datapath.ofproto_parser

                    # 构造ARP回复包，附带结果数据，有控制器执行packet_out，返回到申请的主机上
                    pkt = packet.Packet()
                    pkt.add_protocol(ethernet.ethernet(ethertype=ether_types.ETH_TYPE_ARP,
                                                    dst=host_mac,
                                                    src=setting.CONTROLLER_MAC))  # 这里的mac随意写，只是用作构造ARP包
                    pkt.add_protocol(arp.arp(opcode=arp.ARP_REPLY,
                                            src_mac=setting.CONTROLLER_MAC,
                                            src_ip=setting.CONTROLLER_IP[0],
                                            dst_mac=host_mac,
                                            dst_ip=src_host_ip))

                    pkt.serialize()
                    my_data = '[SplitResult(split_result=%s)]' % split_result
                    data = pkt.data + bytearray(my_data.encode())
                    actions = [parser.OFPActionOutput(port)]
                    out = parser.OFPPacketOut(datapath=datapath,
                                            buffer_id=ofproto.OFP_NO_BUFFER,
                                            in_port=ofproto.OFPP_CONTROLLER,
                                            actions=actions,
                                            data=data)

                    time.sleep(3)  # 延迟一段时间，等待主机方启动完监听回复ARP包
                    datapath.send_msg(out)
                    logger.info("the split result is returned to the client %s" % src_host_ip)

        # 3.检测是否是无人机的实时位置数据
        elif self.search_uav_method.search(data_str) != None: 
            if dst_cont_ip in setting.CONTROLLER_IP:
                
                logger.info("UAV's terminal send current position (x,y)")


                # 1.取出上报的UAV坐标
                file_name = self.search_uav_method.search(data_str).group('position')

                # 2.解析IPv4层
                pkt = packet.Packet(data=original_data)
                ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
                self.uav_ip = ipv4_pkt.src  # 取出上报状态的主机IP

                # 3.找到无人机上SDN交换机的datapath，mac地址，端口等等


                # # 原本：找到主机的信息
                # for host_key, host_value in self.structure.access_table.items():
                #     if src_host_ip == host_value[0]:
                #         datapath = self.structure.sw_datapaths_table[host_key[0]]  # 取出连接主机的交换机的datapath
                #         port = host_key[1]
                #         host_mac = host_value[1]
                #         break
                
                self.uav_datapath = ev.msg.datapath
                self.uav_port = ev.msg.match['in_port']
                eth = pkt.get_protocol(ethernet.ethernet)
                self.uav_mac = eth.src
                if self.uav_datapath == None:
                    logger.info("the uav's datapath doest't exist")
                    return
                logger.info("receive the uav's position from the uav")


               


