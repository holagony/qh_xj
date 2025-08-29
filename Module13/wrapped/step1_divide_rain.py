import os
import pickle
import copy
import numpy as np
import pandas as pd
from Module13.wrapped.decode_j import decode_j_pre
from Module13.wrapped.decode_r import decode_r_pre
from Utils.ordered_easydict import OrderedEasyDict as edict


def get_year_data(df, num_year):
    '''
    提取每一年的数据，变成df
    '''
    year_df = df[df['year'] == num_year]
    year_df = year_df.set_index(['station', 'year', 'month', 'day', 'hour']).stack().reset_index()
    year_df.rename(columns={'level_5': 'minute', 0: 'pre'}, inplace=True)
    year_df['minute'] = year_df['minute'].apply(lambda x: int(x[:-3]) - 1)
    year_df = year_df[['station', 'year', 'month', 'day', 'hour', 'minute', 'pre']]
    year_df['time'] = year_df['year'].map(str) + '-' + year_df['month'].map(str) + '-' + year_df['day'].map(str) + '-' + year_df['hour'].map(str) + '-' + year_df['minute'].map(str)
    year_df['time'] = pd.to_datetime(year_df['time'], format='%Y-%m-%d-%H-%M')

    return year_df


def divide_rain(year_df, interval):
    '''
    对每一年的数据进行划分场雨
    '''
    data_noZero = year_df[year_df['pre'] != 0]
    data_noZero = data_noZero.dropna()

    if len(data_noZero) == 0:
        rain_list = []

    else:
        timeStamp = data_noZero.index
        timeNode = [timeStamp[0]]

        rain_idx = []
        for i in range(1, len(timeStamp)):
            diff = timeStamp[i] - timeStamp[i - 1]
            if diff >= interval:
                rain_idx.append([timeNode[-1], timeStamp[i - 1]])
                timeNode.append(timeStamp[i])

        rain_list = []  # 所有场雨的列表
        for j in range(len(rain_idx)):
            start = rain_idx[j][0]
            end = rain_idx[j][1]
            rain = year_df[start:end + 1]
            rain_list.append(rain)

    return rain_list


def step1_run(input_path, pickle_out_path, pre_threshold=None, start_year=None, end_year=None):
    '''
    基于格尔木雨型项目代码修改
    后续加上山东分钟数据格式和国家气象局分钟数据格式
    解析降水数据，划分场雨
    input_path: dict={R:'xxx/xxx.dat',
                      J:'xxx/xx'}
    '''
    # 数据解析
    data_list = []
    for key, path in input_path.items():
        if key == 'J':
            j_data = decode_j_pre(path)
            data_list.append(j_data)

        elif key == 'R':
            r_data = decode_r_pre(path)
            data_list.append(r_data)

    rain_total_df = pd.concat(data_list, axis=0)
    rain_total_df.sort_index(inplace=True)
    rain_total_df.index.name = 'Datetime'
    year_begin = rain_total_df.index.year[0] + 1  # R文件特性，处理完后多出一年，但没有数据
    year_end = rain_total_df.index.year[-1]
    st_id = rain_total_df.iloc[0,0] # 增加站号
    
    # 阈值筛选
    if pre_threshold != None:
        rain_total_df.iloc[:, 5:] = np.where(rain_total_df.iloc[:, 5:] < pre_threshold, 0, rain_total_df.iloc[:, 5:])

    # 取原始数据自身的起始终止年份
    if start_year == None:
        start_year = year_begin

    if end_year == None:
        end_year = year_end

    # 创建结果保存字典
    result = edict()

    # 划分场雨
    for i in range(start_year, end_year + 1):
        result[str(i)] = dict()
        df = get_year_data(rain_total_df, i)  # 一年的降水数据
        interval=[120,150,180,240,360,720,1440]

        for inr in interval:
            rain_list = divide_rain(df, inr)
            result[str(i)][str(inr) + 'min_interval'] = edict()
            result[str(i)][str(inr) + 'min_interval']['each_rain'] = rain_list

            table = pd.DataFrame(columns=['开始时间', '结束时间', '时长', '总雨量', '第几场雨'])

            if rain_list != []:
                for num, rain in enumerate(rain_list):
                    first_time = rain.iloc[0, -1].strftime('%Y-%m-%d %H:%M:%S')
                    last_time = rain.iloc[-1, -1].strftime('%Y-%m-%d %H:%M:%S')
                    total_time = len(rain)
                    total_pre = rain['pre'].sum()

                    df_row = table.shape[0]
                    table.loc[df_row] = [first_time, last_time, total_time, total_pre, num]

            table = table.round(2)
            result[str(i)][str(inr) + 'min_interval']['table'] = table

    # 保存结果为pickle，供后面的步骤程序读取
    with open(pickle_out_path + '/step1_result.txt', 'wb') as f:
        pickle.dump(result, f)

    result['pickle'] = pickle_out_path + '/step1_result.txt'

    # 处理result里面的时间格式、删除字典里面的each_rain key
    result_json = copy.deepcopy(result)

    for year, sub_dict in result_json.items():
        if year != 'pickle':
            for inr, rain_info in sub_dict.items():
                rain_info.pop('each_rain', None)

                for key, val in rain_info.items():
                    rain_info['table'] = val.to_dict(orient='records')

                    # 处理each_rain里面每个df的时间格式
                    # elif key == 'each_rain':
                    #     temp = edict()
                    #     for num,df in enumerate(val):
                    #         df = df.reset_index(drop=True).copy()
                    #         df['time'] = df['time'].dt.strftime('%Y-%m-%d %H:%M:%S')
                    #         temp[str(num)] = df.to_dict(orient='records')
                    #     rain_info[key] = temp

    return result_json, start_year, end_year, st_id


def get_minute_rain_seq(pickle_path, year, inr, num_rain):
    '''
    从每年统计的所有场雨总表中，提取特定一场雨的分钟变化序列
    '''
    try:
        with open(pickle_path, 'rb') as f:
            data_dict = pickle.load(f)

    except Exception:
        raise Exception('第一步划分场雨生成的pickle文件没有读取成功，请检查文件输出路径')

    rain = data_dict[str(year)][str(inr) + 'min_interval']['each_rain'][num_rain]
    rain['time'] = rain['time'].dt.strftime('%Y-%m-%d %H:%M:%S')
    rain.reset_index(drop=True, inplace=True)

    return rain


if __name__ == '__main__':
    # input_path = {'R': r'C:/Users/MJY/Desktop/tongren/R/R015297419672001.DAT', 'J': r'C:/Users/MJY/Desktop/tongren/J'}
    input_path = {"J": r'C:\Users\MJY\Desktop\rain_min\J', "R":r'C:\Users\MJY\Desktop\rain_min\R\R015271319642001.DAT'}
    pickle_out_path = r'C:/Users/MJY/Desktop/result'
    result_1, start_year_out, end_year_out, st_id = step1_run(input_path=input_path, 
                                                       pickle_out_path=pickle_out_path, 
                                                       pre_threshold=None, 
                                                       start_year=None, 
                                                       end_year=None)

    # # 读取某一场雨的详情
    # pickle_path = r'C:\Users\MJY\Desktop\result\step1_result.txt'
    # year = 1957
    # inr = 1440
    # num_rain = 20
    # rain = get_minute_rain_seq(pickle_path, year, inr, num_rain)
