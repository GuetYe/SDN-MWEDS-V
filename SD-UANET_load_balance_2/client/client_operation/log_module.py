'''
Author: Sun Shiquan email:786721684@qq.com
Date: 2024-12-13 09:36:39
LastEditTime: 2024-12-26 15:08:42
LastEditors: Sun Shiquan
Description: 
FilePath: \SD-UANET_load_balance_2\client\client_operation\log_module.py
'''



# logger_module.py
import logging

# 创建logger
logger = logging.getLogger('SSQ')
logger.setLevel(logging.DEBUG)

# # 检查是否已经添加了StreamHandler
# if not any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers):
# 创建console handler并设置等级
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# 创建formatter   %(message)s
formatter = logging.Formatter('%(levelname)-8s - %(filename)s - %(funcName)s:%(message)s')

# 添加formatter到handler
ch.setFormatter(formatter)

# 添加handler到logger
logger.addHandler(ch)

    