import re
import os
import glob
import platform
import numpy as np
import pandas as pd


def decode_j_pre(j_paths):
    '''
    解析J文件里面的分钟降水 分钟单位0.1mm
    '''
    sys = platform.system()
    if sys == "Windows":
        types = ['*.txt']
    elif sys == "Linux":
        types = ['*.txt', '*.TXT']  # linux区分大小写

    total_path = []
    for files in types:
        total_path.extend(glob.glob(os.path.join(j_paths, files)))

    total_path.sort(key=lambda x: int(x.split('-')[-1].split('.')[0]))

    j_list = []
    for path in total_path:
        _, filename = os.path.split(path)  # 获得文件名
        # print(filename)
        
        try:
            # J文件解析
            if filename[0] == 'J':
                station_id = filename.split('-')[0][1:]
                date = filename.split('.')[0].split('-')[1]
                year = date[:4]
                month = date[4:]
                year_int = int(year)
                month_int = int(month)
                date = year + '-' + month + '-' + '01'
    
                num_lst = []
                for num, line in enumerate(open(path, 'r')):
                    line = line.strip('\n')
                    if line == 'R0=' or line == 'R=':
                        num_lst = []
                        break
    
                    elif line == 'R0':
                        start_num = num + 1
                        num_lst.append(start_num)
    
                    elif line == 'F0' or line == 'F=':
                        end_num = num - 1
                        num_lst.append(end_num)
    
                # 读取每行的数据
                # print(num_lst)
                if num_lst != []:
                    with open(path) as f:
                        all_data = f.readlines()[num_lst[0]:num_lst[1] + 1]
                        all_data = [data.strip('\n') for data in all_data]
    
                else:
                    if month_int in [1, 3, 5, 7, 8, 10, 12]:
                        day = 31
                    elif month_int in [4, 6, 9, 11]:
                        day = 30
                    else:
                        if (year_int % 4 == 0) and (year_int % 100 != 0) or (year_int % 400 == 0):
                            day = 29
                        else:
                            day = 28
    
                    all_data = ['.'] * (day - 1) + ['=']
    
                # 计数
                num_hours = 0
                data_lst = []
    
                for i, data in enumerate(all_data):
    
                    if data == '/,':
                        data = ','
                    elif data == '/.':
                        data = '.'
                    elif data == '/=':
                        data = '='
                    else:
                        data = data.replace('//', '00')
    
                    # 转换为数字
                    if data == '.' and i == 0:
                        num_hours += 24
                        arr = np.zeros((24, 60))
    
                    elif data == '.' and all_data[i - 1][-1] == '.':
                        num_hours += 24
                        arr = np.zeros((24, 60))
    
                    elif data == '.' and all_data[i - 1][-1] != '.':
                        num_hours += 1
                        arr = np.zeros((1, 60))
    
                    elif data == ',':
                        num_hours += 1
                        arr = np.zeros((1, 60))
    
                    elif len(data) > 1:
                        num_hours += 1
                        data = data[:-1]
                        len_zero = 120 - len(data)
                        data = data + '0' * len_zero
                        data = re.findall(".{2}", data)
                        data = [int(da) for da in data]
                        arr = np.array(data).reshape(1, -1)
    
                    elif data == '=' and all_data[i - 1][-1] == '.':
                        num_hours += 24
                        arr = np.zeros((24, 60))
    
                    elif data == '=' and all_data[i - 1][-1] != '.':
                        num_hours += 1
                        arr = np.zeros((1, 60))
    
                    data_lst.append(arr)
    
                rain_data = np.concatenate(data_lst, axis=0)
                rain_data = rain_data / 10
    
                date_range = pd.date_range(start=date, periods=num_hours, freq='H')
                rain_data = pd.DataFrame(rain_data, index=date_range, columns=[str(i) + 'min' for i in range(1, 61)])
                rain_data.insert(loc=0, column='station', value=station_id)  # 插入站号
                rain_data.insert(loc=1, column='year', value=rain_data.index.year)  # 插入年
                rain_data.insert(loc=2, column='month', value=rain_data.index.month)  # 插入月
                rain_data.insert(loc=3, column='day', value=rain_data.index.day)  # 插入日
                rain_data.insert(loc=4, column='hour', value=rain_data.index.hour)  # 插入小时
                j_list.append(rain_data)
        
        except:
            pass

    j_data = pd.concat(j_list, axis=0)
    j_data = j_data.sort_index()
    j_data['station'] = j_data['station'].map(int)

    return j_data


if __name__ == '__main__':
    j_paths = r'C:/Users/mjynj/Desktop/AAA/J'
    j_data = decode_j_pre(j_paths)
