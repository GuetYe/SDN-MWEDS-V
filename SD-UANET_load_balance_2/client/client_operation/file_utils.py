'''
Author: 孙石泉 786721684@qq.com
Date: 2024-01-21 10:19:43
LastEditTime: 2024-12-26 15:29:27
LastEditors: Sun Shiquan
Description: 文件的操作（获取路径、文件名、分割、合并）
FilePath: \SD-UANET_load_balance_2\client\client_operation\file_utils.py
'''



import os
import re

import sys
sys.path.append('../')
from client_operation.log_module import logger

# 构造获取文件路径及文件名的正则表达式


class File_Utils:
    def __init__(self) -> None:
        self.search_file_name_method = re.compile(r'(?P<path>.+?)(?P<file>[a-zA-Z0-9_]*\.[a-zA-Z]+.?)')

    @staticmethod
    def file_name(file_path):
        # ?P<path>：捕获组 .+?中的?：取消贪婪模式  ?P<file>：捕获组 
        search_method = re.compile(r'(?P<path>.+?)(?P<file>[a-zA-Z0-9_]*\.[a-zA-Z]+.?)')
        file_name_complete = search_method.search(file_path).group("file")  # 完整文件名(捕获组file的值)

        return file_name_complete

    @staticmethod
    def file_path(file_path):
        search_method = re.compile(r'(?P<path>.+?)(?P<file>[a-zA-Z0-9_]*\.[a-zA-Z]+.?)')
        path = search_method.search(file_path).group("path")  # 完整文件名(捕获组path的值)

        return path

    @staticmethod
    def file_size(file_path):
        file_size = os.path.getsize(file_path)

        return file_size

    def file_split_average(self, file_path, part_count):
        '''
        description: 把文件平均分成多份
        param {*} self
        param {*} file_path 文件的路径
        param {*} part_count 分割份数
        return {*}
        '''
        if part_count == 1:
            logger.info("The part_count is 1，no need to split file")
            return

        # 1.获取被分割的文件名
        path = self.file_path(file_path)  # 完整路径
        file_name_complete = self.file_name(file_path)  # 完整文件名
        
        file_name_part = file_name_complete.split('.')[0]  # 不含后缀的文件名
        file_name_suffix = file_name_complete.split('.')[1]  # 后缀

        # 2.读取需要分割的文件总大小
        file_size = self.file_size(file_path)

        # 3.计算分割后每份文件的大小(最后一份文件大小为pre_size+余数，其余为pre_size)
        remainder = file_size % part_count  # 计算余数
        pre_size = int(file_size / part_count)  # 前面每一份的大小
        last_size = pre_size + remainder  # 最后一份的大小

        # 4.建立分割信息，用于记录分割信息，并在合并文件时读取使用
        SplitInformation = '' + file_name_complete + '\n'  # 第一行记录完整文件名

        # 5.分割文件
        part_number = 1  # 文件序号
        with open(file_path, "rb") as split_file:
            for count in range(part_count):
                part_number = count + 1
                if count != part_count - 1:
                    part_content = split_file.read(pre_size)
                    # 分割后的分块文件名
                    part_file_name = file_name_part + '_' + str(part_number) + '.' + file_name_suffix
                    SplitInformation = SplitInformation + part_file_name + '\n'  # 记录分割文件名
                    part_file_complete_path = path + part_file_name

                    with open(part_file_complete_path, "wb") as part_file:
                        part_file.write(part_content)
                    part_file.close()
                else:
                    part_content = split_file.read(last_size)
                    # 分割后的最后一个分块的文件名
                    part_file_name = file_name_part + '_' + str(part_number) + '.' + file_name_suffix
                    SplitInformation = SplitInformation + part_file_name + '\n'  # 记录分割文件名
                    part_file_complete_path = path + part_file_name
                    with open(part_file_complete_path, "wb") as part_file:
                        part_file.write(part_content)
                    part_file.close()

            # 这里应该要向前缩进一格
            split_file.close()

        # 6.保存分割的信息到txt文件中  只写入最后1分的分割信息？
        SplitInformation_path = path + file_name_complete + '_' + 'Split_Information' + '.txt'
        with open(SplitInformation_path, 'w+') as sf:
            sf.write(SplitInformation)
        sf.close()

    def file_split(self, file_path, split_dict):
        '''
        description: 根据多属性决策得到的分割方案峰源文件
        param {*} self
        param {*} file_path 源文件路径
        param {*} split_dict 分割方法(host_ip, split_size)
        return {*}
        '''

        path = self.file_path(file_path)  # 不含文件名的路径
        file_name_complete = self.file_name(file_path)  # 完整文件名
        file_name_part = file_name_complete.split('.')[0]  # 不含后缀的文件名
        file_name_suffix = file_name_complete.split('.')[1]  # 后缀

        # 遍历每一个大小
        samba_transfer_info = {}  # samba传输文件所需信息
        with open(file_path, "rb") as split_file:  # 打开待分割文件
            for step, (host_ip, split_size) in enumerate(split_dict.items()):  # 依次遍历分割字典中的内容
                part_number = step + 1  # 文件编号
                split_content = split_file.read(split_size)  # 根据字典内容分割文件(不关闭文件，指针会停留在读取的位置)
                
                part_file_name = file_name_part + '_' + str(part_number) + '.' + file_name_suffix  # 构造保存的文件名
                part_file_complete_path = path + part_file_name  # 构造完整的保存路径及文件名
                with open(part_file_complete_path, "wb") as part_file:  # 打开文件
                    part_file.write(split_content)  # 写入内容
                part_file.close()  # 保存
                samba_transfer_info[host_ip] = part_file_complete_path  # 保存该主机IP及对应的文件名(列表的存储顺序是按照插入顺序长期存储的)
        split_file.close()  # 处理完记得关闭文件，释放内存
        return samba_transfer_info  # {'host_ip_1':file_name1, 'host_ip_2':file_name2, ...}

    def save_storage_info(self, local_file_path, save_info):
        '''
        description: 
        param {*} self
        param {*} local_file_path 源文件的路径
        param {*} save_info[host_ip] = remote_file_path(服务器端的文件名)
        return {*}
        '''
        path = self.file_path(local_file_path)  # 不含文件名的路径
        file_name_complete = self.file_name(local_file_path)  # 完整文件名

        save_info_path = path + file_name_complete + '_storage_info' + '.txt'  # 构造存储的txt文件路径
        with open(save_info_path, 'w+') as save_file:
            save_file.write(file_name_complete + '\n')  # 写入完整文件名（第1行）
            save_file.write(str(self.file_size(local_file_path)) + '\n')  # 写入文件总大小信息(第2行)
            save_file.write(str(save_info))  # 写入存储的信息（ip：服务器的分块文件名）save_info[host_ip] = remote_file_path
        save_file.close()
        return save_info_path

    def loading_storage_info(self, file_name_complete, storage_file_path):
        """
        # description: 读取存储信息文件
        # param {*} self-传入类自身属性
        # param {*} file_name_complete- 完整的源文件名
        # param {*} storage_file_path- 存储信息文件完整路径
        # param {*} save_info
        # return {*} 存储信息的字典
        """
        save_info = {}
        file_size = None
        with open(storage_file_path, 'r') as storage_file:
            for step, lines_data in enumerate(storage_file.readlines()):
                lines_data = lines_data.strip()  # 去除该行的换行符
                if step == 0:  # 检查第一行是否和需要拉取的文件名一致
                    if not (lines_data == file_name_complete):
                        storage_file.close()
                        return False
                elif step == 1:  # 读取文件总大小（第2行）
                    file_size = int(lines_data)
                else:
                    save_info = eval(lines_data)  # 第二行即为存储信息的字典，直接用eval函数转换成python的字典
            storage_file.close()
        return save_info, file_size

    def file_merge(self, save_file_path, merge_list, delete_flag=1):
        """
        # description: 合并文件
        # param {*} self-传入类本身属性
        # param {*} save_file_path-合并后保存的路径
        # param {*} merge_list-分块文件路径信息列表
        # param {*} delete_flag-合并后的分块文件是否删除，默认删除
        # return {*} 合并结果
        """
        with open(save_file_path, 'wb') as merge_file:
            for each_part_file_path in merge_list:
                with open(each_part_file_path, 'rb') as part_file:
                    content = part_file.read(-1)  # -1代表读取整个文件内容
                    merge_file.write(content)  # 写入到总文件中
                del content
                part_file.close()  # 读取完毕，关闭分块文件
                if delete_flag:
                    os.remove(each_part_file_path)
        merge_file.close()  # 写入完毕，关闭总文件

        return True


if __name__ == '__main__':
    e = File_Utils()
    a = {'10.0.0.201': 47230601, '10.0.0.203': 5152429, '10.0.0.205': 33490790}
    e.file_split(file_path='E:/code_guet/SD-UANET_load_balance/data_test/bandicam 2023-12-29 15-05.mp4', split_dict=a)
