'''
Author: 孙石泉 786721684@qq.com
Date: 2023-11-22 20:25:24
LastEditTime: 2024-11-27 22:48:41
LastEditors: Sun Shiquan
Description: 
注意：
1.如果一直存在flood泛洪的问题，泛洪前判断目的地址是否是交换机的地址，是的话不进行泛洪
FilePath: \SD-UANET_load_balance_mac\controller\ryu_operation\arp_handle.py
'''



from ryu.base import app_manager
from ryu.base.app_manager import lookup_service_brick
from ryu.ofproto import ofproto_v1_3
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls, MAIN_DISPATCHER
from ryu.lib.packet import packet
from ryu.lib.packet import arp, ipv4, ethernet


from log_module import logger

# ethernet.ethernet协议
ETHERNET = ethernet.ethernet.__name__
ETHERNET_MULTICAST = "ff:ff:ff:ff:ff:ff"
ARP = arp.arp.__name__


class ArpHandler(app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        super(ArpHandler, self).__init__(*args, **kwargs)
        self.name = 'arp'
        self.structure = lookup_service_brick('structure')
        self.monitor = lookup_service_brick('monitor')
        
        self.arp_table = {}  #{arp_pkt.src_ip：src}
        self.sw_arp_record = {} # {(datapath.id, eth_src, arp_dst_ip)：in_port}
        self.switch_ip = ["10.0.0.101", "10.0.0.102", "10.0.0.103", "10.0.0.104", "10.0.0.105", "10.0.0.106", "10.0.0.107",
                           "10.0.0.40", "10.0.0.1", "10.0.0.59", "10.0.0.60", "10.0.0.61" \
                           "10.0.0.253", "10.0.0.254",\
                            "192.168.1.1", "192.168.1.2", "192.168.1.3", "192.168.1.4", \
                            "192.168.1.5", "192.168.1.6", "192.168.1.7", "192.168.1.30", "192.168.1.40"]



    def _build_packet_out(self, datapath, buffer_id, src_port, dst_port, data):
        '''
        description:  构造输出的包
        param {*} self
        param {*} datapath
        param {*} buffer_id
        param {*} src_port
        param {*} dst_port
        param {*} data
        return {*}
        '''
        actions = []
        if dst_port:
            actions.append(datapath.ofproto_parser.OFPActionOutput(dst_port))

        msg_data = None
        if buffer_id == datapath.ofproto.OFP_NO_BUFFER:
            if data is None:
                return None
            msg_data = data

        out = datapath.ofproto_parser.OFPPacketOut(datapath=datapath, buffer_id=buffer_id,
                                                   data=msg_data, in_port=src_port, actions=actions)

        return out



    def arp_handler(self, header_list, datapath, in_port):
        # 1:reply or drop(reply：arp包第1次到改端口，drop：arp包第二次到同sw同port情况);  0: flood或不是arp包
        header_list = header_list
        datapath = datapath
        in_port = in_port

        # 数据链路层协议
        eth_src = header_list['ethernet'].src
        eth_dst = header_list['ethernet'].dst
        # 如果是广播或者是arp协议
        if eth_dst == ETHERNET_MULTICAST and "arp" in header_list:
            # arp协议的目的主机IP
            arp_dst_ip = header_list["arp"].dst_ip
            if (datapath.id, eth_src, arp_dst_ip) in self.sw_arp_record.keys():  # break loop 找到arp包(哪个交换机触发，源max，目标ip)的记录 丢弃
                out = datapath.ofproto_parser.OFPPacketOut(
                    datapath=datapath,
                    buffer_id=datapath.ofproto.OFP_NO_BUFFER,
                    in_port=in_port,
                    actions=[], data=None
                )
                datapath.send_msg(out)
                logger.info("arp_handler: meet the same arp packet, drop it")
                return True

                # random_boolean = random.choice([True, False])
                # if random_boolean == True:
                #     datapath.send_msg(out)
                #     logger.info("arp_handler: meet the same arp packet, drop it")
                #     return True
            else:
                self.sw_arp_record[(datapath.id, eth_src, arp_dst_ip)] = in_port
                
        # 不管是不是广播 arp回复
        if "arp" in header_list:
            hwtype = header_list[ARP].hwtype
            proto = header_list[ARP].proto
            hlen = header_list[ARP].hlen
            plen = header_list[ARP].plen
            opcode = header_list[ARP].opcode

            arp_src_ip = header_list[ARP].src_ip
            arp_dst_ip = header_list[ARP].dst_ip

            actions = []
            # 如果是arp请求消息(不包括aro回复消息)
            if opcode == arp.ARP_REQUEST:
                # 目标主机ip的mac地址有存在某个sw中，控制器替代目标主机回复发起arp请求的主机
                if arp_dst_ip in self.arp_table:

                    actions.append(datapath.ofproto_parser.OFPActionOutput(in_port))
                    ARP_Reply = packet.Packet()
                    # 添加数据链路层协议
                    ARP_Reply.add_protocol(ethernet.ethernet(ethertype=header_list[ETHERNET].ethertype,
                                                             dst=eth_src,
                                                             src=self.arp_table[arp_dst_ip]))
                    # 添加arp协议
                    ARP_Reply.add_protocol(arp.arp(opcode=arp.ARP_REPLY,
                                                   src_mac=self.arp_table[arp_dst_ip],
                                                   src_ip=arp_dst_ip,
                                                   dst_mac=eth_src,
                                                   dst_ip=arp_src_ip))
                    # 数据包序列化
                    ARP_Reply.serialize()
                    # 如果连接目标终端的sw收到了arp请求包，回复原终端
                    out = datapath.ofproto_parser.OFPPacketOut(
                        datapath=datapath,
                        buffer_id=datapath.ofproto.OFP_NO_BUFFER,
                        in_port=datapath.ofproto.OFPP_CONTROLLER,
                        actions=actions,
                        data=ARP_Reply.data
                    )
                    datapath.send_msg(out)
                    return True

        # 不是arp的请求消息 目标主机IP不存在在self.arp_table中
        else:
            return False






    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        """
            处理PacketIn事件
            1. arp包 是否已经记录
        """
        msg = ev.msg
        datapath = msg.datapath  # 从连接中获取数据平面的datapath(交换机)数据结构
        ofproto = datapath.ofproto #获取OpenFlow协议信息
        parser = datapath.ofproto_parser #获取协议的解析

        in_port = msg.match['in_port']
        # 解析数据包
        pkt = packet.Packet(msg.data)

        arp_pkt = pkt.get_protocol(arp.arp)
        ipv4_pkt = pkt.get_protocol(ipv4.ipv4)

        eth = pkt.get_protocols(ethernet.ethernet)[0]
        eth_src = eth.src

        # p.protocol_name：协议的名字  pkt.protocols(p)：pkt中该协议的内容(已建立连接的主机，协议类型为bytes)
        header_list = dict((p.protocol_name, p) for p in pkt.protocols if type(p) != bytes)
        if isinstance(arp_pkt, arp.arp):

            logger.info("arp_src and arp_dst is:%s -- %s"% (arp_pkt.src_ip, arp_pkt.dst_ip))
            self.arp_table[arp_pkt.src_ip] = eth_src
            # 1:reply(控制器代理回复) or drop(与记录相同的arp包);  0: flood
            if self.arp_handler(header_list, datapath, in_port):
                return None
            # 1.发送arp请求协议给目的主机或把目的主机的arp回复发给源主机 2.flood
            else:
                arp_dst_ip = arp_pkt.dst_ip
                # 通过host_ip查询self.access_table的键: {(dpid, in_port): (src_ip, src_mac)}获得键(dpid, in_port)
                # 获取主机与交换机的连接信息
                location = self.structure.get_dpid_and_port_by_ip(arp_dst_ip)
                if location:  # 如果有这个主机的位置
                    dpid_dst, out_port = location
                    datapath = self.structure.sw_datapaths_table[dpid_dst]
                    # 发送数据包发主机(arp请求或arp回复消息)
                    out = self._build_packet_out(datapath, ofproto.OFP_NO_BUFFER, ofproto.OFPP_CONTROLLER,
                                                 out_port, msg.data)
                    datapath.send_msg(out)
                    return
                else:
                    
                    for dpid in self.structure.sw_ports_table:
                        for port in self.structure.sw_ports_table[dpid]:
                            # 如果access_table中不存在主机信息
                            if (dpid, port) not in self.structure.access_table.keys() \
                            and str(arp_dst_ip) not in self.switch_ip: 
                                datapath = self.structure.sw_datapaths_table[dpid]
                                # 控制器给所有交换机的所有端口下发泛洪的packet-out
                                out = self._build_packet_out(datapath, ofproto.OFP_NO_BUFFER,
                                                             ofproto.OFPP_CONTROLLER, port, msg.data)
                                datapath.send_msg(out)
                                logger.info("get dst_ip:{} switch error,_packet_in_handler: Flooding".format(arp_dst_ip))
                    return


    def show_arp_handler_msg(self):
        logger.info("arp处理，防止广播风暴")
