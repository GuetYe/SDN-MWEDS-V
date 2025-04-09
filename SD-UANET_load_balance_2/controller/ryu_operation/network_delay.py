'''
Author: 孙石泉 786721684@qq.com
Date: 2023-11-22 09:57:52
LastEditTime: 2024-12-20 22:31:26
LastEditors: Sun Shiquan
Description: 
FilePath: \SD-UANET_load_balance_2\controller\ryu_operation\network_delay.py
'''
import time

from ryu.base import app_manager
from ryu.base.app_manager import lookup_service_brick
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls, MAIN_DISPATCHER
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
from ryu.lib.packet import packet, ethernet, ether_types
from ryu.topology.switches import Switches, LLDPPacket

from config import setting
from log_module import logger

class NetworkDelayDetector(app_manager.RyuApp):
    
    """ 测量链路的时延"""
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'switches': Switches}  # 实例化一个Switches类，后续用于LLDP测量时延

    def __init__(self, *args, **kwargs):
        super(NetworkDelayDetector, self).__init__(*args, **kwargs)
        self.name = 'delay'

        self.structure = lookup_service_brick('structure')
        self.monitor = lookup_service_brick('monitor')
        self.switch_module = lookup_service_brick('switches')

        self.echo_delay_table = {}  
        self.lldp_delay_table = {}  
        self.echo_interval = 0.2
        # 交换机链路的时延
        self.link_delay = {}

        if setting.DEBUG_DELAY:
            self._delay_thread = hub.spawn(self.delay_thread)



    def _send_echo_request(self):
        '''
        description: 发送echo request
        param {*} self
        return {*}
        '''
        for each_dpid in list(self.structure.sw_datapaths_table.keys()):  # list可以解决字典在迭代过程中被改变导致错误的问题
            if any(each_dpid in link for link in self.structure.link_table_backup.keys()): # 在链路的交换机才发送echo请求
                datapath = self.structure.sw_datapaths_table[each_dpid]  # 取出交换机的datapath
                parser = datapath.ofproto_parser  # 解释器
                request_time = time.time()  # 记录发送时间
                data = bytes("%.12f" % request_time, encoding="utf8")  
                echo_req = parser.OFPEchoRequest(datapath, data=data)  # 构造echo对象
                datapath.send_msg(echo_req)  
                hub.sleep(self.echo_interval)  # echo请求发送周期，防止发太快，无法处理
                if self.structure.sw_change_flag:  # 交换机状态改变，停止发送
                    break


    @set_ev_cls(ofp_event.EventOFPEchoReply, MAIN_DISPATCHER)
    def _ehco_reply_handler(self, ev):
        '''
        description: 接收echo reply
        param {*} self
        param {*} ev
        return {*}
        '''
        # 有交换机状态改变或第一次获取拓扑时，不允许获取端口统计信息
        if self.structure.sw_change_flag == True or self.structure.first_flag == True:
            return
        now_timestamp = time.time()
        try:
            data = ev.msg.data
            # echo_delay = 现在时刻-发送时的时刻
            ryu_ofps_delay = now_timestamp - eval(data)  
            self.echo_delay_table[ev.msg.datapath.id] = ryu_ofps_delay
        except Exception as error:
            logger.warning("calculate echo_delay error:%s", error)        

    # 利用LLDP时延
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        '''
        description: 解析LLDP包, 这个处理程序可以接收所有可以接收的数据包, swicthes.py l:769
        param {*} self
        param {*} ev
        return {*}
        '''
        # # 有交换机状态改变或第一次获取拓扑时，不允许获取端口统计信息
        # if self.structure.sw_change_flag == True or self.structure.first_flag == True:
        #     return
        
        data = ev.msg.data  # 取出原始数据
        pkt = packet.Packet(data)  # 取出数据包
        eth_pkt = pkt.get_protocols(ethernet.ethernet)[0]  # 解析ethernet层(数据链路层，用于判断是否为LLDP报文)
        # 非LLDP报文则退出
        if eth_pkt.ethertype != ether_types.ETH_TYPE_LLDP:
            return        

        try:
            # 接收到LLDP包的时间戳
            recv_timestamp = time.time()
            msg = ev.msg
            dpid = msg.datapath.id
            src_dpid, src_port_no = LLDPPacket.lldp_parse(msg.data)

            for port in self.switch_module.ports.keys():
                if src_dpid == port.dpid and src_port_no == port.port_no:
                    send_timestamp = self.switch_module.ports[port].timestamp
                    if send_timestamp:
                        # LLDP时延(第一个接收到LLDP的sw——触发packet in的sw) = 接收到的时间戳 - LLDP包发送时的时间戳
                        lldp_delay = recv_timestamp - send_timestamp
                    else:
                        lldp_delay = 0

                    self.lldp_delay_table.setdefault(src_dpid, {})
                    self.lldp_delay_table[src_dpid][dpid] = lldp_delay
                    # logger.warning("calculate lldp_delay successfully") 
                    self.calculate_delay(src_dpid, dpid)
                        
        except LLDPPacket.LLDPUnknownFormat as e:
            logger.warning("calculate lldp_delay error") 
            return


    def calculate_delay(self, src, dst):
        '''
        description: 根据echo和lldp时间计算链路的时延
        param {*} self
        param {*} src
        param {*} dst
        return {*}
        '''
        # echo_delay_table[?]或self.lldp_delay_table[?]不存在时
        if src not in self.echo_delay_table.keys() or dst not in self.echo_delay_table.keys() or src not in self.lldp_delay_table or dst not in self.lldp_delay_table:
            return
        # lldp_delay_table[src][?]或lldp_delay_table[dst][?]不存在时
        if src in self.lldp_delay_table or dst in self.lldp_delay_table:
            if dst not in self.lldp_delay_table[src] or src not in self.lldp_delay_table[dst]:
                return 
        # lldp_delay_table[?][x]或lldp_delay_table[?][x]不存在时
        else:
            return

        ech0_delay_src = self.echo_delay_table[src]
        ech0_delay_dst = self.echo_delay_table[dst]
        lldp_delay_forward = self.lldp_delay_table[src][dst]
        lldp_delay_reverse = self.lldp_delay_table[dst][src]

        # 以ms为单位
        sw_to_sw_delay = (lldp_delay_forward + lldp_delay_reverse - ech0_delay_src - ech0_delay_dst)*1000 / 2
        # 计算的时延为负数，则默认为1ms
        if sw_to_sw_delay < 0:
            sw_to_sw_delay = 1
        
        self.link_delay.setdefault(src, {})
        self.link_delay.setdefault(dst, {})
        # 根据上面的公式算出来的时延在正反2个方向是相同的
        self.link_delay[src][dst] = sw_to_sw_delay
        self.link_delay[dst][src] = sw_to_sw_delay
        
    def delay_thread(self):
        while True:
            self._send_echo_request()
            hub.sleep(5)

