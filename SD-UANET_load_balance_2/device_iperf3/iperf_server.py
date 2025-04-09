'''
Author: 孙石泉 786721684@qq.com
Date: 2023-07-20 20:49:58
LastEditTime: 2024-05-09 20:54:57
LastEditors: 孙石泉
Description: 
FilePath: \SD-UANET_load_balance-24-4-19\device_iperf3\iperf_server.py
'''


import subprocess


def run_iperf(command):
    '''
    command:iperf命令
    '''
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        output, error = process.communicate()
        return output.decode(), error.decode()
    except Exception as e:
        return None, str(e)


def start_iperf_server(port):
    iperf_command = f"iperf3 -s -p {port}"
    return run_iperf(iperf_command)


def main():
    server_port = "5201"  # 假设服务器监听端口为5201

    print(f"Starting iperf3 server on port {server_port}...")
    output, error = start_iperf_server(server_port)

    if error:
        print(f"Error: {error}")
    else:
        print("iperf3 server has started and is ready to receive data.")
        print("Server output:")
        print(output)


if __name__ == "__main__":
    main()
