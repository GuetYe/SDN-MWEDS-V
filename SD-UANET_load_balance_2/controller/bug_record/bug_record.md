<!--
 * @Author: 孙石泉 786721684@qq.com
 * @Date: 2024-01-23 22:50:55
 * @LastEditTime: 2024-03-06 10:59:45
 * @LastEditors: 孙石泉
 * @Description: ryu程序的bug记录
 * @FilePath: \SD-UANET_load_balance\SDN\bug_record\bug_record.md
-->


2024-1-25:
bug：传输文件时间久一点时samba连接中断，iperf3发送数据时间久一点时ryu的拓扑的link_table
解决：SDN交换机与终端连接的WIFI设置为不同的信道。所有SDN交换机都是同一个信道容易产生同频干扰。和客户端工程的传输终端bug是一个问题