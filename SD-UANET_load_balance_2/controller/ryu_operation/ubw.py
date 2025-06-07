from time import sleep
import math
from scipy.optimize import least_squares

# 四个基站坐标 17教501室
A0 = [2, 0.3]
A1 = [6.6, 2]
A2 = [1, 5.0]
A3 = [6.6, 7.2]



x = []
y = []


def intersectionPoint(point1, point2, point3, r1, r2, r3):
    x1, y1 = point1
    x2, y2 = point2
    x3, y3 = point3

    def eq(g):
        x, y = g

        return (
            (x - x1) ** 2 + (y - y1) ** 2 - r1 ** 2,
            (x - x2) ** 2 + (y - y2) ** 2 - r2 ** 2,
            (x - x3) ** 2 + (y - y3) ** 2 - r3 ** 2)

    guess = (x1, y1 + r1)
    ans = least_squares(eq, guess, ftol=None, xtol=None)

    return ans


def recv(serial):
    while True:
        data = serial.read_all().decode()  # str
        if data == '':
            continue
        else:
            break
        sleep(0.02)
    return data


# def draw_round(r, a, b, ax):
#     theta = np.arange(0, 2 * np.pi, 0.01)
#     x = a + r * np.cos(theta)
#     y = b + r * np.sin(theta)

#     ax.plot(x, y)


def repair_data(data, number):
    if len(data[number]) < 8:
        data[number] = data[number] + data[number + 1]
        del data[number + 1]
    return data


# def draw(x, y):
#     plt.ion()
#     plt.plot(x, y)
#     plt.pause(0.01)


def get_coordinates(data0):
    # flag = False    # 标志位，判断数据是否有缺失
    # data0 = []

    # data = recv(serial)  # 读取一帧串口数据
    # print(data)
    # if 'mc' in data:
    #     while len(data0) < 10:
    #         data0.extend(data.split(' '))  # data0:存储有效的标签数据
    #         data = recv(serial)  # 读取一帧串口数据
    #     else:
    #         if '' in data0:
    #             data0.remove('')

    #     # 修复数据
    #     data0 = repair_data(data0, 2)
    #     data0 = repair_data(data0, 3)
    #     data0 = repair_data(data0, 4)
    #     data0 = repair_data(data0, 5)

    if data0[1] == '0f':

        # print("data0",data0)

        # 标签到四个基站的距离
        distance_A0 = int(data0[2], base=16) / 1000
        distance_A1 = int(data0[3], base=16) / 1000
        distance_A2 = int(data0[4], base=16) / 1000
        distance_A3 = int(data0[5], base=16) / 1000

        # distance = [distance_A0,distance_A1,distance_A2,distance_A3]

        ans1 = intersectionPoint(A0, A1, A2, distance_A0, distance_A1, distance_A2)
        ans2 = intersectionPoint(A0, A1, A3, distance_A0, distance_A1, distance_A3)
        ans3 = intersectionPoint(A0, A2, A3, distance_A0, distance_A2, distance_A3)
        ans4 = intersectionPoint(A1, A2, A3, distance_A1, distance_A2, distance_A3)

        ans = [round((ans1.x[0] + ans2.x[0] + ans3.x[0] + ans4.x[0]) / 4, 2),
                round((ans1.x[1] + ans2.x[1] + ans3.x[1] + ans4.x[1]) / 4, 2)]

        print("四基站定位", ans)
        # print(distance)

    elif data0[1] == '0e':
        # 标签到3个基站的距离
        distance_A1 = int(data0[2], base=16) / 1000
        distance_A2 = int(data0[3], base=16) / 1000
        distance_A3 = int(data0[4], base=16) / 1000

        # distance = [distance_A0,distance_A1,distance_A2,distance_A3]

        ans = intersectionPoint(A1, A2, A3, distance_A1, distance_A2, distance_A3)

        ans = [round(ans.x[0], 2), round(ans.x[1], 2)]

        print("三基站定位(A1,A2,A3):", ans)

    elif data0[1] == '0d':
        # 标签到3个基站的距离
        distance_A0 = int(data0[2], base=16) / 1000
        distance_A2 = int(data0[3], base=16) / 1000
        distance_A3 = int(data0[4], base=16) / 1000

        # distance = [distance_A0,distance_A1,distance_A2,distance_A3]

        ans = intersectionPoint(A0, A2, A3, distance_A0, distance_A2, distance_A3)

        ans = [round(ans.x[0], 2), round(ans.x[1], 2)]

        print("三基站定位(A0,A2,A3):", ans)

    elif data0[1] == '0b':
        # 标签到3个基站的距离
        distance_A0 = int(data0[2], base=16) / 1000
        distance_A1 = int(data0[3], base=16) / 1000
        distance_A3 = int(data0[4], base=16) / 1000

        # distance = [distance_A0,distance_A1,distance_A2,distance_A3]

        ans = intersectionPoint(A0, A1, A3, distance_A0, distance_A1, distance_A3)

        ans = [round(ans.x[0], 2), round(ans.x[1], 2)]

        print("三基站定位(A0,A1,A3):", ans)

    elif data0[1] == '07':
        # 标签到四个基站的距离
        distance_A0 = int(data0[2], base=16) / 1000
        distance_A1 = int(data0[3], base=16) / 1000
        distance_A2 = int(data0[4], base=16) / 1000

        ans = intersectionPoint(A0, A1, A2, distance_A0, distance_A1, distance_A2)

        ans = [round(ans.x[0], 2), round(ans.x[1], 2)]

        print("三基站定位(A0,A1,A2):", ans)

    else:
        return

    return ans



# if __name__ == "__main__":
#     # 打开串口
#     serial = serial.Serial('COM5', 57600, timeout=0.05)
#     with open('UWB.csv', 'w', newline='') as file:
#         # 将得到的file对象传递给csv.writer()方法进行处理，得到一个可写入对象
#         csv_writer = csv.writer(file)
#         # 生成一个白色图像用于停止绘制轨迹
#         # stop_img = np.ones((500, 500, 3), dtype='uint8')
#         # cv.imshow('stop_img', stop_img)
#         # plt.xlim(0, 8)
#         # plt.ylim(0, 7)
#         while True:
#             ans = get_coordinates(serial)
#             # if ans:
#             #     # 写入数据到UWB.csv 保存(x，y)坐标
#             #     csv_writer.writerow(ans)
#             #     x.append(ans[0])
#             #     y.append(ans[1])
#             #     draw(x, y)

#             # if cv.waitKey(1) & 0xFF == ord('q'):
#             #     break
#         cv.destroyAllWindows()



