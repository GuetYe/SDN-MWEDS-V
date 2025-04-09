'''
Author: 孙石泉 786721684@qq.com
Date: 2024-01-21 10:24:21
LastEditTime: 2025-03-01 15:17:12
LastEditors: Sun Shiquan
Description: 客户端终端运行的py文件（上传/下载功能）
注意：
1.终端接收控制器发过来的文件分割方案功能需要安装winpcap(已经不在维护)或npcap的软件包


FilePath: \SD-UANET_load_balance_2\client\run\main.py
'''


import sys
import os
import time
import platform
import threading



sys.path.append('../')
from client_operation.client_request import ClientRequest
from client_operation.receive_result import ReceivePacket
from client_operation.file_utils import File_Utils
from client_operation.nas_samba import Samba
import config.setting as setting
from client_operation.log_module import logger
import time


my_client_platform = platform.system()  # 读取客户端平台类型



class ThreadUploadFile (threading.Thread):   #继承父类threading.Thread
    def __init__(self, threadID, host_ip, local_file_path):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.host_ip = host_ip
        self.local_file_path = local_file_path

    def run(self):                   #把要执行的代码写到run函数里面 线程在创建后会直接运行run函数 
        # 为每一个服务器实例化一个samba类
        host_smb = Samba(host=self.host_ip, username=setting.DEFAULT_USERNAME, password=setting.DEFAULT_PASSWORD)
        result = host_smb.connect()  # 尝试连接服务器
        part_file_name = file_utils.file_name(self.local_file_path)  # 截取完整文件名
        if result:
            logger.info("Connecting to the client %s successfully, uploading files %s ..." % (host_ip, part_file_name))
        # 尝试建立远程主机的保存文件夹
        # save_remote_path_complete已经包含了save_remote_path，还要 os.path.join？
        try:
            host_smb.smb_client.createDirectory(setting.DEFAULT_SHARE_FOLDER_NAME, \
                                                os.path.join(save_remote_path, save_remote_path_complete))
        except Exception as e:
            logger.info("%s smaba createDirectory fail" % self.host_ip)
            pass
        # 实际值（服务器）：save_remote_path + file_name_part + '_part/'文件名
        remote_file_path = save_remote_path_complete + part_file_name

        # 原本：remote_file_path=remote_file_path
        logger.info("uploading files to %s" % self.host_ip)
        host_smb.upload_files(local_file_path=self.local_file_path, remote_file_path=remote_file_path)

        logger.info("(%s-%s) has been uploaded successfully！" % (self.host_ip, self.local_file_path))
        host_smb.close()  # 上传完毕记得断开连接
        save_info[host_ip] = remote_file_path  # 存储信息字典，[ip]:服务器端的分块文件名

    def stop(self):
        host_smb.connect_state == False



