'''
Author: 孙石泉 786721684@qq.com
Date: 2023-11-21 14:23:49
LastEditTime: 2024-12-20 22:26:42
LastEditors: Sun Shiquan
Description: 
FilePath: \SD-UANET_load_balance_2\controller\ryu_operation\network_structure.py
'''

"""
ryu的组成：
ryu.base：重要的文件：app_manager.py  1.加载 Ryu 应用程序   2.为 Ryu 应用程序提供contexts   3.在 Ryu 应用程序之间路由消息
ryu.ofproto：(一类是协议的数据结构定义，另一类是协议解析(数据包处理函数文件)):
​   ofproto_v1_0.py:1.0版本的OpenFlow协议数据结构的定义
​	ofproto_v1_0_parser.py:1.0版本的协议编码和解码
ryu.controller：实现controller和交换机之间的互联和事件处理。​	
   controller:1.处理来自交换机的连接  2.生成事件并将其路由到适当的实体，如Ryu应用程序
​   ofp_handler:基本的 OpenFlow 处理，包括协商(握手，错误信息处理和keep alive 等)
​   dpset:管理交换机(计划由 ryu/topology取代),定义交换机端的一些消息，如端口状态信息等，用于描述和操作交换机。如添加端口，删除端口等操作
​   ofp_event:OpenFlow 事件定义
ryu.lib：网络基本协议的实现和使用，dpid, mac和ip等数据结构
   packet:Ryu 数据包库。TCP/IP 等常用协议的解码器/编码器实现
​   ovs:ovsdb 交互库。
​	of_config:OF-Config 实现。
​	netconf:ryu/lib/of_config使用的 NETCONF 定义。
​	xflow:sFlow 和 NetFlow 的实现。
   hub：实现协程（coroutines）和异步编程的工具
ryu.topology：交换机和链路的查询模块。包含了switches.py等文件，基本定义了一套交换机的数据结构。
    event.py：定义交换上的事件。
    dumper.py：定义获取网络拓扑的内容。
    api.py：向上提供了一套调用topology目录中定义函数的接口

ryu.controller.handler.HANDSHAKE_DISPATCHER：交换 HELLO 讯息
ryu.controller.handler.CONFIG_DISPATCHER： 接收SwitchFeatures讯息
ryu.controller.handler.MAIN_DISPATCHER 一般状态
ryu.controller.handler.DEAD_DISPATCHER 联机中断

"""

import sys
sys.path.append("../")

from ryu.base import app_manager      
from ryu.controller import ofp_event   
from ryu.controller.handler import set_ev_cls, MAIN_DISPATCHER, DEAD_DISPATCHER, CONFIG_DISPATCHER
from ryu.lib import hub
from ryu.lib.packet import packet, arp, ethernet, ether_types
from ryu.topology import event
from ryu.topology.api import get_switch, get_link, get_host
from ryu.base.app_manager import lookup_service_brick
from ryu.ofproto import ofproto_v1_3

import networkx as nx
from config import setting
from log_module import logger


