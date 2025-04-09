'''
Author: 孙石泉 786721684@qq.com
Date: 2023-12-29 17:17:03
LastEditTime: 2024-01-04 17:05:39
LastEditors: 孙石泉
Description: 北向接口
FilePath: \SD-UANET_load_balance\SDN\ryu_operation\controller_north_interface.py
'''


import urllib
import json
import urllib.request
 
def get_all_switches():
    '''
    description: 获取所有交换机
    return {*}
    '''
    url = "http://127.0.0.1:8080/v1.0/topology/switches"
    req = urllib.request.Request(url)
    res_data = urllib.request.urlopen(req)
    res = res_data.read()
    res = json.loads(res)
    return res
 
def get_all_links():
    '''
    description: 获取所有链路连接
    return {*}
    '''
    url = "http://127.0.0.1:8080/v1.0/topology/links"
    req = urllib.request.Request(url)
    res_data = urllib.request.urlopen(req)
    res = res_data.read()
    res = json.loads(res)
    return res

def get_all_hosts():
    '''
    description: 获取所有终端
    return {*}
    '''
    url = "http://127.0.0.1:8080/v1.0/topology/hosts"
    req = urllib.request.Request(url)
    res_data = urllib.request.urlopen(req)
    res = res_data.read()
    res = json.loads(res)
    return res

def get_switch(dpid):
    '''
    description: 获取某个交换机的信息
    param {*} dpid
    return {*}
    '''
    url = "http://127.0.0.1:8080/v1.0/topology/switches/" + "%016x" % dpid
    req = urllib.request.Request(url)
    res_data = urllib.request.urlopen(req)
    res = res_data.read()
    res = json.loads(res)
    return res
 
def get_host(dpid):
    '''
    description: 获取某个交换机的终端的信息
    param {*} dpid
    return {*}
    '''
    url = "http://127.0.0.1:8080/v1.0/topology/hosts/" + "%016x" % dpid
    req = urllib.request.Request(url)
    res_data = urllib.request.urlopen(req)
    res = res_data.read()
    res = json.loads(res)
    return res


def get_flow_entries(dpid):
    '''
    description: 获取某个交换机的含流表项
    param {*} dpid 交换机dpid好
    return {*}
    '''
    url = "http://127.0.0.1:8080/stats/flow/" + "%016x" % dpid
    req = urllib.request.Request(url)
    res_data = urllib.request.urlopen(req)
    res = res_data.read()
    res = json.loads(res)
    return res
 
def add_flow_entry(dpid,match, priority, actions):
    '''
    description: 向某个交换机添加流表项
    param {*} dpid 交换机dpid号
    param {*} match 匹配条件
    param {*} priority 优先级
    param {*} actions 动作
    return {*}
    '''
    url = "http://127.0.0.1:8080/stats/flowentry/add"
    post_data = "{'dpid':%016x,'match':%s,'priority':%s,'actions':%s}" % (dpid,str(match),priority,str(actions))
    req = urllib.request.Request(url, post_data)
    res = urllib.request.urlopen(req)
    return res.getcode()
 
def delete_flow_entry(dpid, match=None, priority=None, actions=None):
    '''
    description: 删除某个交换机的流表项
    param {*} dpid 交换机dpid号
    param {*} match 匹配条件
    param {*} priority 优先级
    param {*} actions 动作
    return {*}
    '''
    url = "http://127.0.0.1:8080/stats/flowentry/delete"
    post_data = "{'dpid':%016x" % dpid
    if match is not None:
        post_data += ",'match':%s" % str(match)
    if priority is not None:
        post_data += ",'priority':%s" % priority
    if actions is not None:
        post_data += ",'actions':%s" % str(actions)
    post_data += "}"
 
    req = urllib.request.request(url, post_data)
    res = urllib.request.urlopen(req)
    return res.getcode()




