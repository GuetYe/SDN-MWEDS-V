import serial  # 调用串口包
import math

HEAD = 0xAA  # 起始帧（帧头）

# 目标地址
D_ADDR = {
    "IMU": 0x60
}

# 功能码
ID = {
    "fuc": 0xE0
}

# 数据长度
LEN = {
    "fuc": 0x0B
}

# 平移位置信息
direction = {
    "forward": 0,
    "right": 90,
    "back": 180,
    "left": 270
}


# ser = serial.Serial(port, baud_rate, timeout=1, bytesize=8, parity='N', stopbits=1)   # 选择串口，并设置波特率


class NM_drone:

    def __init__(self, port, baud_rate):
        self.port = port  # 串口号
        self.baud_rate = baud_rate  # 波特率
        self.ser = serial.Serial(self.port, self.baud_rate, timeout=1, bytesize=8, parity='N', stopbits=1)
        if self.ser.is_open:
            print("port open success")
        else:
            print("port open failed")

    def hextostr(self, list_data):  # list_data为整数表示的列表
        hex_str = ''
        for item in list_data:
            temp = hex(item & 0xff)  # 先转换为字符串，例如100转换为'0x64'
            if len(temp) == 3:
                hex_str = hex_str + '0' + temp[2]  # 一个16进制数以两个字符表示，如0x06对应的字符串为'06'而不是'6';

            else:
                hex_str = hex_str + temp[2] + temp[3]
        # print(hex_str)
        return hex_str

    def listtohex(self, list_data):  # list_data为整数表示的列表
        '''
        数据处理：列表 -> hex
        :param list_data: 一帧数据
        :return:
        '''

        send_data = []
        for data in list_data:
            send_data.append(data & 0xff)
        send_data = bytearray(send_data)
        # print(send_data)
        return send_data

    def SC(self, data):
        '''
        计算和校验
        :param data: 数据
        :return: 和校验
        '''
        return sum(data)

    def AC(self, data):
        '''
        计算附加校验
        :param data: 数据
        :return: 附加校验
        '''
        sum_data = 0
        data2 = []
        for i in data:
            sum_data += i
            data2.append(sum_data)
        return sum(data2)

    def send_command(self, frame):
        '''
        往串口发送数据
        :param frame: 一帧数据
        '''
        SC_data = self.SC(frame)  # 和校验
        AC_data = self.AC(frame)  # 附加校验
        # 向原列表末尾添加新序列中的值  append是添加对象
        frame.extend([SC_data, AC_data])
        # print(frame)
        #  这行多余的？
        self.hextostr(frame)

        send_data = self.listtohex(frame)  # 列表-->hex

        self.ser.write(send_data)

    def unlock(self):
        '''
        解锁
        '''
        frame = [HEAD]  # 帧头
        frame.append(D_ADDR['IMU'])  # 目标地址
        frame.append(ID['fuc'])  # 功能码
        frame.append(LEN['fuc'])  # 数据长度
        data = [0x10, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]  # 数据内容
        frame.extend(data)
        self.send_command(frame)  # 往串口发送数据

    def lock(self):
        '''
        上锁
        '''
        frame = [HEAD]
        frame.append(D_ADDR['IMU'])
        frame.append(ID['fuc'])
        frame.append(LEN['fuc'])
        data = [0x10, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        frame.extend(data)
        self.send_command(frame)

    def up(self, altitude=10, speed=10):
        '''
        上升
        :param altitude: 上升高度 cm
        :param speed: 上升速度 cm/s
        :return:
        '''

        frame = [HEAD]
        frame.append(D_ADDR['IMU'])
        frame.append(ID['fuc'])
        frame.append(LEN['fuc'])
        if altitude >= 0 and altitude <= 10000:
            altitude_high = altitude >> 8  # 高度高八位数据 把低8位数据右移出去
            altitude_low = altitude & 0xff  # 高度低八位数据
        else:
            raise Exception("设置飞行高度超出范围，请检查！")  # 如果高度超出范围，报错

        if speed >= 10 and speed <= 300:
            speed_high = speed >> 8  # 速度高八位数据 把低8位数据右移出去
            speed_low = speed & 0xff  # 速度低八位数据
        else:
            raise Exception("设置飞行速度超出范围，请检查！")  # 如果速度超出范围，报错

        # 注意：涉及到自定义数据区使用小端模式，即低字节在前，高字节在后
        data = [0x10, 0x02, 0x01, altitude_low, altitude_high, speed_low, speed_high, 0x00, 0x00, 0x00, 0x00]
        frame.extend(data)
        self.send_command(frame)

    def down(self, altitude=10, speed=10):
        '''
        下降
        :param altitude: 下降高度 cm
        :param speed: 下降速度 cm/s
        :return:
        '''
        frame = [HEAD]
        frame.append(D_ADDR['IMU'])
        frame.append(ID['fuc'])
        frame.append(LEN['fuc'])
        if altitude >= 0 and altitude <= 10000:
            altitude_high = altitude >> 8
            altitude_low = altitude & 0xff
        else:
            raise Exception("设置飞行高度超出范围，请检查！")
        if speed >= 10 and speed <= 300:
            speed_high = speed >> 8
            speed_low = speed & 0xff
        else:
            raise Exception("设置飞行速度超出范围，请检查！")

        data = [0x10, 0x02, 0x02, altitude_low, altitude_high, speed_low, speed_high, 0x00, 0x00, 0x00, 0x00]
        frame.extend(data)
        self.send_command(frame)

    def forward(self, distance=10, speed=10):
        '''
        向前平移
        :param distance: 平移距离 cm
        :param speed: 平移速度 cm/s
        :return:
        '''
        frame = [HEAD]
        frame.append(D_ADDR['IMU'])
        frame.append(ID['fuc'])
        frame.append(LEN['fuc'])
        if distance >= 0 and distance <= 10000:
            distance_high = distance >> 8
            distance_low = distance & 0xff
        else:
            raise Exception("设置飞行距离超出范围，请检查！")
        if speed >= 10 and speed <= 300:
            speed_high = speed >> 8
            speed_low = speed & 0xff
        else:
            raise Exception("设置飞行速度超出范围，请检查！")

        direction_high = direction["forward"] >> 8
        direction_low = direction["forward"] & 0xff

        data = [0x10, 0x02, 0x03, distance_low, distance_high, speed_low, speed_high, direction_low, direction_high,
                0x00, 0x00]
        frame.extend(data)
        self.send_command(frame)

    def back(self, distance=10, speed=10):
        '''
           向后平移
           :param distance: 平移距离 cm
           :param speed: 平移速度 cm/s
           :return:
           '''
        frame = [HEAD]
        frame.append(D_ADDR['IMU'])
        frame.append(ID['fuc'])
        frame.append(LEN['fuc'])
        if distance >= 0 and distance <= 10000:
            distance_high = distance >> 8
            distance_low = distance & 0xff
        else:
            raise Exception("设置飞行距离超出范围，请检查！")
        if speed >= 10 and speed <= 300:
            speed_high = speed >> 8
            speed_low = speed & 0xff
        else:
            raise Exception("设置飞行速度超出范围，请检查！")

        direction_high = direction["back"] >> 8
        direction_low = direction["back"] & 0xff

        data = [0x10, 0x02, 0x03, distance_low, distance_high, speed_low, speed_high, direction_low, direction_high,
                0x00,
                0x00]
        frame.extend(data)
        self.send_command(frame)

    def left(self, distance=10, speed=10):
        '''
           向左平移
           :param distance: 平移距离 cm
           :param speed: 平移速度 cm/s
           :return:
           '''
        frame = [HEAD]
        frame.append(D_ADDR['IMU'])
        frame.append(ID['fuc'])
        frame.append(LEN['fuc'])
        if distance >= 0 and distance <= 10000:
            distance_high = distance >> 8
            distance_low = distance & 0xff
        else:
            raise Exception("设置飞行距离超出范围，请检查！")
        if speed >= 10 and speed <= 300:
            speed_high = speed >> 8
            speed_low = speed & 0xff
        else:
            raise Exception("设置飞行速度超出范围，请检查！")

        direction_high = direction["left"] >> 8
        direction_low = direction["left"] & 0xff

        data = [0x10, 0x02, 0x03, distance_low, distance_high, speed_low, speed_high, direction_low, direction_high,
                0x00,
                0x00]
        frame.extend(data)
        self.send_command(frame)

    def right(self, distance=10, speed=10):
        '''
           向右平移
           :param distance: 平移距离 cm
           :param speed: 平移速度 cm/s
           :return:
           '''
        frame = [HEAD]
        frame.append(D_ADDR['IMU'])
        frame.append(ID['fuc'])
        frame.append(LEN['fuc'])
        if distance >= 0 and distance <= 10000:
            distance_high = distance >> 8
            distance_low = distance & 0xff
        else:
            raise Exception("设置飞行距离超出范围，请检查！")
        if speed >= 10 and speed <= 300:
            speed_high = speed >> 8
            speed_low = speed & 0xff
        else:
            raise Exception("设置飞行速度超出范围，请检查！")

        direction_high = direction["right"] >> 8
        direction_low = direction["right"] & 0xff

        data = [0x10, 0x02, 0x03, distance_low, distance_high, speed_low, speed_high, direction_low, direction_high,
                0x00,
                0x00]
        frame.extend(data)
        self.send_command(frame)

    def translation(self, speed=10, angle=0, distance=10):
        '''
        以任意角度平移
        :param distance: 平移距离 cm
        :param speed: 平移速度 cm/s
        :param angle: 平移角度( 0-359度（当前机头为 0 参考，顺时针）)
        :return:
        '''

        frame = [HEAD]
        frame.append(D_ADDR['IMU'])
        frame.append(ID['fuc'])
        frame.append(LEN['fuc'])
        if distance >= 0 and distance <= 10000:
            distance_high = distance >> 8
            distance_low = distance & 0xff
        else:
            raise Exception("设置飞行距离超出范围，请检查！")
        if speed >= 10 and speed <= 300:
            speed_high = speed >> 8
            speed_low = speed & 0xff
        else:
            raise Exception("设置飞行速度超出范围，请检查！")

        direction_high = angle >> 8
        direction_low = angle & 0xff

        data = [0x10, 0x02, 0x03, distance_low, distance_high, speed_low, speed_high, direction_low, direction_high,
                0x00,
                0x00]
        frame.extend(data)
        self.send_command(frame)

    def left_rotate(self, angle=5, deg=5):
        '''
        向左偏转
        :param angle: 偏转角度 deg
        :param deg:偏转角速度 deg/s
        :return:
        '''
        frame = [HEAD]
        frame.append(D_ADDR['IMU'])
        frame.append(ID['fuc'])
        frame.append(LEN['fuc'])
        if angle >= 0 and angle <= 359:
            angle_high = angle >> 8
            angle_low = angle & 0xff
        else:
            raise Exception("设置角度超出范围，请检查！")
        if deg >= 5 and deg <= 90:
            deg_high = deg >> 8
            deg_low = deg & 0xff
        else:
            raise Exception("设置飞行角速度超出范围，请检查！")

        data = [0x10, 0x02, 0x07, angle_low, angle_high, deg_low, deg_high, 0x00, 0x00, 0x00, 0x00]
        frame.extend(data)
        self.send_command(frame)

    def right_rotate(self, angle=5, deg=5):
        '''
        向右偏转
        :param angle: 偏转角度 deg
        :param deg:偏转角速度 deg/s
        :return:
        '''
        frame = [HEAD]
        frame.append(D_ADDR['IMU'])
        frame.append(ID['fuc'])
        frame.append(LEN['fuc'])
        if angle >= 0 and angle <= 359:
            angle_high = angle >> 8
            angle_low = angle & 0xff
        else:
            raise Exception("设置角度超出范围，请检查！")
        if deg >= 5 and deg <= 90:
            deg_high = deg >> 8
            deg_low = deg & 0xff
        else:
            raise Exception("设置飞行角速度超出范围，请检查！")

        data = [0x10, 0x02, 0x08, angle_low, angle_high, deg_low, deg_high, 0x00, 0x00, 0x00, 0x00]
        frame.extend(data)
        self.send_command(frame)

    def takeoff(self, altitude=100):
        '''
        一键起飞
        :param altitude: 按设置高度起飞，1m为默认高度
        :return:
        '''
        frame = [HEAD]
        frame.append(D_ADDR['IMU'])
        frame.append(ID['fuc'])
        frame.append(LEN['fuc'])
        if altitude >= 0 and altitude <= 500:
            altitude_high = altitude >> 8
            altitude_low = altitude & 0xff
        else:
            raise Exception("设置飞行高度超出范围，请检查！")

        data = [0x10, 0x00, 0x05, altitude_low, altitude_high, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        frame.extend(data)
        self.send_command(frame)

    def land(self):
        '''
        一键降落
        :return:
        '''
        frame = [HEAD]
        frame.append(D_ADDR['IMU'])
        frame.append(ID['fuc'])
        frame.append(LEN['fuc'])
        data = [0x10, 0x00, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        frame.extend(data)
        self.send_command(frame)

    def mode_select(self, mode=3):
        '''
        模式选择
        :param mode: 0:姿态;1:姿态+定高;2:定点;3:程控
        :return:
        '''
        frame = [HEAD]
        frame.append(D_ADDR['IMU'])
        frame.append(ID['fuc'])
        frame.append(LEN['fuc'])
        data = [0x01, 0x01, 0x01, mode, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        frame.extend(data)
        self.send_command(frame)

    def rotate(self, deg, angle=5):
        if deg < 5 and deg > -5:
            return
        elif deg >= 5:
            self.right_rotate(angle, deg)
        else:
            self.left_rotate(abs(angle), abs(deg))

    def forward_back(self, speed, distence=10):
        if speed < 10 and speed > -10:
            return
        if speed >= 0:
            self.forward(distence, speed)
        else:
            self.back(abs(distence), abs(speed))

    def up_down(self, speed, altitude=10):
        if speed < 10 and speed > -10:
            return
        if speed >= 0:
            self.forward(altitude, speed)
        else:
            self.back(abs(altitude), abs(speed))

    def left_right(self, speed, distence=10):
        if speed < 10 and speed > -10:
            return
        if speed >= 0:
            self.right(distence, speed)
        else:
            self.left(abs(distence), abs(speed))

    def hover(self):
        '''
        悬停
        '''
        frame = [HEAD]  # 帧头
        frame.append(D_ADDR['IMU'])  # 目标地址
        frame.append(ID['fuc'])  # 功能码
        frame.append(LEN['fuc'])  # 数据长度
        data = [0x10, 0x00, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]  # 数据内容
        frame.extend(data)
        self.send_command(frame)  # 往串口发送数据



    def send_control(self, lr, fb, ud, deg):
        if ud != 0:
            self.up_down(ud)
        if deg != 0:
            self.rotate(deg)

        if fb == 0:
            if lr == 0:
                self.hover()
            else:
                self.left_right(lr)
        # fb不等于0情况
        else:
            # 总速度
            speed = int(math.sqrt((lr * lr) + (fb * fb)))
            # 角度：角度制 0-359度（当前机头为 0 参考，顺时针）
            angle = int(math.atan(abs(lr) / abs(fb)) * 57.29577)
            # 向右飞
            if lr >= 0:
                # 向前飞
                if fb >= 0:
                    angle = angle
                # 向后飞
                else:
                    angle = 180 - angle
            else:
                if fb >= 0:
                    angle = 360 - angle
                else:
                    angle = 180 + angle

            self.translation(speed=speed, angle=angle)
    

    def move_to_target(self, position, target_position):
        """
        控制SDN交换机移动到目标位置
        """

        # 计算当前位置与目标位置之间的误差
        target_x, target_y = target_position
        current_x, current_y = position

        # 计算误差距离
        distance = math.sqrt((target_x - current_x) ** 2 + (target_y - current_y) ** 2)

        if distance < 0.5:  # 如果误差小于0.5米，认为已经到达目标
            print("Target reached.")
            return

        # 计算移动方向
        angle = math.degrees(math.atan2(target_y - current_y, target_x - current_x))
        speed = int(distance * 10)  # 根据误差调整速度，这里简单地按距离成比例调整速度
        # 计算LR和FB方向上的速度分量
        lr = speed * math.cos(math.radians(angle))
        fb = speed * math.sin(math.radians(angle))
        deg = 0  # 不涉及角度变化时，deg可以为0
        self.send_control_command(lr, fb, deg)
        # 控制无人机的移动
        self.send_control(lr, fb, deg)


