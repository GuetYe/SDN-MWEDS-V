'''
Author: 孙石泉 786721684@qq.com
Date: 2023-11-24 09:14:50
LastEditTime: 2025-02-27 16:14:36
LastEditors: Sun Shiquan
Description: 
FilePath: \SD-UANET_load_balance_2\controller\run\main.py
'''


import sys
sys.path.append("../")

import time

from ryu.base import app_manager    
from ryu.base.app_manager import lookup_service_brick
from ryu.lib import hub


from PySide2.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsLineItem, QGraphicsTextItem, \
                              QGraphicsPixmapItem, QMainWindow
from PySide2.QtCore import Qt, QCoreApplication, QPointF, QTimer
from PySide2.QtGui import QPixmap

from ryu_operation import controller_north_interface

from ryu_operation.log_module import logger
import random

from ryu.lib.packet import packet, ipv4, ethernet, arp
from ryu.lib.packet import ether_types
import config.setting as setting

class NodeWithImage(QGraphicsPixmapItem):
    '''
    description: 图片节点的类
    return {*}
    '''
    def __init__(self, x, y, label, image_path, size, parent=None):
        '''
        description: 
        param {*} self
        param {*} x 节点x坐标
        param {*} y 节点y坐标
        param {*} label 节点标签
        param {*} image_path 图片路径
        param {*} size 图片大小sizeXsize
        param {*} parent
        return {*}
        '''
        # QPixmap加载图像
        pixmap = QPixmap(image_path).scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        super(NodeWithImage, self).__init__(pixmap, parent)
        # NodeWithImage 的父项是 QGraphicsView 中的 QGraphicsScene。
        # 节点图片是以其左上角为原点，而我们通常更希望指定的 (x, y) 是节点的中心，因此需要进行适当的偏移
        # (x, y)是图片的中心点坐标，(x - size / 2, y - size / 2)是图片的左上角坐标
        # Graphics View系统有3个坐标系，图形项坐标、场景坐标、视图坐标
        self.setPos(x - size / 2, y - size / 2)

        text = QGraphicsTextItem(label, self)
        # (x, y) 表示文本左上角相对于 NodeWithImage 左上角的偏移量
        text.setPos(-text.boundingRect().width() / 2, -size / 2 - 10)

