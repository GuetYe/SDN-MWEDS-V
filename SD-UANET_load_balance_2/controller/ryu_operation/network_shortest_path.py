'''
Author: 孙石泉 786721684@qq.com
Date: 2023-11-22 09:58:22
LastEditTime: 2025-02-27 21:51:37
LastEditors: Sun Shiquan
Description: 
FilePath: \SD-UANET_load_balance_2\controller\ryu_operation\network_shortest_path.py
'''


import time
import networkx as nx
from networkx.algorithms.approximation import steiner_tree

from ryu.base import app_manager
from ryu.base.app_manager import lookup_service_brick
from ryu.ofproto import ofproto_v1_3
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls, MAIN_DISPATCHER
from ryu.lib.packet import ipv4, ethernet, ether_types, packet

from config import setting

from log_module import logger



class ShortestPathForwarding(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    def __init__(self, *args, **kwargs):
        super(ShortestPathForwarding, self).__init__(*args, **kwargs)
        self.name = 'shortest_path'
        self.structure = lookup_service_brick('structure')
        self.monitor = lookup_service_brick('monitor')
        self.delay = lookup_service_brick('delay')
        self.arp = lookup_service_brick('arp')

        self.shortest_path_table = {}  # {(src.dpid, dst.dpid): [path]} src-dst的最短路径列表
        
        # 存储格式:(触发packet_in的源目地址)：time.time()
        self.packet_cache = {}

        self.table_select = "normal"


    

    def add_flow(self, datapath, priority, match, actions, hard_timeout=0):
        '''
        description: 下发流表
        param {*} self
        param {*} datapath
        param {*} priority
        param {*} match
        param {*} actions
        param {*} idle_timeout
        param {*} hard_timeout
        return {*}
        '''
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # 普通的流表
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        # 空闲超时（idle_timeout）和硬超时（hard_timeout）
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst,
                                idle_timeout = 0, hard_timeout=hard_timeout)
        
        datapath.send_msg(mod)



    def send_flow_mod_first(self, datapath, eth_type, eth_src, src_ip, dst_ip, src_port, dst_port, second_node_num):
        '''
        description: 下发流表(路径的第1台交换机)
        param {*} self
        param {*} datapath 交换机datapath实例
        param {*} eth_type 数据链路层的协议类型
        param {*} src_ip 源点IP
        param {*} dst_ip 目的点IP
        param {*} src_port 源点交换机的端口
        param {*} dst_port 目的点交换机端口
        return {*}
        '''

        parser = datapath.ofproto_parser

        match = parser.OFPMatch(in_port=src_port, eth_type=ether_types.ETH_TYPE_IP,
                                ipv4_src=src_ip, ipv4_dst=dst_ip)

        # 修改数据包的目的MAC地址，广播方式发送数据，使每个mesh节点都可以接收并响应改数据包
        # eth_dst="ff:ff:ff:ff:ff:ff"        
        eth_dst = setting.switch_mult_mac[second_node_num]   
        #   parser.OFPActionPushMpls(ethertype=eth_type), \parser.OFPActionSetField(mpls_label=setting.MPLS_LABEL),
        actions = [
                   parser.OFPActionSetField(eth_dst=eth_dst),
                   parser.OFPActionOutput(dst_port)]

        self.add_flow(datapath, 300, match, actions, hard_timeout=40)
        logger.info("send_flow_mod_first successsfully")


    def send_flow_mod_two_to_before_last(self, datapath, eth_type, eth_src, src_port, dst_port, node_num, next_node_num):
        '''
        description: 下发流表
        param {*} self
        param {*} datapath 交换机datapath实例
        param {*} eth_type 数据链路层的协议类型
        param {*} src_ip 源点IP
        param {*} dst_ip 目的点IP
        param {*} src_port 源点交换机的端口
        param {*} dst_port 目的点交换机端口
        return {*}
        '''

        parser = datapath.ofproto_parser
        #输出端口为数据包的输入端口
        ofproto = datapath.ofproto 
        dst_port = ofproto.OFPP_IN_PORT

        eth_dst_match = setting.switch_mult_mac[node_num]
        # , eth_dst=eth_dst_match  mpls_label=setting.MPLS_LABEL,
        
        match = parser.OFPMatch(in_port=src_port, eth_type=eth_type, 
                                eth_src=eth_src, eth_dst=eth_dst_match)

        eth_dst_action = setting.switch_mult_mac[next_node_num] 
        # eth_dst_action = "ff:ff:ff:ff:ff:ff"
        # parser.OFPActionSetField(eth_dst=eth_dst_action),\

        actions = [parser.OFPActionSetField(eth_dst=eth_dst_action),
                   parser.OFPActionOutput(dst_port)]
        
        self.add_flow(datapath, 300, match, actions, hard_timeout=40)


    def send_flow_mod_last(self, datapath, eth_type, eth_src, dst_ip, src_port, dst_port, node_num):
        '''
        description: 下发流表
        param {*} self
        param {*} datapath 交换机datapath实例
        param {*} eth_type 数据链路层的协议类型
        param {*} src_ip 源点IP
        param {*} dst_ip 目的点IP
        param {*} src_port 源点交换机的端口
        param {*} dst_port 目的点交换机端口
        return {*}
        '''

        parser = datapath.ofproto_parser
 
        eth_dst_match = setting.switch_mult_mac[node_num]
        # , eth_dst=eth_dst_match   mpls_label=setting.MPLS_LABEL,
        match = parser.OFPMatch(in_port=src_port, eth_type=eth_type, 
                                eth_src=eth_src, eth_dst=eth_dst_match)
        
        # 获取目的主机的mac地址
        eth_dst = "ff:ff:ff:ff:ff:ff"
        for key in self.structure.access_table.keys():  # {(dpid, in_port): (src_ip, src_mac)}
            # 原本if self.access_table[key][0] == host_ip:
            for access_ip, access_mac in self.structure.access_table[key]:
                if access_ip == dst_ip:
                    eth_dst = access_mac
        # parser.OFPActionPopMpls(ethertype=ether_types.ETH_TYPE_IP), \
        actions = [
                   parser.OFPActionSetField(eth_dst=eth_dst), \
                   parser.OFPActionOutput(dst_port)]

        
        self.add_flow(datapath, 300, match, actions, hard_timeout=40)
        logger.info("send_flow_mod_last successsfully")


    def send_packet_out_mult(self, datapath, out_port):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # 构造一个以太网帧，目的MAC地址为广播地址
        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(dst='ff:ff:ff:ff:ff:ff'))

        # 创建一个输出动作，发送到指定端口（这里假设端口号为1）
        actions = [parser.OFPActionOutput(out_port)]

        # 将数据包和动作打包成流表项
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=ofproto.OFP_NO_BUFFER,
            in_port=ofproto.OFPP_CONTROLLER,
            actions=actions,
            data=pkt.data
        )

        # 发送流表项到交换机
        datapath.send_msg(out)





    def send_flow_mod_mpls_drop(self, datapath, eth_type, src_port):
        '''
        description: 下发流表
        param {*} self
        param {*} datapath 交换机datapath实例
        param {*} eth_type 数据链路层的协议类型
        param {*} src_ip 源点IP
        param {*} dst_ip 目的点IP
        param {*} src_port 源点交换机的端口
        param {*} dst_port 目的点交换机端口
        return {*}
        '''

        parser = datapath.ofproto_parser
        # 把MPLS类型的数据包都丢弃
        match = parser.OFPMatch(in_port=src_port, eth_type=eth_type)
        actions = []
        # 优先级需比正常的处理MPLS类型数据流表低
        self.add_flow(datapath, 200, match, actions, hard_timeout=40)





    def send_flow_mod(self, datapath, eth_type, src_ip, dst_ip, src_port, dst_port):
        '''
        description: 下发流表
        param {*} self
        param {*} datapath 交换机datapath实例
        param {*} eth_type 数据链路层的协议类型
        param {*} src_ip 源点IP
        param {*} dst_ip 目的点IP
        param {*} src_port 源点交换机的端口
        param {*} dst_port 目的点交换机端口
        return {*}
        '''

        parser = datapath.ofproto_parser
        actions = [parser.OFPActionOutput(dst_port)]

        match_normal = parser.OFPMatch(in_port=src_port, eth_type=eth_type,
                                ipv4_src=src_ip, ipv4_dst=dst_ip)
        
        self.add_flow(datapath, 300, match_normal, actions, hard_timeout=40)
        
    


    def send_flow_mod_low(self, datapath, eth_type, src_ip, dst_ip, src_port, dst_port):
        '''
        description: 下发流表
        param {*} self
        param {*} datapath 交换机datapath实例
        param {*} eth_type 数据链路层的协议类型
        param {*} src_ip 源点IP
        param {*} dst_ip 目的点IP
        param {*} src_port 源点交换机的端口
        param {*} dst_port 目的点交换机端口
        return {*}
        '''
        ofproto = datapath.ofproto #获取OpenFlow协议信息
        parser = datapath.ofproto_parser

        # dst_port = ofproto.OFPP_FLOOD
        # dst_port = ofproto.OFPP_IN_PORT

        actions = [parser.OFPActionOutput(dst_port)]
        # actions = [parser.OFPActionOutput(src_port)]
        match_normal = parser.OFPMatch(in_port=src_port, eth_type=eth_type,
                                ipv4_src=src_ip, ipv4_dst=dst_ip)
        

        self.add_flow(datapath, 400, match_normal, actions, hard_timeout=40)


    def send_flow_mod_drop(self, datapath, eth_type, src_ip, dst_ip, src_port, dst_port):
        '''
        description: 下发流表
        param {*} self
        param {*} datapath 交换机datapath实例
        param {*} eth_type 数据链路层的协议类型
        param {*} src_ip 源点IP
        param {*} dst_ip 目的点IP
        param {*} src_port 源点交换机的端口
        param {*} dst_port 目的点交换机端口
        return {*}
        '''

        parser = datapath.ofproto_parser
        actions = []
        match = parser.OFPMatch(in_port=src_port, eth_type=eth_type,
                                ipv4_src=src_ip, ipv4_dst=dst_ip)

        self.add_flow(datapath, 1, match, actions, hard_timeout=60)




    def _build_packet_out(self, datapath, buffer_id, src_port, dst_port, data):
        '''
        description: 构造packet out包
        param {*} self
        param {*} datapath 要接收packet out包的交换机
        param {*} buffer_id 数据包的buffer_id序号
        param {*} src_port 流表的输入端口
        param {*} dst_port 流表的输出端口
        param {*} data 数据包
        return {*}
        '''
        actions = []
        # 添加动作，输出端口
        if dst_port:
            actions.append(datapath.ofproto_parser.OFPActionOutput(dst_port))

        msg_data = None
        # buffer_id == -1，控制器发送数据包给交换机(交换机不存储数据包，随packet-in消息发给控制器)
        if buffer_id == datapath.ofproto.OFP_NO_BUFFER:
            if data is None:
                return None
            msg_data = data

        # 生成packet-out消息题
        out = datapath.ofproto_parser.OFPPacketOut(datapath=datapath, buffer_id=buffer_id,
                                                   data=msg_data, in_port=src_port, actions=actions)
        return out

    # 构造组播输出的包
    @staticmethod
    def build_multicast_packet_out(datapath, buffer_id, src_port, dst_ports, data):
        """ 构造组播输出的包"""
        actions = []
        for port in dst_ports:
            actions.append(datapath.ofproto_parser.OFPActionOutput(port))

        msg_data = None
        if buffer_id == datapath.ofproto.OFP_NO_BUFFER:
            if data is None:
                return None
            msg_data = data

        out = datapath.ofproto_parser.OFPPacketOut(datapath=datapath, buffer_id=buffer_id,
                                                   data=msg_data, in_port=src_port, actions=actions)

        return out


    def send_packet_out(self, datapath, buffer_id, src_port, dst_port, data):
        '''
        description: 下发packout消息
        param {*} self
        param {*} datapath 交换机datapath实例
        param {*} buffer_id buffer_id标志
        param {*} src_port 源点交换机的端口
        param {*} dst_port 目的点交换机的端口
        param {*} data 把流的数据包给交换机
        return {*}
        '''
        out = self._build_packet_out(datapath, buffer_id, src_port, dst_port, data)
        if out:
            datapath.send_msg(out)

    def get_port_pair(self, src_dpid, dst_dpid):
        '''
        description: 获得2个节点的连接信息
        param {*} self
        param {*} src_dpid
        param {*} dst_dpid
        return {*}
        '''
        if (src_dpid, dst_dpid) in self.structure.link_table_backup.keys():
            return self.structure.link_table_backup[(src_dpid, dst_dpid)]
        else:
            logger.info("link_table_backup is:", self.structure.link_table_backup)
            logger.info("get_port_pair: dpid: %s -> dpid: %s is not in links"% (src_dpid, dst_dpid))
            return None


   
    def get_switches(self, dpid, in_port, src_ip, dst_ip):
        '''
        description:  根据源节点IP和目的节点IP获得2者的dpid
        param {*} self
        param {*} dpid 触发packet-in的交换机
        param {*} in_port 触发packet-in的交换机端口
        param {*} src_ip 源节点IP
        param {*} dst_ip 目的节点IP
        return {*} 源节点dpid，目的节点dpid(列表)
        '''
        dst_switch = list()
        logger.info("get_switches:get src-{} and dst-{} switch".format(src_ip, dst_ip))
        
        # 1.获得src switch的dpid和端口
        src_location = self.structure.get_dpid_and_port_by_ip(src_ip) 
        if src_location != None and src_location[0] == dpid:
            src_switch, src_switch_port = src_location
        else:
            logger.info("get_switches:get src_location{} error".format(src_ip))
            return None,None

        # # 触发packet-in的交换机端口可能不是连接主机的端口
        if in_port not in self.structure.not_use_ports[dpid]: 
            logger.info("get_switches：not_use_ports[{}]：{}".format(dpid, 
                            self.structure.not_use_ports[dpid]))
            logger.info("get_switches：in_port-{} is not in not_use_ports[{}]".format(in_port, 
                            dpid))
            return None, None

        # 2.获得dst switch的dpid和端口，如果是设定的组播地址
        if dst_ip in setting.DST_MULTICAST_IP.keys():
            dst_group_ip = setting.DST_MULTICAST_IP[dst_ip]
            for other_ip in dst_group_ip:
                dst_location = self.structure.get_dpid_and_port_by_ip(other_ip)
                if dst_location:
                    dst_switch.append(dst_location[0]) 
                else:
                    logger.info(f"get multicast route dst switches error: {dst_ip}")
                    return None, None
            logger.info(f"get multicast route dst switches: {dst_switch}")
        # 单播的目的节点
        else:
            dst_location = self.structure.get_dpid_and_port_by_ip(dst_ip)
            if dst_location:
                dst_switch.append(dst_location[0])
            else:
                logger.info(f"get single route dst switches error: {dst_ip}")
                return None, None
        # 获取源节点和目的节点的交换机成功，打印相关信息查看是否有误
        logger.info("\n")
        logger.info("<src_ip:{},src_switch:{}".format(src_ip, src_switch))
        logger.info("<dst_ip:{},dst_switch:{}".format(dst_ip, dst_switch))
        logger.info("\n")
        return src_switch, dst_switch






    def get_shortest_paths(self, src_dpid, dst_dpid, weight=1):
        '''
        description: dijkstra算法计算src到dst的最短路径，weight
        param {*} self
        param {*} src_dpid 源节点dpid
        param {*} dst_dpid 目的节点dpid
        param {*} weight 权重因子
        return {*}
        '''

        self.shortest_path_table.setdefault((src_dpid, dst_dpid), None)
        shortest_path = nx.shortest_path(self.structure.network_topology,
                                        source=src_dpid,
                                        target=dst_dpid,
                                        weight=weight,
                                        method=setting.CALCULATE_SHORTEST_PATH_METHOD)
        self.shortest_path_table[(src_dpid, dst_dpid)] = shortest_path

        return shortest_path





    def install_flow(self, path, eth_type, eth_src, eth_dst, src_ip, dst_ip, in_port, buffer_id, data=None):
        '''
        description: 根据最短路径下发流表
        param {*} self
        param {*} path 最短路径
        param {*} eth_type 数据链路层协议类型
        param {*} src_ip 源主机IP
        param {*} dst_ip 目的主机IP
        param {*} in_port 触发packet-in的交换机端口
        param {*} buffer_id buffer_id号
        param {*} data 重新下发给交换机的数据包
        return {*}
        '''
        if path is None or len(path) == 0:
            logger.info("install_flow error: Path Error")
            return False
        else:
            first_dp = self.structure.sw_datapaths_table[path[0]]
            # 1.路径长度>2，第2个至倒数第2个交换机下发流表
            if len(path) > 2:
                for i in range(1, len(path) - 1):
                    # port_pair[0]:前1个交换机的端口  port_pair[1]:该交换机的端口
                    port_pair = self.get_port_pair(path[i - 1], path[i])
                    port_pair_next = self.get_port_pair(path[i], path[i + 1])
                    node_num = path[i]
                    next_node_num = path[i + 1]
                    if port_pair and port_pair_next:
                        src_port, dst_port = port_pair[1], port_pair_next[0] 
                        datapath = self.structure.sw_datapaths_table[path[i]]

                        if self.table_select == "normal":
                            # # 下发正向流表
                            self.send_flow_mod_low(datapath, eth_type, src_ip, dst_ip, src_port, dst_port)
                            # # 下发反向流表
                            self.send_flow_mod_low(datapath, eth_type, dst_ip, src_ip, dst_port, src_port)
                        else:
                        
                            self.send_flow_mod_two_to_before_last(datapath, eth_type, eth_src, src_port, dst_port, node_num, next_node_num)
                            # self.send_packet_out_mult(datapath, dst_port)
                    else:
                        logger.info(f"install_flow error: len(path) > 2 "
                              f"node0, node1, port_pair: {path[i - 1], path[i], port_pair}, "
                              f"node1, node2, next_port_pair: {path[i], path[i + 1], port_pair_next}")
                        return False
            # 2.路径长度>1,给最后1个和第1个节点下发流表项
            if len(path) > 1:
                logger.info("in_port: %s"% (in_port))
                port_pair = self.get_port_pair(path[-2], path[-1])
                logger.info("path:{}, port_pair:{}, in_port:{}".format(path, port_pair, in_port))

                if port_pair is None:
                    logger.info("install_flow error in len(path)>1: port not found")
                    return False
                # 最后1个交换机的输入端口和输出到主机的端口
                src_port = port_pair[1]
                dst_port = self.structure.get_port(dst_ip)

                if dst_port is None:
                    logger.info("install_flow error in len(path)>1: last port %s is not found" % (dst_port))
                    return False
                # 给最后1个交换机下发流表
                last_dp = self.structure.sw_datapaths_table[path[-1]]
                last_node_num = path[-1]

                if self.table_select == "normal":
                    self.send_flow_mod(last_dp, eth_type, src_ip, dst_ip, src_port, dst_port)
                
                    self.send_flow_mod(last_dp, eth_type, dst_ip, src_ip, dst_port, src_port)
                else:

                    last_last_num = path[len(path)-2]
                    self.send_flow_mod_last(last_dp, eth_type, eth_src, dst_ip, src_port, dst_port, last_node_num)
                    self.send_flow_mod_first(last_dp, eth_type, eth_dst, dst_ip, src_ip, dst_port, src_port, last_last_num)
                    # self.send_packet_out_mult(datapath, dst_port)

                # 给第1个交换机下发流表
                port_pair = self.get_port_pair(path[0], path[1])
                if port_pair is None:
                    logger.info("install_flow error in len(path)>1: port not found in first switch")
                    return False
                # 第1个交换机的输出端口
                out_port = port_pair[0]

                if self.table_select == "normal":
                    self.send_flow_mod(first_dp, eth_type, src_ip, dst_ip, in_port, out_port)
                    self.send_flow_mod(first_dp, eth_type, dst_ip, src_ip, out_port, in_port)
                else:

                    # self.send_flow_mod_low(first_dp, eth_type, src_ip, dst_ip, out_port, out_port)
                    second_node_num = path[1]
                    one_node_num = path[0]
                    self.send_flow_mod_first(first_dp, eth_type, eth_src, src_ip, dst_ip, in_port, out_port, second_node_num)
                    self.send_flow_mod_last(first_dp, eth_type, eth_dst, src_ip, out_port, in_port, one_node_num)
                
                    # self.send_packet_out(first_dp, buffer_id, in_port, out_port, data)
                    # self.send_packet_out_mult(datapath, out_port)
                    return True
            
            # 3.len(path) == 1，给第1个交换机下发流表项
            else:
                # 第1个交换机与目的主机的连接端口
                out_port = self.structure.get_port(dst_ip)
                if out_port is None:
                    logger.info("install_flow error: out_port is None in first switch")
                    return False

                if self.table_select == "normal":
                    self.send_flow_mod(first_dp, eth_type, src_ip, dst_ip, in_port, out_port)
                    self.send_flow_mod(first_dp, eth_type, dst_ip, src_ip, out_port, in_port)
            
                else:
                    # self.send_flow_mod_low(first_dp, eth_type, src_ip, dst_ip, out_port, out_port)

                    self.send_flow_mod_first(first_dp, eth_type, eth_src, src_ip, dst_ip, in_port, out_port, path)

                    self.send_packet_out(first_dp, buffer_id, in_port, out_port, data)
                    # self.send_packet_out_mult(datapath, out_port)
                    return True
    
    def ip_in_access_table(self, access_table, src_ip):  
        '''
        description: 判断IP是否在network_structure类的access_table中
        param {*} access_table network_structure类的access_table中
        param {*} src_ip src_ip
        return {*}
        '''
        for key, value_list in access_table.items():  
            for value in value_list:  
                if isinstance(value, tuple) and value[0] == src_ip:  
                    return True  
        return False  


    def claculate_path_and_install_flow_entry(self, msg, eth_type, eth_src, eth_dst, src_ip, dst_ip):
        '''
        description: 计算最短路径并下发流表
        param {*} self 
        param {*} msg 触发packet-in的消息
        param {*} eth_type 数据链路层协议类型
        param {*} src_ip 源节点IP
        param {*} dst_ip 目的节点IP
        return {*}
        '''
        datapath = msg.datapath
        in_port = msg.match['in_port']

        # 1. 找出源节点和目的节点的位置
        src_dst_switches = self.get_switches(datapath.id, in_port, src_ip, dst_ip)
        logger.info("src_ip:{} dst_ip:{}".format(src_ip, dst_ip))
        logger.info("the switch that triggers packet-in is：{}".format(datapath.id))
        # 如果源节点和目的节点存在，计算最优路径，下发流表
        if src_dst_switches[0] != None and len(src_dst_switches[1]) >= 1:
            src_switch, dst_switch = src_dst_switches
            logger.info("{} ping {}, src_dst_switches:{}".format(src_ip, dst_ip, src_dst_switches))
            # 1.单播情况
            if len(dst_switch) == 1:
                dst_switch = dst_switch[0]
                # 计算最优路径，综合考虑剩余带宽、时延、丢包率
                path = self.get_shortest_paths(src_switch, dst_switch, weight="synthetic_weight")
                logger.info("[path]%s--%s: %s"% (src_switch, dst_switch, path))
                # 下发流表
                install_flow_result = self.install_flow(path, eth_type, eth_src, eth_dst, src_ip, dst_ip, in_port, msg.buffer_id, msg.data)
                if install_flow_result == True:
                    logger.info("The installation of the path's flow entry was successful!")
                    return True
                else:
                    return False

            # 2.组播情况，dst_switch为列表
            elif len(dst_switch) > 1:
                logger.info("multicast path is not available at present")
                return False
        
        # # 其他非目标mesh节点收到数据包后丢弃
        # elif src_ip in setting.host_ip and dst_ip in setting.host_ip \
        #     and self.ip_in_access_table(self.structure.access_table, src_ip) \
        #     and self.ip_in_access_table(self.structure.access_table, dst_ip):

        #     # 丢弃该数据包(MPLS)
        #     # self.send_flow_mod_drop(datapath, eth_type, src_ip, dst_ip, in_port, in_port)
        #     self.send_flow_mod_mpls_drop(datapath, eth_type, in_port)
        #     logger.info("The installation of the mesh's transfer flow entry was successful!")
        #     return False

        else:
            logger.info("src_dst_switches is nonexistent")
            return False



    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        '''
        description: 根据ipv4包计算最短路径，下发流表
        param {*} self
        param {*} ev
        return {*}
        '''
        # 有交换机状态改变或第一次获取拓扑时，不允许获取端口统计信息
        if self.structure.sw_change_flag == True or self.structure.first_flag == True:
            return
        
        msg = ev.msg
        # # 触发packet-in的交换机的端口号
        datapath = msg.datapath
        in_port = msg.match['in_port']

        # 解析数据包
        pkt = packet.Packet(msg.data)
        ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
        
        eth_pkt = pkt.get_protocols(ethernet.ethernet)[0]  # 解析ethernet层(数据链路层，用于判断是否为LLDP报文)
        eth_type = eth_pkt.ethertype    
        

        # 判断是否是LLDP报文的数据包，如果是则不处理该数据
        if eth_type == ether_types.ETH_TYPE_LLDP:
            # logger.info("dpid:{} eth_pkt:{}".format(datapath.id, eth_pkt))
            return

        # logger.info("eth_type:", eth_type) 
        logger.info("in_port: %s"% (in_port))
        
        # 如果数据包为IP包
        if isinstance(ipv4_pkt, ipv4.ipv4) or eth_type == ether_types.ETH_TYPE_IP:

            src_ip = ipv4_pkt.src
            dst_ip = ipv4_pkt.dst

            # 更改目的MAC地址为广播地址,使所有其他mesh节点都可回应packet-out发出的包(只是packet-out一次，因为不是在流表项使用)
            eth = pkt.get_protocol(ethernet.ethernet)
            # eth.dst = "ff:ff:ff:ff:ff:ff"
            eth_src = eth.src
            eth_dst = eth.dst


            # logger.info("src_ip and dst_ip is:", src_ip, dst_ip)
            # logger.info("packet_cache is:", self.packet_cache)
            # 目的是交换机IP的包，多半是主机上传的状态包，此时不要下发流表，否则在流表有效期内会接收不到主机的状态更新
            if ipv4_pkt.dst in setting.CONTROLLER_IP:
                return
            # ip源/目地址为交换机的地址，不下发流表
            elif src_ip in setting.switch_ip or dst_ip in setting.switch_ip:
                return
            # 数据链路层协议,IP或MPLS
            eth_type = ether_types.ETH_TYPE_IP

            # logger.info("src_ip:{} dst_ip:{}".format(src_ip, dst_ip))

            # x秒内不允许(src_ip,src_ip)或(dst_ip, src_ip)的包触发packet-in下发流表
            if (src_ip, dst_ip) in self.packet_cache.keys():
                if time.time() - self.packet_cache[(src_ip, dst_ip)] <= setting.INTERVAL_INSTALL_FLOW: 
                    # logger.info("The interval for install flow entry is less than %d s, prohibit installing flow entry"% setting.INTERVAL_INSTALL_FLOW)
                    return False
            # elif (dst_ip, src_ip) in self.packet_cache.keys():
            #     if time.time() - self.packet_cache[(dst_ip, src_ip)] <= setting.INTERVAL_INSTALL_FLOW:
            #         logger.info("The interval for install flow entry is less than %d s, prohibit installing flow entry"% setting.INTERVAL_INSTALL_FLOW)
            #         return True
                
            logger.info("\n") 
            # 计算最短路径并下发流表
            install_flow_result = self.claculate_path_and_install_flow_entry(msg, eth_type, eth_src, eth_dst, src_ip, dst_ip)

            if install_flow_result == True:
                # 将源目地址流表的时间戳
                self.packet_cache[(src_ip, dst_ip)] = time.time()