class Networkstructure(app_manager.RyuApp):
    '''
    description: 获取网络拓扑类
    return {*}
    '''
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    # 利用topology库获取拓扑信息 event.EventSwitchEnter, event.EventSwitchLeave,
            #   event.EventPortAdd, event.EventPortDelete, event.EventPortModify,
    events = [event.EventLinkAdd, event.EventLinkDelete]
    
    def __init__(self, *args, **kwargs):
        super(Networkstructure, self).__init__(*args, **kwargs)
        self.name = 'structure'
        self.monitor = lookup_service_brick("monitor")  # 创建一个Networkmonitor的实例
        self.delay = lookup_service_brick("delay")  # 创建一个Networkdelay的实例
        
        self.topology_api_app = self # 传入获取交换机API的形参get_switch()
        # 网络拓扑图，无向图
        self.network_topology = nx.Graph()
        self.sw_dpid_list = []  # 交换机的dpid 
        self.sw_ports_table = {}  # {dpid: {port_no, ...}} 交换机的所有端口号
        self.sw_link_port_table = {}  # {dpid: {port, ...}}  交换机链路的端口

        self.link_table = {}  # {(src_dpid, dst_dpid): (src_port_no, dst_port_no)} 相邻交换机的端口连接信息
        self.link_table_backup = {}
        self.get_topology_num = 0

        
        self.not_use_ports = {}  # {dpid: {port, ...}}   交换机之间没有用来连接的port
        self.sw_datapaths_table = {}  # {dpid: datapath} 保存交换机的datapath实例
        self.access_table = {}  # {(dpid, in_port): (src_ip, src_mac)} 交换机与终端的连接信息

        self.delete_sw_info = {} # {dpid:"触发删除的次数"}
        self.delete_threshold = 100

        # 交换机状态改变标志位。True：正在变化，False：没有变化
        self.sw_change_flag = False
        # True：第一次建立拓扑  False：不是第1次建立拓扑
        self.first_flag = True


        # 调试network_structure.py时的线程
        if setting.DEBUG_STRUCTURE:
            self._structure_thread = hub.spawn(self.structure_thread)




    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        '''
        description: 安装table miss流表，保存datapath和dpid。控制器与交换机连接时，交换机会发送一个OFPT_FEATURES_REPLY消息
        param {*} self
        param {*} ev
        return {*}
        '''
        # 交换机状态改变中，不允许所有操作交换机的行为
        self.sw_change_flag = True

        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table miss flow entry
        match = parser.OFPMatch() 
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        # 控制器下发流表函数
        self.add_flow(datapath, 0, match, actions)
        # 保存交换机的datapath实例和dpid
        self.sw_datapaths_table.setdefault(datapath.id, datapath)
        self.sw_datapaths_table[datapath.id] = datapath

        if datapath.id not in self.sw_dpid_list:
            self.sw_dpid_list.append(datapath.id)
        logger.info("switch {} connected and install table miss entry".format(datapath.id))
        
        # 交换机状态正常，允许所有操作交换机的行为
        self.sw_change_flag = False

    def add_flow(self, datapath, priority, match, actions):
        '''
        description: 控制器给交换机下发流表
        param {*} self 表示类的对象
        param {*} datapath 交换机的datapath实例
        param {*} priority 流表的优先级
        param {*} match 流表的匹配条件
        param {*} actions 动作
        return {*}
        '''
        # 指令：APPLY_ACTIONS，立即把数据包执行行动，不变更行动集，仅执行指定的行动列表
        inst = [datapath.ofproto_parser.OFPInstructionActions(datapath.ofproto.OFPIT_APPLY_ACTIONS, actions)]
        # flow-mod消息，下发流表
        mod = datapath.ofproto_parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst)
        datapath.send_msg(mod)


    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        '''
        description: 交换机状态改变(连接或断开)，初始化端口配置和流速特征，保存或删除datapath
        param {*} self
        param {*} ev
        return {*}
        '''
        # 交换机状态改变中，不允许所有操作交换机的行为
        self.sw_change_flag = True
        datapath = ev.datapath 
        # 一般状态 
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.sw_datapaths_table:
                # 保存交换机的datapath实例
                self.sw_datapaths_table[datapath.id] = datapath
                logger.info("register datapath: %016x" % datapath.id)

                if self.monitor == None:
                    self.monitor = lookup_service_brick("monitor")  # 创建一个Networkmonitor的实例
                # 端口配置和特征初始化，后续获取端口的配置和流速特征
                self.monitor.dpid_port_fueatures_table.setdefault(datapath.id, {})
        # 联机中断
        elif ev.state == DEAD_DISPATCHER:
            pass
            # if datapath.id in self.sw_datapaths_table:
            #     del self.sw_datapaths_table[datapath.id]
                # logger.info("unreigster datapath: %016x" % datapath.id)
                # logger.info("unreigster datapath: %016x" % datapath.id)
        # 交换机状态正常，允许所有操作交换机的行为
        self.sw_change_flag = False


    def get_port(self, dst_ip):
        """ 根据目的ip获得出去的端口"""
        for key in self.access_table.keys():  # {(dpid, in_port): (src_ip, src_mac)}
            for access_ip, access_mac in self.access_table[key]:
                if access_ip == dst_ip:
                    dst_port = key[1]
                    return dst_port
        return None



    @set_ev_cls(events)
    def get_topology(self, ev, way=0):
        '''
        description: 获取并建立网络拓扑(被动方式)
        param {*} self
        param {*} ev
        param {*} way 主动还是被动方式
        return {*}
        '''
        self.sw_change_flag = True
        # 还没有交换机连接
        if not self.sw_dpid_list:
            logger.info("There are not have switch, please wait it")
            return
        
        # 获取所有swicth列表和link信息
        switch_list = get_switch(self.topology_api_app, None)
        link_list = get_link(self.topology_api_app, None)

    
        if switch_list == [] or link_list == {}:
            logger.info("switch_list or link_list is empty")
            return
        
        
        # 将swicth添加到self.sw_ports_table
        for each_switch in switch_list:

            # logger.info("each_switch: %s", each_switch)

            dpid = each_switch.dp.id
            # 初始化相关端口信息
            self.sw_ports_table.setdefault(dpid, set())
            self.sw_link_port_table.setdefault(dpid, set())
            self.not_use_ports.setdefault(dpid, set())
            if dpid not in self.sw_dpid_list:
                self.sw_dpid_list.append(dpid)
            # 添加该交换机的所有端口号
            for each_port in each_switch.ports:
                self.sw_ports_table[dpid].add(each_port.port_no)

        # # 每个一定次数清空link_table，实现动态拓扑的功能
        # if self.get_topology_num >= setting.link_table_reset_interval:
        #     logger.info("link_table reset")
        #     self.link_table = {}
        #     self.get_topology_num = 0
                


        # 将link添加到self.link_table
        for link in link_list:
            # logger.info("link: %s", link)

            src_sw = link.src  
            dst_sw = link.dst
            if (src_sw.dpid, dst_sw.dpid) in setting.link_list:
                # 保存链接信息
                self.link_table[(src_sw.dpid, dst_sw.dpid)] = (src_sw.port_no, dst_sw.port_no)
                # 保存交换机的链路端口
                if src_sw.dpid in self.sw_dpid_list:
                    self.sw_link_port_table[src_sw.dpid].add(src_sw.port_no)
                if dst_sw.dpid in self.sw_dpid_list:
                    self.sw_link_port_table[dst_sw.dpid].add(dst_sw.port_no)
        
        # link_table的备份，防止shortest_path.py中get_port_pair函数在找路径时报错。查询链路信息时都用link_table_backup
        if len(self.link_table) != 0:
            logger.info("the link_table to assignment is:%s", self.link_table)
            self.link_table_backup = self.link_table
        else:
            logger.info("link_table(zero) is:%s", self.link_table)
            logger.info("link_table_backup is:%s", self.link_table_backup)

        # 统计没使用的端口
        for each_sw_dpid in self.sw_ports_table.keys():
            all_ports_set = self.sw_ports_table[each_sw_dpid]
            linked_port_set = self.sw_link_port_table[each_sw_dpid]
            # 没有用到的端口 = 全部端口 - 链路之间的端口
            self.not_use_ports[each_sw_dpid] = all_ports_set - linked_port_set


        # 动态拓扑  加上这段代码，拓扑没那么稳定
        # bug：开机时后面连接交换机连接较慢，会把其信息删除掉，方法：增加滤波方法，多次触发删除条件才删除
            
        # if self.sw_ports_table != {} and self.link_table != {}:
        #     for each_dpid in list(self.sw_ports_table.keys()): # 用list迭代sw_ports_table.keys()，字典在迭代期间不可改变字典的键值
        #         self.delete_sw_info.setdefault(each_dpid, {})
        #         if not any(each_dpid in link for link in self.link_table.keys()):
        #             # 触发删除条件的次数自增1
        #             self.delete_sw_info[each_dpid].setdefault('delete_counter', 0)
        #             self.delete_sw_info[each_dpid]['delete_counter'] += 1
        #             logger.info("the number of agree to delete dpid:{}".format(self.delete_sw_info[each_dpid]['delete_counter']))
        #             # 触发删除条件的次数>设定的阈值
        #             if self.delete_sw_info[each_dpid]['delete_counter'] >= self.delete_threshold:
                
        #                 # 所有交换机及其端口
        #                 if each_dpid in self.sw_ports_table.keys():
        #                     del self.sw_ports_table[each_dpid] 
        #                 # 交换机及其已用的端口
        #                 if each_dpid in self.sw_link_port_table.keys():
        #                     del self.sw_link_port_table[each_dpid]
        #                 # 交换机的没有占用的端口
        #                 if each_dpid in self.not_use_ports.keys():                   
        #                     del self.not_use_ports[each_dpid]
        #                 #交换机的datapath实例 不要删除，没有改dpid的datapaths，monitor模块发送echo请求出会出错，
        #                 if each_dpid in self.sw_datapaths_table.keys(): 
        #                     del self.sw_datapaths_table[each_dpid]  
        #                 # 所有交换机的dpid列表
        #                 if each_dpid in self.sw_dpid_list:
        #                     self.sw_dpid_list.remove(each_dpid) 
                            
        #                 # 链路的时延
        #                 if each_dpid in self.delay.link_delay.keys():
        #                     del self.delay.link_delay[each_dpid]
        #                 # 链路的丢包率
        #                 if (each_dpid in link_loss for link_loss in self.monitor.link_loss.keys()):
        #                     for link_loss in list(self.monitor.link_loss.keys()):  # 用list迭代all_links_loss.keys()，字典在迭代期间不可改变字典的键值
        #                         if each_dpid in link_loss:
        #                             del self.monitor.link_loss[link_loss]
        #                 # 图的节点
        #                 if each_dpid in self.network_topology:
        #                     self.network_topology.remove_node(each_dpid)

        #                 if each_dpid in self.access_table.keys():
        #                     port_no = self.get_port(each_dpid)
        #                     del self.access_table[(each_dpid, port_no)]
        #                 logger.info("the number of agree to delete dpid:{}".format(self.delete_sw_info[each_dpid]['delete_counter']))
        #                 logger.info("topology was changed,remode {}'s information".format(each_dpid))

        #         # 触发删除条件的次数清零
        #         else:
        #             self.delete_sw_info[each_dpid].setdefault('delete_counter', 0)
        #             self.delete_sw_info[each_dpid]['delete_counter'] = 0



        # 建立拓扑 bw、delay和loss、synthetic默认为0
        self.build_topology_between_switches()
        if way == 0:
            logger.info("network topology build passively")
        else:
            logger.info("network topology build actively")

        setting.print_pretty_table(self.sw_ports_table , ['dpid', 'port_no'], [10, 10],
                    '<structure.py> --- sw_ports_table', )  # 交换机所有端口
        setting.print_pretty_table(self.link_table, ['dpid-dpid', 'port-port'], [10, 10],
                                   '<structure.py>--- link_table', )  # 交换机相互连接的端口
        setting.print_pretty_table(self.sw_link_port_table, ['dpid', 'port'], [10, 10],
                                   '<structure.py>--- sw_link_port_table', )  # 交换机相互连接的端口
        setting.print_pretty_table( self.delay.link_delay, ['sw---sw', 'delay'], [10, 10],
                            '<structure.py>--- link_delay', )  # 交换机之间的时延
        setting.print_pretty_table(self.access_table, ['dpid-port_no   ', '   ip-mac'], [10, 10],
                            '<structure.py>--- self.access_table', )  # 主机与交换机的连接信息
        setting.print_pretty_table(self.sw_datapaths_table, ['dpid', 'datapath'], [10, 10],
                                   
                                   '<structure.py> --- sw_datapaths_table', )  # 交换机所有datapaths
        
        logger.info("not_use_ports:{}".format(self.not_use_ports)) # 交换机没有使用的端口

        logger.info("sw_dpid_list:{}".format(self.sw_dpid_list))
        logger.info("The network topology is:{}".format(self.network_topology))
        self.first_flag = False
        self.sw_change_flag = False
        self.get_topology_num += 1

    def build_topology_between_switches(self, bw=0.0, delay=0.0, loss=0.0, synthetic=100.0):
        '''
        description: 根据网络链路属性建立拓扑
        param {*} self
        param {*} bw
        param {*} delay
        param {*} loss
        return {*}
        '''
        # 第一次可能没有创建monitor和delay实例，则创建实例，不然会报错
        if self.monitor ==  None or self.delay == None:
            self.monitor = lookup_service_brick("monitor")  
            self.delay = lookup_service_brick("delay")  
            return 
        max_bandwidth = 30000000
        max_delay = 1
        max_loss = 50

        min_bandwidth = 0
        min_delay = 0
        min_loss = 0


        if self.network_topology:
            # 获取链路最大及最小的带宽、时延和丢包率
            max_bandwidth = max([edge_attr.get('bw', 30000000) for u, v, edge_attr in self.network_topology.edges(data=True)])
            if max_bandwidth == 0.0:
                max_bandwidth = 30000000
            # logger.info("max_bandwidth is:%s", max_bandwidth)
            max_delay = max([edge_attr.get('delay', 1) for u, v, edge_attr in self.network_topology.edges(data=True)])
            if max_delay == 0.01:
                max_delay = 0.02
            # logger.info("max_delay is:%s", max_delay)
            max_loss = max([edge_attr.get('loss', 50) for u, v, edge_attr in self.network_topology.edges(data=True)])
            if max_loss == 0.0:
                max_delay = 5
            # logger.info("max_loss is:%s", max_loss)

            min_bandwidth = min([edge_attr.get('bw', 0) for u, v, edge_attr in self.network_topology.edges(data=True)])
            # logger.info("min_bandwidth is:%s", min_bandwidth)
            min_delay = min([edge_attr.get('delay', 0) for u, v, edge_attr in self.network_topology.edges(data=True)])
            # logger.info("min_delay is:%s", min_delay)
            min_loss = min([edge_attr.get('loss', 0) for u, v, edge_attr in self.network_topology.edges(data=True)])
            # logger.info("min_loss is:%s", min_loss)

        # 获取每条边的属性并添加到图中
        for link in self.link_table:
            src_dpid, dst_dpid = link
            src_port, dst_port = self.link_table[link]
            # 1.剩余带宽
            if src_dpid in self.monitor.port_remained_bw.keys() and dst_dpid in self.monitor.port_remained_bw.keys():
                src_port_bw = self.monitor.port_remained_bw[src_dpid][src_port]
                dst_port_bw = self.monitor.port_remained_bw[dst_dpid][dst_port]
                if src_port_bw != None and dst_port_bw != None:
                    # 取双向链路中的最小剩余带宽
                    bw = min(src_port_bw, dst_port_bw) 

            # 2.丢包率
            if link in self.monitor.link_loss.keys() and link[::-1] in self.monitor.link_loss.keys():
                src_to_dst_loss = self.monitor.link_loss[link]
                dst_to_src_loss = self.monitor.link_loss[link[::-1]]
                if src_to_dst_loss !=None and dst_to_src_loss!= None:
                    # 取双向链路的最大丢包率
                    loss  = max(src_to_dst_loss, dst_to_src_loss)  


            # 3.时延
            if src_dpid in self.delay.link_delay.keys() and dst_dpid in self.delay.link_delay.keys():
                if self.delay.link_delay[src_dpid].get(dst_dpid) != None:
                    # 时延在链路中正向和反向的都相同，取正向的就行
                    delay = self.delay.link_delay[src_dpid][dst_dpid]
            
            # 归一化处理
            bandwidth_norm = (bw - min_bandwidth) / (max_bandwidth - min_bandwidth +1e-10)
            delay_norm = (delay- min_delay) / (max_delay - min_delay +1e-10)
            loss_norm = (loss - min_loss) / (max_loss - min_loss +1e-10)
            # 加权综合的weight(综合剩余带宽、时延、丢包),越小越好（每项分值范围为0~100）
            synthetic = - setting.synthetic_bandwidth_weight * bandwidth_norm * 100 \
                         + setting.synthetic_delay_weight * delay_norm * 100 \
                         + setting.synthetic_loss_weight * loss_norm * 100 \
                         + 100
            if synthetic < 0:
                synthetic = 0.0

            
            # 把属性添加到图的链路中
            self.network_topology.add_node(src_dpid, pos=setting.node_position[src_dpid])
            self.network_topology.add_node(dst_dpid, pos=setting.node_position[dst_dpid])
            self.network_topology.add_edge(src_dpid, dst_dpid, bw=bw, delay=delay, loss=loss, synthetic_weight = synthetic)
        

        

    # 将packet-in解析的arp的网络通路信息存储
    def storage_access_info(self, sw_id, in_port, src_ip, src_mac):
        '''
        description: 存储交换机的所连主机信息
        param {*} self
        param {*} sw_id 链路中的交换机id序号
        param {*} in_port 交换机与主机连接的端口号
        param {*} src_ip 主机ip地址
        param {*} src_mac 主机mac地址
        return {*}
        '''
        # 只保存在链路中的交换机的主机信息
        if sw_id in self.sw_dpid_list:
            # 如果端口不是交换机链路的端口
            if in_port in self.not_use_ports[sw_id] and in_port not in self.sw_link_port_table[sw_id]:
                if src_ip not in setting.CONTROLLER_IP:  # 不存储控制器IP (arp_src_ip, arp_src_mac)
                    if (sw_id, in_port) in self.access_table.keys():
                        if (src_ip, src_mac) in self.access_table[(sw_id, in_port)]:
                            return
                        else:
                            self.access_table[(sw_id, in_port)].append((src_ip, src_mac))
                            return
                    # 新的终端
                    else:
                        # 新的终端，创建一个终端信息列表
                        self.access_table[(sw_id, in_port)] = [(src_ip, src_mac)]
                        return
            # 交换机链路的接口也可能被存储为主机，删除掉            
            for each_port in list(self.sw_link_port_table[sw_id]):
                if each_port in self.access_table.keys():
                    if (sw_id, each_port) in self.access_table.keys():
                        del self.access_table[(sw_id, each_port)]

    def get_dpid_and_port_by_ip(self, host_ip):
        '''
        description: 通过主机ip获取其连接的交换机dpid和端口
        param {*} self
        param {*} host_ip
        return {*}
        '''
        if host_ip == "0.0.0.0" or host_ip == "255.255.255.255":
            return None

        for key in self.access_table.keys():  # {(dpid, in_port): (src_ip, src_mac)}
            # 原本if self.access_table[key][0] == host_ip:
            for access_ip, access_mac in self.access_table[key]:
                if access_ip == host_ip:
                    return key
        return None



    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        '''
        description: 处理arp包，获取主机与交换机的连接信息
        param {*} self
        param {*} ev
        return {*}
        '''
        # 有交换机状态改变或第一次获取拓扑时，不允许获取端口统计信息
        if self.sw_change_flag == True or self.first_flag == True:
            return
        
        msg = ev.msg
        datapath = msg.datapath
        in_port = msg.match['in_port']  # 取出数据包进入的交换机端口号
  
        # 解析数据包
        pkt = packet.Packet(msg.data)
        arp_pkt = pkt.get_protocol(arp.arp)  # 解析arp层(数据链路层，用户获取包的来源、MAC和IP)
        eth_pkt = pkt.get_protocols(ethernet.ethernet)[0]  # 解析ethernet层(数据链路层，用于判断是否为LLDP报文)
        # 数据链路层协议的类型
        eth_type = eth_pkt.ethertype     

        # 如果是lldp报文触发的packet-in
        if eth_type == ether_types.ETH_TYPE_LLDP:
            # logger.info("packet-in:LLDP Packet is detected, return") # 忽略LLDP报文
            return
        

        # 3.解析arp内容，并存储主机的通路信息到host_access_table表中
        # 这里注意，当数据包查到流表可以转发时，不会触发该arp解析
        arp_src_ip = None
        arp_src_mac = None    
        if isinstance(arp_pkt, arp.arp): 
            arp_src_ip = arp_pkt.src_ip  
            logger.info("arp_src_ip_src_ip:{}".format(arp_src_ip))
            arp_src_mac = arp_pkt.src_mac  

            # 1.判断交换机dpid和端口 原本：self.not_use_ports # 还未更新not_use_sw_ports，不解析
            if datapath.id not in self.sw_dpid_list:  
                return
            # 2.解决Windosw未设置IP时发arp包会出现src_ip=0.0.0.0的问题
            if arp_pkt.src_ip == "0.0.0.0":
                arp_src_ip = arp_pkt.dst_ip

            # 2.存储主机与交换机的连接信息
            self.storage_access_info(datapath.id, in_port, arp_src_ip, arp_src_mac)


    def structure_thread(self):
        '''
        description: network_structure.py单独调试时运行的线程
        param {*} self
        return {*}
        '''
        while True:
            # way=1:主动获取拓扑
            self.get_topology(ev=None, way=1)
            hub.sleep(5)
    