class ThreadPullSpeed (threading.Thread):   #继承父类threading.Thread
    def __init__(self, threadID, host_ip, locate_path, part_file_name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.host_ip = host_ip
        self.locate_path = locate_path
        self.part_file_name = part_file_name
    def run(self):                   #把要执行的代码写到run函数里面 线程在创建后会直接运行run函数 
        host_smb = Samba(host=self.host_ip, username=setting.DEFAULT_USERNAME, password=setting.DEFAULT_PASSWORD)
        result = host_smb.connect()  # 尝试连接服务器
        if result:
            while host_smb.connect_state:
                host_smb.get_pull_speed(self.remote_path, self.part_file_name)
            logger.info("Thread {} end".format(self.threadID))



if __name__ == '__main__':

    # 获取当前时间
    now_time = time.strftime("%Y-%m-%d %H:%M:%S")
    with open('../result/result_6 points_2g_and_5g.txt', 'a+', encoding='utf-8') as result_file:
        result_file.write(now_time)
        result_file.write("  5G-mesh网络5G-功率10db-test_1000MB.zip")
        result_file.write(":\n")
     # 实验次数
    for number in range(setting.experiment_number):
        ################################配置################################
        # 需要存储 或 拉取文件保存的路径，及运行模式(存储或者拉取文件)
        file_path = 'E:/test_1000MB.zip'
        save_remote_path = '/'  # 需要存储的远程主机根路径
        mode = 1  # 1 = 存储   2 = 拉取
        merge_delete_flag = 1  # 拉取文件后是否删除分块文件 1=删除  0=不删除
        ################################配置################################

        # 判断是Linux系统还是windows系统，windows
        logger.info("The client platform is:%s" % my_client_platform)

        # ！windows平台自行输入IP地址！，Linux平台自动识别
        host_ip = ''
        if my_client_platform == 'Windows':
            host_ip = ClientRequest.get_wlan_ip_windows()
            # host_ip = "10.0.0.213"
        elif my_client_platform == 'Linux':
            host_ip = ClientRequest.get_host_IP_linux()
        else:
            logger.info("The client platform is another platform")


        file_utils = File_Utils()  # 实例化一个文件处理工具类
        program_start_time = time.time()  # 记录程序开始运行时间
        # -----------------------执行存储-----------------------
        if mode == 1:
            logger.info("Select the upload file function my_host_ip is %s." % (host_ip))
            storage_request = ClientRequest(host_ip)  # 构造请求实例

            storage_request.request_save(file_path)  # 发送请求至控制器
            logger.info("Request to upload file")

            logger.info("Listening for split result of the controller, pleace wait %s s." % setting.SNIFF_TIMEOUT)
            receive = ReceivePacket()  # 实例化一个数据包接收类
            receive.catch_pack()  # 监听主机收到的数据包(仅监听arp数据包)

            if not receive.receive_dict:  # 检查是否接收到控制器的决策结果
                logger.info("Unable to get split result from the controller")
                exit()
            else:
                logger.info("The split result was successfully obtained")

            # samba_transfer_info：{'host_ip_1':file_name1, 'host_ip_2':file_name2, ...}
            samba_transfer_info = file_utils.file_split(file_path=file_path, split_dict=receive.receive_dict)  # 根据决策结果分割文件
            file_split_info = [file_utils.file_name(file_name) for file_name in samba_transfer_info.values()]  # 截取分割后的文件名
            file_save_host_info = [host_ip for host_ip in samba_transfer_info.keys()]
            logger.info("The split result is: %s" % file_split_info)
            logger.info("The client corresponding to the split result is: %s" % file_save_host_info)

            file_name_complete = file_utils.file_name(file_path)  # 截取完整文件名
            file_name_part = file_name_complete.split('.')[0]  # 截取不含后缀的文件名
            # 服务器存储位置的路径
            save_remote_path_complete = save_remote_path + file_name_part + '_part/'  # 构造存储远程的路径(xxx_part/xxx_1.xxx)不含文件名
            save_info = {}  # 保存信息，远程取文件的时候要用
            threads = []  # 用于存储线程的列表
            for step, (host_ip, local_file_path) in enumerate(samba_transfer_info.items()):
                thread = ThreadUploadFile(step + 1, host_ip, local_file_path)
                threads.append(thread)  # 将线程对象添加到列表中
                # 启动线程
                thread.start()
                # 必须延迟一点时间，不然samba连接的服务器会是同一个(都是最后一个)
                time.sleep(5)
                
            # 等待每个线程结束
            for each_thread in threads:
                each_thread.join()
            
            # 将存储信息保存到txt文件中，用于下次取文件的依赖
            save_info_path = file_utils.save_storage_info(file_path, save_info)
            program_run_time = time.time() - program_start_time
            logger.info('The distributed storage information has been saved to: %s' % save_info_path)
            m, s = divmod(program_run_time, 60)
            h, m = divmod(m, 60)
            logger.info('The time for uploading files is: %02d:%02d:%02d \n' % (h, m, s))

            with open('../result/result_6 points_2g_and_5g.txt', 'a+', encoding='utf-8') as result_file:
                result_file.write(str(int(h)))
                result_file.write(":")
                result_file.write(str(int(m)))
                result_file.write(":")
                result_file.write(str(int(s)))
                result_file.write("\n")




        # -----------------------执行拉取-----------------------
        elif mode == 2:
            logger.info("Select the pull file function")
            path = file_utils.file_path(file_path)
            file_name_complete = file_utils.file_name(file_path)  # 取完整文件名
            storage_info_file_path = path + file_name_complete + '_storage_info' + '.txt'  # 构造存储的txt文件路径

            # 检查存储文件信息的TXT文件是否存在
            if not os.path.exists(storage_info_file_path):
                logger.info('The index file %s does not exit' % storage_info_file_path)
            else:
                logger.info('The index file was read successfully')

            # 读取存储文件信息
            save_info, object_file_size = file_utils.loading_storage_info(file_name_complete, storage_info_file_path)
            logger.info("filename：%s , filesize: %s byte" % (file_name_complete, object_file_size))
            if not save_info:
                logger.info('The index file was incorrectly read')

            # 遍历存储信息，下载各个文件到file_path中
            download_file_size_cumulte = 0  # 记录下的文件总大小
            merge_list = []  # 保存下载的分块文件的路径
            for step, (host_ip, remote_path) in enumerate(save_info.items()):
                # 分别构造samba主机实例
                host_smb = Samba(host=host_ip, username=setting.DEFAULT_USERNAME, password=setting.DEFAULT_PASSWORD)
                result = host_smb.connect()  # 尝试连接主机
                part_file_name = file_utils.file_name(remote_path)  # 截取完整文件名
                local_file_path = path + part_file_name  # 下载文件保存的完整路径
                merge_list.append(local_file_path)  # 保存该分块文件路径，方便后续合并
                if result:
                    logger.info("\nConnecting to the server  %s successfully,pulling files %s ..." % (host_ip, part_file_name))

                # 把分块文件下载到本地
                thread_pull_speed = ThreadPullSpeed(step, local_file_path, part_file_name)
                thread_pull_speed.start()

                host_smb.download_files(local_file_path=local_file_path, remote_file_path=remote_path)
                logger.info("The files has been pulled successfully！")
                download_file_size_cumulte += int(file_utils.file_size(local_file_path))  # 计算下载的文件累计总大小
                thread_pull_speed.join()

                host_smb.close()  # 下载完毕记得断开连接

            # 检查下载的文件大小是否和存储时记录的文件大小一致
            if download_file_size_cumulte != object_file_size:
                logger.info('File size check error')
            # 合并文件
            result = file_utils.file_merge(file_path, merge_list, delete_flag=merge_delete_flag)
            if result:
                logger.info('The files are successfully merged, the save path is: %s \n' % file_path)
            program_run_time = time.time() - program_start_time  # 计算运行时间
            m, s = divmod(program_run_time, 60)
            h, m = divmod(m, 60)
            logger.info('The time for pulling files is: %02d:%02d:%02d \n' % (h, m, s))

            with open('../result/result_6 points_5g.txt', 'a+', encoding='utf-8') as result_file:
                result_file.write(str(int(h)))
                result_file.write(":")
                result_file.write(str(int(m)))
                result_file.write(":")
                result_file.write(str(int(s)))
                result_file.write("\n")