class TopologyView(QGraphicsView):
    '''
    description: 显示图场景中的内容,显示界面的主要逻辑在这
    return {*}
    '''
    def __init__(self, structure, parent=None):
        super(TopologyView, self).__init__(parent)
        # QGraphicsScene：图场景
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # 数据结构用于存储节点和连接
        self.nodes = {}

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_topology)
        self.timer.start(3000)

        self.structure = structure
        # 拓扑中节点的初始位置
        self.topo_info = {1:[150, 5], 2:[150, 95], 3:[150, 185], 4:[50, 275], 5:[250, 275], 6:[150, 365],  21:[150, 250]}

        # 用集合记录已经添加的连接线
        self.added_connections = set()  

        #虚拟的拓扑连接，Qt显示.1、需更改的地方
        self.virtual_link_list = [(5,21), (6,21), (4,21), (3,21), (3,4)]
    
    
    def add_node_with_image(self, identifier, x, y, label, image_path, size):
        '''
        description: 在图场景中添加图片节点
        param {*} self
        param {*} identifier 节点序号
        param {*} x 节点x坐标
        param {*} y 节点y坐标
        param {*} label 节点标签
        param {*} image_path 图片路径
        param {*} size 图片大小(size x size)
        return {*}
        '''
        node_with_image = NodeWithImage(x, y, label, image_path, size)
        # scene.addItem：在图场景中添加图形项的基类
        self.scene.addItem(node_with_image)
        # 节点的属性 节点跳频+节点连接关系
        self.nodes[identifier] = {'item': node_with_image, 'connections': set()}
        


    def add_connection(self, identifier1, identifier2):
        '''
        description: 在图场景中画线
        param {*} self
        param {*} identifier1 节点1序号
        param {*} identifier2 节点2序号
        return {*}
        '''
        if identifier1 in self.nodes and identifier2 in self.nodes:
            node1 = self.nodes[identifier1]['item']
            node2 = self.nodes[identifier2]['item']

            line = QGraphicsLineItem(
                                    node1.pos().x() + node1.pixmap().width() / 2,
                                    node1.pos().y() + node1.pixmap().height() / 2,
                                    node2.pos().x() + node2.pixmap().width() / 2,
                                    node2.pos().y() + node2.pixmap().height() / 2
                                    )
            self.scene.addItem(line)
            # 更新数据结构
            self.nodes[identifier1]['connections'].add(line)
            self.nodes[identifier2]['connections'].add(line)


    def remove_node(self, identifier):
        '''
        description: 在图场景中删除图片节点
        param {*} self
        param {*} identifier 节点的序号
        return {*}
        '''
        if identifier in self.nodes:
            node_info = self.nodes.pop(identifier)
            self.scene.removeItem(node_info['item'])

            for connection in node_info['connections']:
                self.scene.removeItem(connection)
            
        # 删除节点相关的连接线信息
        connections_to_remove = set()
        for key in self.added_connections:
            if identifier in key:
                connections_to_remove.add(key)

        # 在画过的连接线集合中移除与节点相关的连接线信息
        self.added_connections -= connections_to_remove

        
    def refresh_topology(self):
        '''
        description: 在QT的定时器中刷新页面
        param {*} self
        return {*}
        '''
        if self.structure.sw_dpid_list and self.structure.sw_change_flag == False:
                
                # 1.添加节点
                for each_dpid in self.structure.sw_dpid_list:
                    if each_dpid not in self.nodes.keys():
                        # 固定位置上添加节点
                        if each_dpid in self.topo_info.keys():
                            self.add_node_with_image(each_dpid,
                                                     self.topo_info[each_dpid][0],
                                                     self.topo_info[each_dpid][1], "{}".format(each_dpid),
                                                     "../qt_ui/router_color.png", 30
                                                     )

                        # 随机位置上添加节点
                        else:
                            self.add_node_with_image(each_dpid,
                                                     random.uniform(0, self.width()),
                                                     random.uniform(0, self.height()), "{}".format(each_dpid),
                                                     "../qt_ui/router_color.png", 30
                                                     )
                    # 添加界面显示的图标.2、需更改的地方
                    self.add_node_with_image(21,
                                            self.topo_info[21][0],
                                            self.topo_info[21][1], "{}".format(21),
                                            "../qt_ui/UAV.png", 30
                                            )

                # # 2.删除节点
                # for each_node in list(self.nodes.keys()):
                #     logger.info("each_node:{} sw_dpid_list:{}".format(each_node, self.structure.sw_dpid_list))
                #     if each_node not in self.structure.sw_dpid_list:
                        
                #         self.remove_node(each_node)
                #         logger.info("remove node{}".format(each_node))

                
                # 3.画节点之间的链路
                for (src_dpid, dst_dpid) in self.structure.link_table_backup.keys():
                    if (src_dpid, dst_dpid) not in self.added_connections \
                        and src_dpid in self.nodes.keys() \
                        and dst_dpid in self.nodes.keys() :
                        # 连接2个节点
                        self.add_connection(src_dpid, dst_dpid)
                        # 将连接线添加到已画过的集合中
                        self.added_connections.add((src_dpid, dst_dpid))  

                # 画虚拟链路，3、可更改的地方
                for (src_dpid, dst_dpid) in self.virtual_link_list:
                    if (src_dpid, dst_dpid) not in self.added_connections \
                        and src_dpid in self.nodes.keys() \
                        and dst_dpid in self.nodes.keys() :
                        # 连接2个节点
                        self.add_connection(src_dpid, dst_dpid)
                        # 将连接线添加到已画过的集合中
                        self.added_connections.add((src_dpid, dst_dpid))  

        # # 模拟节点的移动
        # for identifier, node_info in self.nodes.items():
        #     new_x = node_info['item'].pos().x() + random.uniform(-10, 10)
        #     new_y = node_info['item'].pos().y() + random.uniform(-10, 10)
        #     node_info['item'].setPos(QPointF(new_x, new_y))
            
        #     # 更新连接线的位置
        #     for connection in node_info['connections']:
        #         line = connection.line()
        #         start_point = line.p1()
        #         end_point = line.p2()

        #         # 判断哪个端点是当前节点
        #         other_point = start_point if start_point != node_info['item'].pos() else end_point
        #         # 更新当前节点的连接线的位置
        #         connection.setLine(
        #             node_info['item'].pos().x() + node_info['item'].pixmap().width() / 2,
        #             node_info['item'].pos().y() + node_info['item'].pixmap().height() / 2,
        #             other_point.x(),
        #             other_point.y()
        #         )
    

        logger.info("QT刷新页面成功")
      
      
    def resizeEvent(self, event):
        # 在窗口大小变化时调整 QGraphicsView 的视口大小
        super(TopologyView, self).resizeEvent(event)
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)



class MainWindow(QMainWindow):
    '''
    description: QT界面的QMainWindow类，画主界面
    return {*}
    '''
    def __init__(self):
        super(MainWindow, self).__init__()
        # 设置窗口位置和大小
        self.setGeometry(260, 260, 300, 400)
        self.setWindowTitle("Network Topology")

        self.structure = lookup_service_brick("structure")  # 创建一个Networkstructure的实例

        self.topology_view = TopologyView(self.structure)
        self.setCentralWidget(self.topology_view)



