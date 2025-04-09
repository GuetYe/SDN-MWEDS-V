# Copyright (C) 2014 Stratosphere Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Usage example

1. Run this application:
$ ryu-manager --verbose --observe-links ryu.app.ws_topology

2. Connect to this application by WebSocket (use your favorite client):
$ wscat -c ws://localhost:8080/v1.0/topology/ws

3. Join switches (use your favorite method):
$ sudo mn --controller=remote --topo linear,2

4. Topology change is notified:# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""



"""
用法示例

1. 运行此应用程序:
$ ryu-manager --verbose --observe-links ryu.app.ws_topology

2. 通过 WebSocket 连接到此应用程序（使用您喜欢的客户端）:
$ wscat -c ws://localhost:8080/v1.0/topology/ws

3. 连接交换机 (使用您喜欢的方法):
$ sudo mn --controller=remote --topo linear,2

4. 拓扑变化会被通知:
< {"params": [{"ports": [{"hw_addr": "56:c7:08:12:bb:36", "name": "s1-eth1", "port_no": "00000001", "dpid": "0000000000000001"}, {"hw_addr": "de:b9:49:24:74:3f", "name": "s1-eth2", "port_no": "00000002", "dpid": "0000000000000001"}], "dpid": "0000000000000001"}], "jsonrpc": "2.0", "method": "event_switch_enter", "id": 1}
> {"id": 1, "jsonrpc": "2.0", "result": ""}

< {"params": [{"ports": [{"hw_addr": "56:c7:08:12:bb:36", "name": "s1-eth1", "port_no": "00000001", "dpid": "0000000000000001"}, {"hw_addr": "de:b9:49:24:74:3f", "name": "s1-eth2", "port_no": "00000002", "dpid": "0000000000000001"}], "dpid": "0000000000000001"}], "jsonrpc": "2.0", "method": "event_switch_leave", "id": 2}
> {"id": 2, "jsonrpc": "2.0", "result": ""}

一个基于 WebSocket 的 SDN 拓扑通知应用程序。通过 WebSocket，它实时通知连接的客户端有关交换机、链路和主机事件的拓扑变化。处理拓扑变化的方法通过 WebSocket 向所有连接的客户端广播相应的消息
"""  # noqa




from socket import error as SocketError
from tinyrpc.exc import InvalidReplyError

# 从 ryu 库中导入必要的模块和类
from ryu.app.wsgi import (
    ControllerBase,
    WSGIApplication,
    websocket,
    WebSocketRPCClient
)
from ryu.base import app_manager
from ryu.topology import event, switches
from ryu.controller.handler import set_ev_cls

# WebSocketTopology 应用程序类
class WebSocketTopology(app_manager.RyuApp):
    _CONTEXTS = {
        'wsgi': WSGIApplication,
        'switches': switches.Switches,
    }

    # 初始化方法
    def __init__(self, *args, **kwargs):
        super(WebSocketTopology, self).__init__(*args, **kwargs)

        # 用于存储 WebSocket 连接的 RPC 客户端列表
        self.rpc_clients = []

        # 从参数中获取 WSGIApplication 实例
        wsgi = kwargs['wsgi']
        # 在 WSGIApplication 中注册 WebSocketTopologyController 控制器
        wsgi.register(WebSocketTopologyController, {'app': self})

    # 处理交换机进入事件
    @set_ev_cls(event.EventSwitchEnter)
    def _event_switch_enter_handler(self, ev):
        msg = ev.switch.to_dict()
        self._rpc_broadcall('event_switch_enter', msg)

    # 处理交换机离开事件
    @set_ev_cls(event.EventSwitchLeave)
    def _event_switch_leave_handler(self, ev):
        msg = ev.switch.to_dict()
        self._rpc_broadcall('event_switch_leave', msg)

    # 处理链路添加事件
    @set_ev_cls(event.EventLinkAdd)
    def _event_link_add_handler(self, ev):
        msg = ev.link.to_dict()
        self._rpc_broadcall('event_link_add', msg)

    # 处理链路删除事件
    @set_ev_cls(event.EventLinkDelete)
    def _event_link_delete_handler(self, ev):
        msg = ev.link.to_dict()
        self._rpc_broadcall('event_link_delete', msg)

    # 处理主机添加事件
    @set_ev_cls(event.EventHostAdd)
    def _event_host_add_handler(self, ev):
        msg = ev.host.to_dict()
        self._rpc_broadcall('event_host_add', msg)

    # 广播 RPC 消息给所有连接的客户端
    def _rpc_broadcall(self, func_name, msg):
        disconnected_clients = []       
        for rpc_client in self.rpc_clients:
            # 尝试使用每个 RPC 客户端发送消息
            rpc_server = rpc_client.get_proxy()
            try:
                getattr(rpc_server, func_name)(msg)
            except SocketError:
                # 如果发生连接错误，记录并添加到待删除列表
                self.logger.debug('WebSocket disconnected: %s', rpc_client.ws)
                disconnected_clients.append(rpc_client)
            except InvalidReplyError as e:
                self.logger.error(e)

        # 从客户端列表中移除断开连接的客户端
        for client in disconnected_clients:
            self.rpc_clients.remove(client)

# WebSocketTopologyController 控制器类
class WebSocketTopologyController(ControllerBase):

    def __init__(self, req, link, data, **config):
        super(WebSocketTopologyController, self).__init__(
            req, link, data, **config)
        self.app = data['app']

    # WebSocket 处理器，处理拓扑 WebSocket 连接
    @websocket('topology', '/v1.0/topology/ws')
    def _websocket_handler(self, ws):
        # 创建 WebSocketRPCClient 实例
        rpc_client = WebSocketRPCClient(ws)
        # 将客户端添加到应用程序的客户端列表
        self.app.rpc_clients.append(rpc_client)
        # 启动 WebSocketRPCClient 服务
        rpc_client.serve_forever()

