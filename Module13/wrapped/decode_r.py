import re
import os
import glob
import numpy as np
import pandas as pd
from datetime import timedelta


def process_line(x, year, month, day):
    '''
    解析一行里面分段后的分钟数据
    '''
    # 2400变成0000
    if x.iloc[0, 1] == '2400':
        x.iloc[0, 1] = '0000'

    if x.iloc[0, 2] == '2400':
        x.iloc[0, 2] = '0000'

    # 开始时间处理
    start_hour = x[1].values[0][:2]
    start_min = x[1].values[0][2:]
    start_time = pd.to_datetime(year + '-' + month + '-' + day + '-' + start_hour + '-' + start_min, format='%Y-%m-%d-%H-%M')

    if int(start_hour) in [20, 21, 22, 23] and (int(x[1].values[0]) != 2000):  # 排除时间等于2000的情况(属于后一天了)
        start_time = start_time - timedelta(days=1)

    # 结束时间处理
    end_hour = x[2].values[0][:2]
    end_min = x[2].values[0][2:]
    end_time = pd.to_datetime(year + '-' + month + '-' + day + '-' + end_hour + '-' + end_min, format='%Y-%m-%d-%H-%M')

    # 如时间段:start--2040 end--2150 (前两位小时，后两位分钟)
    if int(x[1].values[0]) >= 2001 and int(x[2].values[0]) >= int(x[1].values[0]) and int(end_hour) in [20, 21, 22, 23]:
        end_time = end_time - timedelta(days=1)

    # 处理完毕后，生成datetimeindex
    date_range = pd.date_range(start_time, end_time, freq='t')
    duration = int((end_time - start_time).seconds / 60) + 1  # 分钟时间差
    ident = int(x.iloc[0, 0])  # 标识符

    if ident == 2 or ident == 3:  # 2无降水 3缺测
        pre_vals = np.zeros((duration, 1))
        data = pd.DataFrame(pre_vals, index=date_range)

    else:  # 0/5/6正常
        pre_vals = x.iloc[0, 3:].values.astype(int)
        data = pd.DataFrame(pre_vals, index=date_range)

    return data


# 循环test
# path = r'C:\Users\HT\Desktop\rain_project\data\R\52713\R01\R015271319642001.dat'
# r_data = pd.read_csv(path, header=None)
# tmp = []
# for i in range(r_data.shape[0]):
#     print(i)
#     pre_info = r_data.loc[i].values[0]
#     pre_info = pre_info.split(' ')
#     year = pre_info[0]
#     month = pre_info[1]
#     day = pre_info[2]

#     pre_info = pd.DataFrame(pre_info[5:],columns=['info'])
#     pre_info['flag'] = pre_info['info'].apply(lambda x: len(x)==1)
#     index = pre_info[pre_info['flag'] == True].index.tolist()

#     pre_parts = np.split(pre_info['info'], index)[1:]
#     pre_parts = [part.to_frame().reset_index(drop=True).T for part in pre_parts]

#     # 调用
#     pre_parts = [process_line(part,year,month,day) for part in pre_parts]
#     pre_day = pd.concat(pre_parts,axis=0)
#     assert len(pre_day)==1440,'缺少数据'
#     tmp.append(pre_day)

# tmp = pd.concat(tmp,axis=0)


def sample(x):
    '''
    pandas applyfunc
    sample每一行
    '''
    pre_info = x.values[0]
    pre_info = pre_info.split(' ')
    year = pre_info[0]
    month = pre_info[1]
    day = pre_info[2]

    # step1 对该行的字符串分段
    pre_info = pd.DataFrame(pre_info[5:], columns=['info'])
    pre_info['flag'] = pre_info['info'].apply(lambda x: len(x) == 1)
    index = pre_info[pre_info['flag'] == True].index.tolist()
    pre_parts = np.split(pre_info['info'], index)[1:]
    pre_parts = [part.to_frame().reset_index(drop=True).T for part in pre_parts]

    # step2 逐段统计
    pre_parts = [process_line(part, year, month, day) for part in pre_parts]
    pre_day = pd.concat(pre_parts, axis=0)

    return pre_day


def decode_r_pre(path):
    '''
    解析R01文件 原始分钟单位0.01mm
    '''
    station_id = path.split('.')[0][-13:-8]
    r_data = pd.read_csv(path, header=None)
    r_data = r_data.apply(sample, axis=1)  # 逐行apply
    r_data = r_data.tolist()
    r_data = pd.concat(r_data, axis=0)
    r_data.columns = ['pre']
    r_data['pre'] = r_data['pre'] / 100

    r_hour_idx = r_data.resample('1H').mean()[:-1].index
    r_data = r_data.values.reshape(-1, 60)
    r_data = pd.DataFrame(r_data, index=r_hour_idx, columns=[str(i) + 'min' for i in range(1, 61)])
    r_data.insert(loc=0, column='station', value=station_id)  # 插入站号
    r_data.insert(loc=1, column='year', value=r_data.index.year)  # 插入年
    r_data.insert(loc=2, column='month', value=r_data.index.month)  # 插入月
    r_data.insert(loc=3, column='day', value=r_data.index.day)  # 插入日
    r_data.insert(loc=4, column='hour', value=r_data.index.hour)  # 插入小时

    return r_data


if __name__ == '__main__':
    path = r'C:\Users\MJY\Desktop\qh_rain\data\R015286619542001.DAT'
    r_data = decode_r_pre(path)
