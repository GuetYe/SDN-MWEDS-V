'''
Author: 孙石泉 786721684@qq.com
Date: 2023-11-22 10:01:34
LastEditTime: 2025-02-27 16:13:21
LastEditors: Sun Shiquan
Description: 
FilePath: \SD-UANET_load_balance_2\controller\config\setting.py
'''






# 1satrt-------------network_structure.py-------------

DEBUG_STRUCTURE = False
# 控制器的ip和mac
CONTROLLER_IP = ['10.0.0.1', '10.0.0.2']
CONTROLLER_MAC = '0a:0b:0c:0d:0e:0f'

link_table_reset_interval = 30

synthetic_bandwidth_weight = 0.7
synthetic_delay_weight = 0.2
synthetic_loss_weight = 0.1


link_list = [(1,2),(1,21), (2,1),(2,3), (3,2),(3,4),(3,5), (4,3),(4,6), (5,3),(5,6),(5,21), (6,4),(6,5),(6,21), (21,1),(21,5),(21,6)]
            
# link_list = [(1,2), (1,3), (1,4), (1,6), (2,1), (4,1), (3,1), (6,1),\
#              (2,5), (2,6), (5,2), (6,2),\
#              (3,4), (3,5), (4,3), (5,3),\
             
#              (5,6), (6,5)
#             ]

# 1end1-------------network_structure.py-------------


# 2start-------------network_monitor.py-------------

DEBUG_MONITOR = False
SHOW_FLOW_ENTRY = True
WIRELESS_MAX_SEPPD = 30000000  # 无线链路最大带宽，单位bit/s 30M

# 2end-------------network_monitor.py-------------

# 3start-------------network_delay.py-------------

DEBUG_DELAY  = False



# 3end-------------network_delay.py-------------


# 4-start-------------network_shortest_path.py.py-------------

CALCULATE_SHORTEST_PATH_METHOD = 'dijkstra'  # the calculation method of shortest path
DST_MULTICAST_IP = {'224.1.1.1': ["10.0.0.2", "10.0.0.4", "10.0.0.11"], }  # 组播地址： 组成员的ip


# LLDP:01:80:c2:00:00:0e

# 每台交换机的多播mac地址
switch_mult_mac = {1:"01:80:c2:00:00:0e", 2:"01:80:c2:00:00:0e", 3:"01:80:c2:00:00:0e", 4:"01:80:c2:00:00:0e", \
               5:"01:80:c2:00:00:0e", 6:"01:80:c2:00:00:0e", 7:"44:DF:65:92:EF:39", 8:"44DF656CD76F", \
                9:"01:80:c2:00:00:0e", 10:"44DF656CD1E7", 11:"01:80:c2:00:00:0e", 12:"01:80:c2:00:00:0e", \
                13:"44DF656D1B25", 14:"01:80:c2:00:00:0e"}
# switch_mult_mac = {1:"44:DF:65:92:EF:39", 2:"D4:DA:21:AC:66:7C", 3:"A4:A9:30:7D:76:F5", 4:"D4:DA:21:AC:71:62", \
#                5:"44:DF:65:6D:01:57", 6:"30:B4:9E:5D:F4:AC", 7:"D8:3A:DD:42:0F:70"}

MPLS_LABEL = 1
# 4end-------------network_shortest_path.py.py-------------


# 5-start-host_multi_attr_decision_make.py---------------
REMAIN_CAPACITY_LIMITATION = 0.05  # 存储节点的剩余容量的极限，超过该值则不会被选择为存储节点

LOAD_FACTOR = 0.4
CPU_UTI_FACTOR = 0.3
MEM_UTI_FACTOR = 0.2
CAPACITY_FACTOR = 0.1

INTERVAL_INSTALL_FLOW = 5

switch_ip = ["10.0.0.101", "10.0.0.102", "10.0.0.103", "10.0.0.104", "10.0.0.105", "10.0.0.106", "10.0.0.107",
                           "10.0.0.108", "10.0.0.109", "10.0.0.110", "10.0.0.111"]

host_ip = ["10.0.0.51", "10.0.0.52", "10.0.0.53", "10.0.0.54", "10.0.0.55", "10.0.0.56", "10.0.0.57", \
                        "10.0.0.59", "10.0.0.60", "10.0.0.66"]

# 5-end-host_multi_attr_decision_make.py-----------------

# 6-start-host_multi_attr_decision_make.py---------------
# 计算节点网络状态属性得分的权重因子
link_score_bandwidth_weight = 0.7
link_score_delay_weight = 0.2
link_score_loss_weight = 0.1

# 属性矩阵的权重因子
attribute_matrix_weight = [0.6, 0.1, 0.3]

# 6-end-host_multi_attr_decision_make.py---------------


# 6-start-network_uav_position.py---------------
node_position = {1:[6.6, 7.2], 2:[2.7, 7.1], 3:[5.1, 0] ,4:[2.5, 0.2], 5:[4.0, 3.8], 6:[0, 4.4]}

