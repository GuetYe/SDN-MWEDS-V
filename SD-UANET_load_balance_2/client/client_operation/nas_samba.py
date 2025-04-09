'''
Author: 孙石泉 786721684@qq.com
Date: 2024-01-21 10:21:59
LastEditTime: 2024-03-19 22:26:04
LastEditors: 孙石泉
Description: samba连接/上传/下载。树莓派的U盘的格式需为NTFS格式，不然无法写，只能读
FilePath: \SD-UANET_load_balance\client\client_operation\nas_samba.py
'''


import sys
import platform
import os
from smb.SMBConnection import SMBConnection

import time
import sys
sys.path.append('../')
from client_operation.log_module import logger

my_client_platform = platform.system()  # 读取客户端平台类型
if my_client_platform == 'Windows':  # Windows平台下加载模块的方法
    sys.path.append('../')
    import config.setting as setting
elif my_client_platform == 'Linux':  # Linux平台下加载模块的方法
    sys.path.append('../')
    import config.setting as setting


class Samba:
    def __init__(self, host, username, password) -> None:
        self.host = host
        self.username = username
        self.password = password
        self.my_name = ""
        self.remote_name = ""
        self.smb_port = 445  # smb协议默认端口445
        # 构造一个smb对象
        self.smb_client = SMBConnection(username=self.username, password=self.password,
                                        my_name=self.my_name, remote_name=self.remote_name)
        self.connect_state = False  # 是否成功连接SMB对象状态
        # NAS的远程文件信息(上传)
        self.last_file_info_upload = {}
        self.curr_file_info_upload = {}
        # NAS的远程文件信息(拉取)
        self.last_file_info_pull = {}
        self.curr_file_info_pull = {}

    def connect(self):
        """
        description: 连接samba服务器
        param {*} self-传入类本身属性
        return {*}
        """
        # 默认超时30s
        result = self.smb_client.connect(self.host, self.smb_port, timeout=30)
        if result:
            self.connect_state = True
            return True
        else:
            self.connect_state = False
            return False

    def close(self):
        """
        description: 断开连接
        param {*} self-传入类本身属性
        return {*}
        """
        result = self.smb_client.close()
        if result:
            self.connect_state = False
            return True
        else:
            return False

    def show_host_share_folder(self):
        """
        description: 列出本主机所有共享的目录
        param {*} self-传入类本身属性
        return {*}
        """
        if self.connect_state:
            for object in self.smb_client.listShares():
                logger.info(object.name)
            return True
        else:
            logger.info("请先连接")
            return False

    def show_path_content(self, folder='NAS_Share/', path='/'):
        """
        description: 列出本主机某共享目录(folder)下的某路径(path)下的所有文件
        param {*} self-传入类本身属性
        param {*} folder-共享文件夹
        param {*} path-需要展示内容的路径
        return {*}
        """
        if self.connect_state:
            file_object = self.smb_client.listPath(folder, path)
            for each_file in file_object:
                logger.info(each_file.filename)
            return True
        else:
            logger.info("<nas_samba.py>  The samba connection is not set up yet")
            self.connect()
            return False

    def upload_files(self, local_file_path, remote_file_path, share_folder=setting.DEFAULT_SHARE_FOLDER_NAME):
        '''
        description: 上传文件到远程samba服务器
        param {*} self
        param {*} local_file_path 本地文件的路径
        param {*} remote_file_path 指定文件上传在远程samba服务器的路径
        param {*} share_folder 指定要上传到的SMB共享文件夹的名称
        return {*}
        '''
        if self.connect_state:
            localFile = open(local_file_path, "rb")
            result = self.smb_client.storeFile(share_folder, remote_file_path, localFile)
            if not result:
                logger.info("<nas_samba.py>  Failed to upload files")
            localFile.close()
            self.smb_client.close()
        else:
            logger.info("<nas_samba.py>  The samba connection is not set up yet")
            return False

    def download_files(self, local_file_path, remote_file_path, share_folder=setting.DEFAULT_SHARE_FOLDER_NAME):
        '''
        description: 从samba服务器下载文件
        param {*} self
        param {*} local_file_path 本地文件的路径
        param {*} remote_file_path 远程服务器文件的路径和名称。
        param {*} share_folder 指定要下载的SMB共享文件夹的名称
        return {*}
        '''
        if self.connect_state:
            localFile = open(local_file_path, "wb")
            result = self.smb_client.retrieveFile(share_folder, remote_file_path, localFile)
            if not result:
                logger.info("<nas_samba.py>  Failed to download files")
            localFile.close()
            self.smb_client.close()

    def upload_folder(self, local_file_path, remote_file_path, share_folder=setting.DEFAULT_SHARE_FOLDER_NAME):
        '''
        description: 本机上传文件夹到远程samba服务器
        param {*} self
        param {*} local_file_path 本地文件夹
        param {*} remote_file_path 远程文件夹
        param {*} share_folder 服务器中的samba共享文件夹
        return {*}
        '''

        if self.connect_state:
            # os.walk：输出指定文件夹内所有的子文件夹的路径、子文件夹名称、子文件夹的文件
            for fpathe, dirs, fs in os.walk(local_file_path):
                for f in fs:
                    # fpp：子文件夹内f文件的对象
                    fpp = open(os.path.join(fpathe, f), 'rb')
                    # local_file_path替换为""  方便后面在服务器创建文件夹
                    relativePath = fpathe.replace(local_file_path, "")
                    try:
                        self.smb_client.createDirectory(share_folder,
                                                        os.path.join(remote_file_path, relativePath))  # 先创建文件夹
                    except:
                        pass
                    self.smb_client.storeFile(share_folder, os.path.join(remote_file_path, relativePath, f), fpp)
                    fpp.close()
            self.smb_client.close()
        else:
            logger.info("<nas_samba.py>   Failed to upload folder")
    
    

    def get_upload_speed(self, remote_path, part_file_name):
        '''
        description: 获取smaba传输中的上传速度
        param {*} self
        param {*} remote_path NAS的文件路径
        param {*} part_file_name 传输文件名字(包括后缀)
        return {*}
        '''

        if self.connect_state:  
            last_file_list = self.smb_client.listPath("NAS_Share", remote_path)
            for file_info in last_file_list:
                if file_info.isDirectory:
                    continue
                file_name = file_info.filename
                file_size = file_info.file_size
                self.last_file_info_upload[file_name] = file_size
                
            
            start_time = time.time()
            time.sleep(5)
            file_list = self.smb_client.listPath("NAS_Share", remote_path)

            for file_info in file_list:
                if file_info.isDirectory:
                    continue
                file_name = file_info.filename
                file_size = file_info.file_size
                self.curr_file_info_upload[file_name] = file_size
                # logger.info("<nas_samba.py>   file_name:%s,file_size:%d"% (file_name, file_size), end="")

            file_size = self.curr_file_info_upload[part_file_name] - self.last_file_info_upload[part_file_name]
            # logger.info("<nas_samba.py>  file_size:%d  transport_size:%d"% (self.last_file_info[part_file_name], file_size), end="")
            end_time = time.time()

            duration = end_time - start_time
            speed = file_size / (duration * 1024 * 1024)  # 单位: MB/s
            self.last_file_info_upload[part_file_name] = file_size
            logger.info("\r <nas_samba.py>   upload_speed:%.2f MB/s" % speed, end="", flush=True)
            return speed
        else:
            logger.info("<nas_samba.py>  The samba connection is not set up yet")
            return False


    def get_pull_speed(self, locate_path, part_file_name):
        '''
        description: 获取客户端拉取NAS的文件速度
        param {*} self
        param {*} locate_path  文件需存储在本地的路径
        param {*} part_file_name 传输的文件名字(包括文件后缀)
        return {*}
        '''


        if self.connect_state:  
 
            self.last_file_info_pull[part_file_name] = os.path.getsize(locate_path)
            start_time = time.time()
            time.sleep(5)

            self.curr_file_info_pull[part_file_name] = os.path.getsize(locate_path)
            
            file_size = self.curr_file_info_pull[part_file_name] - self.last_file_info_pull[part_file_name]
            end_time = time.time()

            duration = end_time - start_time
            speed = file_size / (duration * 1024 * 1024)  # 单位: MB/s
            self.last_file_info_pull[part_file_name] = file_size
            logger.info("\r <nas_samba.py>   upload_speed:%.2f MB/s" % speed, end="", flush=True)
            return speed
        else:
            logger.info("<nas_samba.py>  The samba connection is not set up yet")
            return False






if __name__ == "__main__":
    # host:远程服务器的IP
    host_1 = Samba(host="10.0.0.55", username="pi", password="123456")
    result = host_1.connect()
    if result:
        logger.info("连接成功")
    # # host_1.show_path_content(folder='NAS_Share', path='/')
    host_1.upload_files(local_file_path='F:\E\controller_files\My_Ryu_Project\Client_Project\config\setting.py',
                        remote_file_path='/setting.py')
    # # host_1.download_files(local_file_path='C://Users//Administrator//Desktop//picture.jpeg', remote_file_path='/picture.jpeg')

    # 上传文件夹
    # host_1.upload_folder(local_file_path='C://Users//Administrator//Desktop//Host_Project', remote_file_path='/Host_Project')
    host_1.close()