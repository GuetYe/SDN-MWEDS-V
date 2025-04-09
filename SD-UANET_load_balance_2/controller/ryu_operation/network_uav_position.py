'''
Author: 孙石泉 786721684@qq.com
Date: 2024-02-27 08:26:13
LastEditTime: 2025-03-15 22:21:04
LastEditors: Sun Shiquan
Description: 
FilePath: \SD-UANET_load_balance_2\controller\ryu_operation\network_uav_position.py
'''

from ryu.base import app_manager  
from ryu.lib import hub
from ryu.base.app_manager import lookup_service_brick
from ryu.lib import hub
from ryu.ofproto import ofproto_v1_3

import numpy as np
from scipy.spatial import Voronoi
from config import setting
import networkx as nx
import math
import copy
from log_module import logger

class NetworkOverloadNode(app_manager.RyuApp):
    '''
    description: 获取网络的过载节点
    return {*}
    '''
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    def __init__(self, *args, **kwargs):
        super(NetworkOverloadNode, self).__init__(*args, **kwargs)
        self.name = 'uav_position'
        self.structure = lookup_service_brick("structure")  # 创建一个Networkstructure的实例
        self.monitor = lookup_service_brick("monitor")  # 创建一个Networkmonitor的实例
        self.delay = lookup_service_brick("delay")  # 创建一个Networkdelay的实例

        
        
        self.find_uav_position_thread = hub.spawn(self.find_uav_position)

        self.voronoi_flag = False
        # 目标坐标
        self.uav_position = []




    # 计算欧几里得距离
    def euclidean_distance(self, node1, node2):
        return math.sqrt((node2[0] - node1[0])**2 + (node2[1] - node1[1])**2)

    # 更新图，添加链路（链路时延作为权重）
    def add_edges_for_drone(self, G, drone_position):
        for node_id, position in setting.node_position.items():
            if node_id != setting.drone_id:  # 忽略无人机自身
                dist = self.euclidean_distance(drone_position, position)
                if dist <= setting.R:  # 如果距离小于R，则建立链路
                    propagation_delay = (dist / setting.propagation_speed)*1000
                     # 传输时延：数据包大小 / 带宽
                    transmission_delay = (setting.packet_size / setting.bandwidth)*1000
                    delay =  propagation_delay  + transmission_delay + 1
                    
                    G.add_edge(setting.drone_id, node_id, delay=delay)  # 添加链路和时延

                    
    def find_uav_position(self):
        '''
        description: 寻找网络中的uav节点的（x，y）坐标，构建新的网络拓扑，优化网络性能。ryu的子线程
        param {*} self
        return {*}
        '''
        hub.sleep(30)

        if self.voronoi_flag == False:
            # 获取地面节点坐标
            points = np.array(list(setting.node_position.values()))
            # 计算维诺图
            vor = Voronoi(points)
            # 提取维诺点的坐标
            voronoi_points = vor.vertices
            # 打印维诺点的坐标
            logger.info("维诺图的维诺点坐标：")
            logger.info(voronoi_points)
            self.voronoi_flag = True
        while True:
            # 计算在不同维诺点位置时的MST代价
            mst_costs = []
            
            for v_point in voronoi_points:
                self.G = copy.deepcopy(self.structure.network_topology)
                # 更新图，将无人机移动到当前维诺点位置
                self.add_edges_for_drone(self.G, v_point)

                # 计算最小生成树
                mst = nx.minimum_spanning_tree(self.G)

                # 计算MST的总代价
                total_cost = sum([data['delay'] for _, _, data in mst.edges(data=True)])
                mst_costs.append((v_point, total_cost))

            # 返回代价最小的维诺点作为最优位置
            optimal_position = min(mst_costs, key=lambda x: x[1])
            self.uav_position = optimal_position[0]
            logger.info("最优无人机位置是:%s，总代价为：%s" % (self.uav_position, optimal_position[1]))
            hub.sleep(10)


