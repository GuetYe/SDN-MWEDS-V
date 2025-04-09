'''
Author: 孙石泉 786721684@qq.com
Date: 2023-11-22 09:57:32
LastEditTime: 2024-12-03 19:53:03
LastEditors: Sun Shiquan
Description: 
FilePath: \SD-UANET_load_balance_mac\controller\ryu_operation\network_monitor.py
'''


from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.lib import hub
from ryu.base.app_manager import lookup_service_brick

from config import setting
from operator import attrgetter
from log_module import logger

class Networkmonitor(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    """ 监控网络流量状态"""
    def __init__(self, *args, **kwargs):
        super(Networkmonitor, self).__init__(*args, **kwargs)
        self.name = 'monitor'
        self.structure = lookup_service_brick("structure")  # 创建一个Networkstructure的实例

        # {dpid:{port_no: (config, state, curr_speed, max_speed)}}交换机的端口配置和特征
        self.dpid_port_fueatures_table = {} 
        # {(dpid, port_no): (stat.tx_bytes, stat.rx_bytes, stat.rx_errors, stat.duration_sec,stat.duration_nsec, stat.tx_packets, stat.rx_packets)}  
        # sw的port的数据包和时间状态信息
        self.port_stats_table = {}
        self.port_speed_table = {} # {(dpid, port_no): [speed, .....]} sw的port的 流量速度
        # {dpid: {port_no: used_bw}}  sw的port的剩余带宽
        self.port_remained_bw = {}
        # 链路的丢包率
        self.link_loss = {}

        # 详细解释见ryu->ryu->ofproto->ofproto_v1_3.py文件
        # 配置OpenFlow交换机端口的行为：禁用（关闭）端口、禁用接收数据包、禁用转发数据包、禁止生成Packet-In消息
        self.config_dict = {ofproto_v1_3.OFPPC_PORT_DOWN: 'Port Down',
                            ofproto_v1_3.OFPPC_NO_RECV: 'No Recv',
                            ofproto_v1_3.OFPPC_NO_FWD: 'No Forward',
                            ofproto_v1_3.OFPPC_NO_PACKET_IN: 'No Pakcet-In'}
        
        # 端口状态：断开、阻塞、活跃
        self.state_dict = {ofproto_v1_3.OFPPS_LINK_DOWN: "Link Down",
                      ofproto_v1_3.OFPPS_BLOCKED: "Blocked",
                      ofproto_v1_3.OFPPS_LIVE: "Live"}

        # 调试network_monitor.py时运行的线程
        if setting.DEBUG_MONITOR:
            self._monitor_thread = hub.spawn(self.monitor_thread)





    def _request_stats(self):
        '''
        description: # 主动发送request，请求获取状态信息
        param {*} self
        return {*}
        '''

        
        # 保存一下structure实例的datapath字典
        datapaths_table = self.structure.sw_datapaths_table.values()
        # 向所有连接状态的交换机发送相关状态请求
        for datapath in list(datapaths_table):
            if self.structure.sw_change_flag:  # 交换机状态改变
                break
            # 初始化端口的配置和特征
            self.dpid_port_fueatures_table.setdefault(datapath.id, {})
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser

            # 1. 端口统计请求(包括端口的收发数据字节数、时刻)
            req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)  # 所有端口
            datapath.send_msg(req)
            # 2. 流的统计请求(交换机和其每个端口的流信息)
            req = parser.OFPFlowStatsRequest(datapath)
            datapath.send_msg(req)
            # 3. 端口描述请求(包括端口的配置、状态、当前速度)
            req = parser.OFPPortDescStatsRequest(datapath, 0) 
            datapath.send_msg(req)





    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def port_desc_stats_reply_handler(self, ev):
        '''
        description: 处理上面请求的回复1.OFPPortDescStatsReply，获取端口配置、状态
        param {*} self
        param {*} ev
        return {*}
        '''
        msg = ev.msg
        body = msg.body  # 交换机回复的消息内容
        dpid = msg.datapath.id
        logger.info("-----port's config and stats-----")
        logger.info("dpid    port    config   state     curr_speed     max_speed")
        for ofport in body:  
            if ofport.port_no != ofproto_v1_3.OFPP_LOCAL:  # 0xfffffffe  4294967294,本地回环端口
                # 端口配置在配置字典中
                if ofport.config in self.config_dict:
                    config = self.config_dict[ofport.config]
                # 激活状态，从而允许流经该端口的数据包
                else:
                    config = 'Up'
                # 端口在链路的状态在状态字典中
                if ofport.state in self.state_dict:
                    state = self.state_dict[ofport.state]
                # 激活状态，可用于数据流经
                else:
                    state = 'Up'
                # curr_speed,max_speed在仿真或实际换机有时为0
                try:
                    ofport_curr_speed = ofport.curr_speed  # 端口当前速度，单位：bit/s
                    ofport_max_speed = ofport.max_speed  # 端口最大速度，单位：bit/s
                    print("ofport.curr_speed:%d  ofport.max_speed:%d" % (ofport.curr_speed, ofport.max_speed))
                # 端口流速有时在properties中
                except:  
                    ofport_curr_speed = ofport.properties[0].curr_speed  # 端口当前速度，单位：bit/s
                    ofport_max_speed = ofport.properties[0].max_speed  # 端口最大速度，单位：bit/s
                    print("properties[0].curr_speed:%d  properties[0].max_speed:%d" % (ofport.properties[0].curr_speed, ofport.properties[0].max_speed))
                # 无线端口时，无线网卡不给出最大带宽
                if ofport_max_speed == 0:
                    ofport_max_speed = setting.WIRELESS_MAX_SEPPD
                # 存储配置，状态, 
                self.dpid_port_fueatures_table[dpid][ofport.port_no] = (config, state, ofport_curr_speed, ofport_max_speed)
        
                print(" %d        %d      %s      %s      %.3f    %.3f" % (dpid, ofport.port_no, config, state, 
                                 ofport_curr_speed, ofport_max_speed))
                print("\n")

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_table_reply_handler(self, ev):
        '''
        description: 处理上面请求的回复2.OFPPortStatsReply，获取端口信息统计存储端口统计信息, 见OFPPortStats, 发送bytes、接收bytes、生效时间duration_sec等
        Replay message(state) content:
            (stat.port_no,
             stat.rx_packets, stat.tx_packets,
             stat.rx_bytes, stat.tx_bytes,
             stat.rx_dropped, stat.tx_dropped,
             stat.rx_errors, stat.tx_errors,
             stat.rx_frame_err, stat.rx_over_err,
             stat.rx_crc_err, stat.collisions,
             stat.duration_sec, stat.duration_nsec))
        param {*} self
        param {*} ev
        return {*}
        '''
        # 有交换机状态改变或第一次获取拓扑时，不允许获取端口统计信息
        if self.structure.sw_change_flag == True or self.structure.first_flag == True:
            return

        body = ev.msg.body
        dpid = ev.msg.datapath.id
        
        logger.info("-----switch port's remain bandwidth -----")
        logger.info("switch  port_no  rx_bytes tx_bytes  used_bw  used_bw_radio  remain_bw tx_packets rx_packets")

        for stat in sorted(body, key=attrgetter("port_no")):
            port_no = stat.port_no
            # 如果不是本地端口(控制器与交换机之间的本地连接端口)？
            if port_no != ofproto_v1_3.OFPP_LOCAL:
                # self.port_stats_table存的信息，用于计算已用带宽和丢包率
                key = (dpid, port_no)
                value = (stat.tx_bytes, stat.rx_bytes, stat.rx_errors,
                         stat.duration_sec, stat.duration_nsec, stat.tx_packets, stat.rx_packets)
                # 保存端口统计信息，最多保存前3次
                self._save_stats(self.port_stats_table, key, value, 3)  
                # 获得已经存了的统计信息(上面刚刚存的)
                stats = self.port_stats_table[key]  
                # 有两次以上的信息才计算剩余带宽
                if len(self.port_stats_table[key]) > 1:  
                    self.calculate_remain_bw(dpid, port_no, stats)
                
        logger.info("\n")         
        # 计算所有链路的丢包率
        self.calculate_loss()


    def calculate_remain_bw(self, dpid, port_no, stats):
        '''
        description: 计算并保存端口的已用带宽
        param {*} dpid 交换机dpid
        param {*} port_no 端口号
        param {*} stats 存储的端口状态信息stats
        return {*}
        '''
        # 前一次和这次的端口处理的字节数
        pre_bytes = stats[-2][0] + stats[-2][1]
        now_bytes = stats[-1][0] + stats[-1][1]
        # 2次接收数据的时间差,单位s,1s=10^9ns
        delta_time = stats[-1][3] + stats[-1][4]/10**9 - stats[-2][3] - stats[-2][4]/10**9
        # 计算的端口流量速度，byte/s
        calculate_speed = (now_bytes - pre_bytes) / delta_time
        speed = calculate_speed if calculate_speed > 0 else 0
        # 已用带宽：byte/s到bit/s
        used_bw = speed * 8
        # 端口的剩余带宽
        self.port_remained_bw.setdefault(dpid, {})
        # 字典的get方法获取键的值，但键不存在时返回None
        port_state = self.dpid_port_fueatures_table.get(dpid).get(port_no)
        if port_state:
            # 剩余带宽 = 端口最大流速 - 现在的流速 
            port_remained_bw = port_state[3] - used_bw
            self.port_remained_bw[dpid][port_no] = port_remained_bw
        
            print("  %d      %d  %d %d %d    %.2f     %d  %d  %d %d" % \
                (dpid, port_no, stats[-1][1], stats[-1][0], 
                used_bw, (used_bw/port_state[3]*100), port_remained_bw, stats[-1][5], stats[-1][6], delta_time))
       


    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        '''
        description: 端口的流表处理统计信息，处理上面的3.OFPFlowStatsRequest请求
        param {*} self
        param {*} ev
        return {*}
        '''
        # 端口的流表处理统计信息
        msg = ev.msg
        body = msg.body
        logger.info("----- switch port's flow entry -----")
        logger.info("dpid  table_id   priority   eth_type   in_port   eth_src    eth_dst   src_ip         dst_ip         out_port    count")
        # 获取交换机每个流表的信息
        for each_state in body:

            # logger.info("each_state:", each_state)

            dpid = msg.datapath.id
            priority = each_state.priority
            table_id = each_state.table_id
            count = each_state.packet_count
            eth_type = each_state.match.get("eth_type")
            in_port = each_state.match.get("in_port")
            eth_src = each_state.match.get("eth_src")
            eth_dst = each_state.match.get("eth_dst")
            src_ip = each_state.match.get("ipv4_src")
            dst_ip = each_state.match.get("ipv4_dst")
            mpls_label = each_state.match.get("mpls_label")
            out_port = ""
            
            if in_port == None:
                in_port = "None"
            elif in_port == ofproto_v1_3.OFPP_LOCAL:
                in_port = "LOCAL"
            else:
                in_port = str(in_port)
            if each_state.instructions:
                for each_port in each_state.instructions[0].actions:
                    if hasattr(each_port, "port"):
                        if each_port.port == ofproto_v1_3.OFPP_LOCAL:
                            out_port = out_port + "LOCAL 、"
                        elif each_port.port == ofproto_v1_3.OFPP_ALL:
                            out_port = out_port + "ALL 、"
                        elif each_port.port == ofproto_v1_3.OFPP_CONTROLLER:
                            out_port = out_port + "CONTRONLLER 、"
                        elif each_port.port == None:
                            out_port = out_port + "None 、"
                        else:
                            out_port = out_port + str(each_port.port)
            
            if setting.SHOW_FLOW_ENTRY:
                print(" %2d      %2d       %5d      %s   %s   %s     %s     %s   %s     %s    %s" % \
                        (dpid, table_id, priority, eth_type, in_port, eth_src, eth_dst, src_ip, dst_ip, out_port, count))

        if setting.SHOW_FLOW_ENTRY:
            print("\n")

    
    @staticmethod
    def _save_stats(_dict, key, value, max_length):
        '''
        description: 向某个已有字典存数据
        param {*} _dict 已有的字典
        param {*} key 键
        param {*} value 值
        param {*} max_length 字典的长度
        return {*}
        '''
        # 在字典末尾添加数据
        if key not in _dict:
            _dict[key] = []
        _dict[key].append(value)
        # 长度超过max_length，弹出最前面的数据
        if len(_dict[key]) > max_length:
            _dict[key].pop(0)  


    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def _port_status_handler(self, ev):
        '''
        description: 交换机端口状态变化情况(增加、删除、更改配置)
        param {*} self
        param {*} ev
        return {*}
        '''
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto

        if msg.reason == ofp.OFPPR_ADD:
            reason = 'ADD'
        elif msg.reason == ofp.OFPPR_DELETE:
            reason = 'DELETE'
        elif msg.reason == ofp.OFPPR_MODIFY:
            reason = 'MODIFY'
        else:
            reason = 'unknown'
        # %d  msg.desc,
        logger.info('switch %016x port status has changed,reason:%s'% dp.id,  reason)


    def calculate_loss(self):
        '''
        description: 计算链路的丢包率
        param {*} self
        return {*}
        '''
        # 有交换机状态改变或第一次获取拓扑时，不允许获取端口统计信息
        if self.structure.sw_change_flag == True or self.structure.first_flag == True:
            return
        
        for link, port in self.structure.link_table_backup.items():
            src_dpid, dst_dpid = link
            src_port, dst_port = port
            self.link_loss.setdefault((src_dpid, dst_dpid), None)
            if (src_dpid, src_port) in self.port_stats_table.keys() and (dst_dpid, dst_port) in self.port_stats_table.keys():
                src_port_stats = self.port_stats_table[(src_dpid, src_port)]
                dst_port_stats = self.port_stats_table[(dst_dpid, dst_port)]
                try:
                    src_tx = src_port_stats[-1][5] - src_port_stats[-2][5]
                    src_rx = src_port_stats[-1][6] - src_port_stats[-2][6]
                    dst_tx = dst_port_stats[-1][5] - dst_port_stats[-2][5]
                    dst_rx = dst_port_stats[-1][6] - dst_port_stats[-2][6]
                # 读取已存的信息，刚启动时有时索引超出范围？？
                except:
                    return
                
                calculate_forward_loss = (src_tx - dst_rx) / src_tx * 100
                calculate_reverse_loss = (dst_tx - src_rx) / dst_tx * 100

                # 1.src到dst的丢包率计算，保留3位小数
                src_to_dst_loss = calculate_forward_loss if calculate_forward_loss > 0 else 5.0
                # 2.dst到src的丢包率计算，保留3位小数
                dst_to_src_loss = calculate_reverse_loss if calculate_reverse_loss > 0 else 5.0
                self.link_loss[(src_dpid, dst_dpid)] = round(src_to_dst_loss, 3)
                self.link_loss[(dst_dpid, src_dpid)] = round(dst_to_src_loss, 3)
                
            else:
                logger.info("<calculate loss error, {} is not in structure.link_table".format(link))
        
        logger.info("link_loss:{}".format(self.link_loss))
        logger.info("\n")
        

    def monitor_thread(self):
        '''
        description: 调试network_monitor.py时运行的线程
        param {*} self
        return {*}
        '''
        while True:
            self._request_stats()
            hub.sleep(5)
