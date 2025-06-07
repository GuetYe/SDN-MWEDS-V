'''
Author: Sun Shiquan email:786721684@qq.com
Date: 2025-01-01 09:32:51
LastEditTime: 2025-01-03 10:43:53
LastEditors: Sun Shiquan
Description: 

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