client_id = 1  # 客户端节点
server_ids = [2, 3, 4]  # 服务器节点
drone_id = 7  # 无人机节点
# 无线通信半径R
R = 3  # 可以根据实际情况调整
# 传播时延：传播速度 = 3 * 10^8 m/s
propagation_speed = 3 * 10**8  # 传播速度（米/秒）
bandwidth = 20**6  # 带宽为1Mbps
packet_size = 800 * 8  # 数据包大小为1500字节 = 12000比特

# 6-end-network_uav_position.py---------------







from pathlib import Path
from functools import reduce

WORK_DIR = Path.cwd().parent

# setting.py
FACTOR = 0.9  # the coefficient of 'bw' , 1 - FACTOR is the coefficient of 'delay'


DISCOVERY_PERIOD = 0.8  # discover network structure's period, the unit is seconds.

MONITOR_PERIOD = 3  # monitor period, bw

DELAY_PERIOD = 3  # detector period, delay

SCHEDULE_PERIOD = 3  # shortest forwarding network awareness period

PRINT_SHOW = True  # show or not show print

INIT_TIME = 0  # wait init for awareness

PRINT_NUM_OF_LINE = 8  # 一行打印8个值

# LOGGER = True  # 是否保存日志
LOGGER = False  # 是否保存日志


LINKS_INFO = WORK_DIR / "mininet/links_info/links_info.xml"  # 链路信息的xml文件路径

# SRC_IP = "10.0.0.1"
# DST_MULTICAST_IP = {'224.1.1.1': 1, }  # 组播地址： 标号（下面的索引号）
# DST_GROUP_IP = [["10.0.0.2", "10.0.0.3", "10.0.0.4"], ]  # 组成员的ip，（索引为上面的标号）



WEIGHT = 'weight'
# FINAL_SWITCH_FLOW_IDEA = 1

finish_time_file = WORK_DIR / "mininet/finish_time.json"


def list_insert_one_by_one(list1, list2):
    l = []
    for x, y in zip(list1, list2):
        l.extend([x, y])
    return l


def gen_format_str(num):
    fmt = ''
    for i in range(num):
        fmt += '{{:<{}}}'
    # fmt += '\n'
    return fmt


# 只能打印key: value的两列，还不如用pandas
def print_pretty_table(param, titles, widths, table_name='zzlong'):
    """
        打印一个漂亮的表
    :param param: 要打印的字典，dict
    :param titles: 每列的title
    :param widths: 每列的宽度
    :param table_name: 表名字
    :param logger: 用什么打印 print / logger.info
    :return: None
    """
    f = print
    # widths系列中取2个元素都执行lambda函数，得到的结果再与第三个元素做lambda函数......
    all_width = reduce(lambda x, y: x + y, widths)
    cut_line = "=" * all_width
    # 表名字
    w = all_width - len(table_name)
    if w > 1:
        f(cut_line[:w // 2] + table_name + cut_line[w // 2: w])
    else:
        f("=" + table_name + "=")


    # 以表格输出
    if isinstance(param, dict):
        # 获得{:^{}}多少个这个
        fmt = gen_format_str(len(titles))
        # 确定宽度
        width_fmt = fmt.format(*widths)
        # 确定值
        title_fmt = width_fmt.format(*titles)
        # 打印第一行title
        f(title_fmt)
        # 打印分割线
        f(cut_line)
        # 打印每一行的值
        for k, v in param.items():
            content_fmt = width_fmt.format(str(k), str(v))
            # 打印内容
            f(content_fmt)

    # 打印分割线
    f(cut_line + '\n')


# FIXME: youwenti
def print_pretty_list(param, num, width=10, table_name='zzlong'):
    """
        按每行固定个，打印列表中的值
    :param param: 要打印的列表 list
    :param num: 每行多少个值
    :param width: 每个值的宽度
    :param table_name: 表名字
    :param logger: 用什么打印 print / logger.info
    :return: None
    """
    f = print
    all_widths = num * width
    cut_line = "=" * all_widths
    # 表名字
    w = all_widths - len(table_name)
    if w > 1:
        f(cut_line[:w // 2] + table_name + cut_line[w // 2: w])
    else:
        f("=" + table_name + "=")

    # 直接打印
    temp = 0
    for i in range(len(param) // num):
        f(param[temp: temp + num])
        temp += num
    if param[temp:]:
        f(param[temp:])
    else:
        pass

    # 打印分割线
    f(cut_line + '\n')


if __name__ == '__main__':
    # a = {'test1': [11, 12, 13], 'test2': [21, 22, 23], 'test3': [31, 32, 33]}
    # print_pretty_table(a, ['my_test', 'values'], [10, 14], 'test_table', print)
    #
    # b = list(range(30))
    # print_pretty_list(b, 10, 10)
    print(WORK_DIR)
    print(LINKS_INFO)
    print(finish_time_file)
