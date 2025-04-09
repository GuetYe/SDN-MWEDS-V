'''
Author: 孙石泉 786721684@qq.com
Date: 2024-01-07 16:30:38
LastEditTime: 2024-01-07 21:21:43
LastEditors: 孙石泉
Description: 1.gui_topology.py调用了ofctl_rest.py和rest_topology.py，main.sh中不用再运行了，否则会报错
             2.电脑一定要联网，web页面才有图像
FilePath: \SD-UANET_load_balance\SDN\ryu_operation\gui_topology.py
'''
# 版权所有 (C) 2014 日本电报电话公司。
#
# 根据 Apache 许可证，版本 2.0 (the "License") 授权;
# 除非符合许可证，否则不得使用此文件。
# 您可以在以下网址获取许可证副本
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# 除非适用法律要求或书面同意，否则软件
# 根据许可证分发的基础上是“按原样提供”的，
# 无任何明示或暗示的保证或条件。
# 有关特定语言的权限，请参阅许可证。
#
# 示例用法
#
# 1. 连接交换机 (使用您喜欢的方法):
# $ sudo mn --controller remote --topo tree,depth=3
#
# 2. 运行此应用程序:
# $ PYTHONPATH=. ./bin/ryu run \
#     --observe-links ryu/app/gui_topology/gui_topology.py
#
# 3. 通过您的Web浏览器访问 http://<ryu主机的IP地址>:8080。
#

import os

# 从 webob 库中导入 DirectoryApp 类，用于提供静态文件服务
from webob.static import DirectoryApp

# 从 ryu 库中导入 ControllerBase、WSGIApplication、route 类和 app_manager 模块
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from ryu.base import app_manager

# 获取当前文件所在目录的路径
PATH = os.path.dirname(__file__)

# 提供静态文件服务的应用程序类
class GUIServerApp(app_manager.RyuApp):
    _CONTEXTS = {
        'wsgi': WSGIApplication,
    }

    # 初始化方法
    def __init__(self, *args, **kwargs):
        super(GUIServerApp, self).__init__(*args, **kwargs)

        # 从参数中获取 WSGIApplication 实例
        wsgi = kwargs['wsgi']
        # 在 WSGIApplication 中注册 GUIServerController 控制器
        wsgi.register(GUIServerController)

# 控制器类，处理静态文件服务请求
class GUIServerController(ControllerBase):
    # 初始化方法
    def __init__(self, req, link, data, **config):
        super(GUIServerController, self).__init__(req, link, data, **config)
        # 构造静态文件目录的路径
        path = "%s/html/" % PATH
        # 创建 DirectoryApp 实例，用于处理静态文件请求
        self.static_app = DirectoryApp(path)

    # 处理静态文件请求的路由方法
    @route('topology', '/{filename:[^/]*}')
    def static_handler(self, req, **kwargs):
        # 如果请求中包含文件名，将文件名设置为路径信息
        if kwargs['filename']:
            req.path_info = kwargs['filename']
        # 返回由静态文件处理器处理的响应
        return self.static_app(req)

# 以下行声明依赖于其他 Ryu 应用程序
app_manager.require_app('ryu.app.rest_topology')
app_manager.require_app('ryu.app.ws_topology')
app_manager.require_app('ryu.app.ofctl_rest')
