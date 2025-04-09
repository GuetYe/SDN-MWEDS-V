from time import sleep
import math

# 四个基站坐标 17教501室
A0 = [0, 0]
A1 = [0, 7.2]
A2 = [6.6, 7.2]
A3 = [5.1, 0]
x = []
y = []


# 手动实现最小二乘法
def least_squares_manual(A, b):
    """
    使用最小二乘法公式求解 Ax = b
    A: 设计矩阵
    b: 目标向量
    返回：解向量 x
    """
    # 计算 A 的转置 A^T
    A_T = list(zip(*A))
    
    # 计算 A^T * A
    ATA = [[sum(A_T[i][k] * A[k][j] for k in range(len(A))) for j in range(len(A[0]))] for i in range(len(A_T))]
    
    # 计算 A^T * b
    ATb = [sum(A_T[i][j] * b[j] for j in range(len(b))) for i in range(len(A_T))]
    
    # 计算 (A^T * A)^-1
    ATA_inv = invert_matrix(ATA)
    
    # 计算 x = (A^T * A)^-1 * A^T * b
    x = [sum(ATA_inv[i][j] * ATb[j] for j in range(len(ATb))) for i in range(len(ATA_inv))]
    return x

def invert_matrix(matrix):
    """
    计算矩阵的逆，使用高斯消元法
    """
    n = len(matrix)
    # 创建增广矩阵
    augmented_matrix = [row[:] + [1 if i == j else 0 for j in range(n)] for i, row in enumerate(matrix)]
    
    # 高斯消元
    for i in range(n):
        # 选主元并交换
        if augmented_matrix[i][i] == 0:
            for j in range(i + 1, n):
                if augmented_matrix[j][i] != 0:
                    augmented_matrix[i], augmented_matrix[j] = augmented_matrix[j], augmented_matrix[i]
                    break
        
        # 消去下三角
        for j in range(i + 1, n):
            ratio = augmented_matrix[j][i] / augmented_matrix[i][i]
            for k in range(i, 2 * n):
                augmented_matrix[j][k] -= ratio * augmented_matrix[i][k]
        
    # 回代求解
    for i in range(n - 1, -1, -1):
        for j in range(i + 1, n):
            augmented_matrix[i][n + j] -= augmented_matrix[i][j] * augmented_matrix[i][n + j]
        augmented_matrix[i][n + i] /= augmented_matrix[i][i]

    # 提取逆矩阵
    inv_matrix = [row[n:] for row in augmented_matrix]
    return inv_matrix

def intersectionPoint(point1, point2, point3, r1, r2, r3):
    x1, y1 = point1
    x2, y2 = point2
    x3, y3 = point3

    # 构造最小二乘法的设计矩阵 A 和目标向量 b
    A = [
        [2 * (x1 - x2), 2 * (y1 - y2)],
        [2 * (x2 - x3), 2 * (y2 - y3)],
        [2 * (x3 - x1), 2 * (y3 - y1)]
    ]
    
    b = [
        (r1**2 - x1**2 - y1**2) + (x2**2 + y2**2 - r2**2),
        (r2**2 - x2**2 - y2**2) + (x3**2 + y3**2 - r3**2),
        (r3**2 - x3**2 - y3**2) + (x1**2 + y1**2 - r1**2)
    ]

    # 计算最小二乘法的解
    solution = least_squares_manual(A, b)
    return solution




def recv(serial):
    while True:

        data = serial.read_all().decode()  # str
        sleep(1) #接收UWB串口数据时延迟1s
        if data == '':
            continue
        else:
            break
        sleep(0.02)
    return data



def repair_data(data, number):
    if len(data[number]) < 8:
        data[number] = data[number] + data[number + 1]
        del data[number + 1]
    return data



def get_coordinates(serial):
    # flag = False    # 标志位，判断数据是否有缺失
    data0 = []

    data = recv(serial)  # 读取一帧串口数据
    # print(data)
    if 'mc' in data:
        while len(data0) < 10:
            data0.extend(data.split(' '))  # data0:存储有效的标签数据
            data = recv(serial)  # 读取一帧串口数据
        else:
            if '' in data0:
                data0.remove('')

        # 修复数据
        data0 = repair_data(data0, 2)
        data0 = repair_data(data0, 3)
        data0 = repair_data(data0, 4)
        data0 = repair_data(data0, 5)

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



