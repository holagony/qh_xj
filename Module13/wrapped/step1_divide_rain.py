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
    提取每一年的数据，变成df - 优化版本
    '''
    year_df = df[df['year'] == num_year].copy()
    year_df = year_df.set_index(['station', 'year', 'month', 'day', 'hour']).stack().reset_index()
    year_df.rename(columns={'level_5': 'minute', 0: 'pre'}, inplace=True)
    
    # 优化：使用向量化操作替代apply
    year_df['minute'] = year_df['minute'].str[:-3].astype(int) - 1
    year_df = year_df[['station', 'year', 'month', 'day', 'hour', 'minute', 'pre']]
    
    # 优化：直接使用pd.to_datetime，避免字符串拼接
    year_df['time'] = pd.to_datetime(year_df[['year', 'month', 'day', 'hour', 'minute']])

    return year_df


def divide_rain(year_df, interval):
    '''
    对每一年的数据进行划分场雨 - 优化版本
    '''
    data_noZero = year_df[year_df['pre'] != 0].dropna()

    if len(data_noZero) == 0:
        return []

    timeStamp = data_noZero.index.values
    
    # 优化：使用numpy向量化操作计算时间差
    if len(timeStamp) == 1:
        return [year_df.iloc[timeStamp[0]:timeStamp[0]+1]]
    
    diffs = np.diff(timeStamp)
    break_points = np.where(diffs >= interval)[0]
    
    # 构建雨段的起始和结束索引
    starts = np.concatenate([[timeStamp[0]], timeStamp[break_points + 1]])
    ends = np.concatenate([timeStamp[break_points], [timeStamp[-1]]])
    
    # 批量创建雨段列表
    rain_list = [year_df.iloc[start:end + 1] for start, end in zip(starts, ends)]
    
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

    # 划分场雨 - 优化版本
    interval = [120, 150, 180, 240, 360, 720, 1440]
    
    for i in range(start_year, end_year + 1):
        result[str(i)] = dict()
        df = get_year_data(rain_total_df, i)  # 一年的降水数据

        for inr in interval:
            rain_list = divide_rain(df, inr)
            result[str(i)][str(inr) + 'min_interval'] = edict()
            result[str(i)][str(inr) + 'min_interval']['each_rain'] = rain_list

            # 优化：批量处理表格数据，避免逐行添加
            if rain_list:
                table_data = []
                for num, rain in enumerate(rain_list):
                    first_time = rain.iloc[0, -1].strftime('%Y-%m-%d %H:%M:%S')
                    last_time = rain.iloc[-1, -1].strftime('%Y-%m-%d %H:%M:%S')
                    total_time = len(rain)
                    total_pre = rain['pre'].sum()
                    table_data.append([first_time, last_time, total_time, total_pre, num])
                
                table = pd.DataFrame(table_data, columns=['开始时间', '结束时间', '时长', '总雨量', '第几场雨'])
                table = table.round(2)
            else:
                table = pd.DataFrame(columns=['开始时间', '结束时间', '时长', '总雨量', '第几场雨'])
            
            result[str(i)][str(inr) + 'min_interval']['table'] = table

    # 保存结果为pickle，供后面的步骤程序读取
    with open(pickle_out_path + '/step1_result.txt', 'wb') as f:
        pickle.dump(result, f)

    result['pickle'] = pickle_out_path + '/step1_result.txt'

    # 处理result里面的时间格式、删除字典里面的each_rain key - 优化版本
    result_json = edict()
    result_json['pickle'] = result['pickle']
    
    # 优化：避免深拷贝，直接构建需要的数据结构
    for year, sub_dict in result.items():
        if year != 'pickle':
            result_json[year] = {}
            for inr, rain_info in sub_dict.items():
                # 直接转换table为字典格式，跳过each_rain
                result_json[year][inr] = {
                    'table': rain_info['table'].to_dict(orient='records')
                }

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