class Networkmain(app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        super(Networkmain, self).__init__(*args, **kwargs)
        self.name = 'main'
        self.structure = lookup_service_brick("structure")  # 创建一个Networkstructure的实例
        self.monitor = lookup_service_brick("monitor")  # 创建一个Networkmonitor的实例
        self.delay = lookup_service_brick("delay")  # 创建一个Networkdelay的实例
        self.arp_handle = lookup_service_brick("arp") # 创建1个ArpHandler实例
        self.host_get_msg = lookup_service_brick("host_get_msg") #创建1个host_get_msg实例
        self.uav_position = lookup_service_brick("uav_position") #创建1个uav_position实例

        self.target_position = self.uav_position.uav_position

        # ryu程序的线程
        self.main_thread = hub.spawn(self.main)
        self.qt_thread = hub.spawn(self.qt)
        


    def send_target_position(self):
        self.target_position = self.uav_position.uav_position
        if self.host_get_msg.uav_datapath != None and self.host_get_msg.uav_port != None and self.host_get_msg.uav_mac != None and self.host_get_msg.uav_ip != None:
            if self.target_position.any():
                self.uav_datapath = self.host_get_msg.uav_datapath
                self.uav_port = self.host_get_msg.uav_port
                self.uav_mac = self.host_get_msg.uav_mac
                self.uav_ip = self.host_get_msg.uav_ip

                # 转发目标坐标数据到申请的交换机的主机上
                ofproto = self.uav_datapath.ofproto
                parser = self.uav_datapath.ofproto_parser

                # 构造ARP回复包，附带结果数据，有控制器执行packet_out，返回到申请的主机上
                pkt = packet.Packet()
                pkt.add_protocol(ethernet.ethernet(ethertype=ether_types.ETH_TYPE_ARP,
                                                dst=self.uav_mac,
                                                src=setting.CONTROLLER_MAC))  # 这里的mac随意写，只是用作构造ARP包
                pkt.add_protocol(arp.arp(opcode=arp.ARP_REPLY,
                                        src_mac=setting.CONTROLLER_MAC,
                                        src_ip=setting.CONTROLLER_IP[0],
                                        dst_mac=self.uav_mac,
                                        dst_ip=self.uav_ip))

                pkt.serialize()
                my_data = 'TargetPosition(target_position=%s)' % self.target_position
                data = pkt.data + bytearray(my_data.encode())
                actions = [parser.OFPActionOutput(ofproto.OFPP_LOCAL)]
                out = parser.OFPPacketOut(datapath=self.uav_datapath,
                                        buffer_id=ofproto.OFP_NO_BUFFER,
                                        in_port=ofproto.OFPP_CONTROLLER,
                                        actions=actions,
                                        data=data)

                self.uav_datapath.send_msg(out)
                logger.info("the target_position is returned to the uav_jetson %s" % self.uav_ip)





    def main(self):

        time_start = time.time()

        # or len(self.structure.sw_dpid_list) < 7
        while (time.time() - time_start) <= 20 or len(self.structure.sw_dpid_list) < 3:
            # 主动获取拓扑
            self.structure.get_topology(ev=None, way=1)
            hub.sleep(2)
        while True:
            self.structure.get_topology(ev=None, way=1)
            hub.sleep(5)
            self.monitor._request_stats()
            hub.sleep(5)
            self.delay._send_echo_request()
            hub.sleep(5)
            # 发送无人机目标位置给SDN板
            self.send_target_position()

            time_current = time.time()  # 记录程序当前截至运行时间
            time_accumulated = time_current - time_start  # 计算累计时间
            time_m, time_s = divmod(time_accumulated, 60)
            time_h, time_m = divmod(time_m, 60)
            logger.info("The controller's program has been running for:%04d:%02d:%02d " % (time_h, time_m, time_s))
            print('\n')

            # self.all_hosts = controller_north_interface.get_all_hosts()
            # logger.info("北向接口获取的hosts：{}".format(self.all_hosts))

            # self.sw7_all_hosts = controller_north_interface.get_host(7)
            # logger.info("北向接口获取sw7的hosts：{}".format(self.sw7_all_hosts))




    def qt(self):
        

        app = QApplication([])
        window = MainWindow()
        window.show()
        while True:
            #把QT页面刷新代码放这下面或者定时器设置时间少一点，页面刷新会快，但是ryu的程序就会变慢

            
            QCoreApplication.processEvents()
            window.show()
            hub.sleep(3)

