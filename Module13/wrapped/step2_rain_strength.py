import json
import simplejson
import pickle
import numpy as np
import pandas as pd
from Utils.ordered_easydict import OrderedEasyDict as edict


def rolling_max_rain_seq(rain_inr, minute, num_rain, year):
    '''
    输入:
    rain_inr: 某一年120min or 150min or 180min间隔的场雨列表
    minute: 历时
    num_rain: 每年从大到小统计的历时数量
    year: 当前场雨列表对应的年份
    
    输出:
    max_records 包括最大历时雨量(滑动计算得到)，历时雨起始时间，历时雨对应的场雨起始时间
    '''
    duration_table = pd.DataFrame(columns=['duration_start', 'duration_end', 'sum_pre', 'idx', 'year'])

    if rain_inr != []:
        for num, rain in enumerate(rain_inr):
            if len(rain) > minute:
                max_sum = rain['pre'].rolling(window=minute).sum().max()  # 最大降水量之和
                max_sum_idx = rain['pre'].rolling(window=minute).sum().idxmax()
                max_seq = rain.loc[max_sum_idx - minute + 1:max_sum_idx]

                start_time = max_seq.iloc[0, -1]
                end_time = max_seq.iloc[-1, -1]
                values = [start_time, end_time, max_sum, num, year]

            else:
                max_sum = rain['pre'].sum()
                start_time = rain.iloc[0, -1]
                end_time = rain.iloc[-1, -1]
                values = [start_time, end_time, max_sum, num, year]

            duration_table.loc[len(duration_table)] = values

        # 每年在这个历时的最大N个记录，和起始时间
        max_records = duration_table[duration_table['sum_pre'].isin(duration_table['sum_pre'].nlargest(num_rain))].sort_values('sum_pre', ascending=[False]).reset_index(drop=True)

        # 添加所对应的场雨起始时间列
        max_records['rain_start'] = max_records['idx'].apply(lambda x: rain_inr[x].iloc[0, -1])
        max_records['rain_end'] = max_records['idx'].apply(lambda x: rain_inr[x].iloc[-1, -1])

        max_records = max_records[['year', 'sum_pre', 'duration_start', 'duration_end', 'rain_start', 'rain_end']]

        # 如果出现雨量重复的情况
        if len(max_records) > num_rain:
            max_records = max_records.iloc[0:num_rain, :]

    else:
        max_records = pd.DataFrame(columns=['year', 'sum_pre', 'duration_start', 'duration_end', 'rain_start', 'rain_end'])

    return max_records


def step2_run(pickle_path, output_path, start_year=None, end_year=None, num_rain=8):
    '''
    不同历时最大雨量计算
    输入：
    pickle_path 原始数据路径，来自step1输出的pickle
    output_path 输出数据路径，输出表格
    start_year 设定索引数据的起始年份
    end_year 设定索引数据的终止年份
    num_rain 设定一年从大到小统计几场雨
    
    输出：
    table0 每年1场最大的历时雨量
    table1 每年8场最大的历时雨量
    result 原始输出数据，按历时保存
    '''
    try:
        with open(pickle_path, 'rb') as f:
            data_dict = pickle.load(f)

    except Exception:
        raise Exception('第一步划分场雨生成的pickle文件没有读取成功，请检查文件输出路径')
    
    dict_years = list(data_dict.keys())
    dict_years = np.array([int(years) for years in dict_years])
    if start_year == None:
        start_year = dict_years.min()
    
    if end_year == None:
        end_year = dict_years.max()
    
    duration = [5, 10, 15, 20, 30, 45, 60, 90, 120, 150, 180, 240, 360, 720, 1440]
    result = edict()

    for i in range(start_year, end_year + 1):
        result[str(i)] = edict()
        rain_list = data_dict[str(i)]
        rain_inr120 = rain_list['120min_interval']['each_rain']  # 这一年120min间隔场雨
        rain_inr150 = rain_list['150min_interval']['each_rain']  # 这一年150min间隔场雨
        rain_inr180 = rain_list['180min_interval']['each_rain']  # 这一年180min间隔场雨
        rain_inr240 = rain_list['240min_interval']['each_rain']
        rain_inr360 = rain_list['360min_interval']['each_rain']
        rain_inr720 = rain_list['720min_interval']['each_rain']
        rain_inr1440 = rain_list['1440min_interval']['each_rain']

        for minute in duration:
            result[str(i)][str(minute) + 'min'] = edict()

            if minute <= 120:
                max_records = rolling_max_rain_seq(rain_inr120, minute, num_rain, i)

            elif minute == 150:
                max_records = rolling_max_rain_seq(rain_inr150, minute, num_rain, i)

            elif minute == 180:
                max_records = rolling_max_rain_seq(rain_inr180, minute, num_rain, i)

            elif minute == 240:
                max_records = rolling_max_rain_seq(rain_inr240, minute, num_rain, i)

            elif minute == 360:
                max_records = rolling_max_rain_seq(rain_inr360, minute, num_rain, i)

            elif minute == 720:
                max_records = rolling_max_rain_seq(rain_inr720, minute, num_rain, i)

            elif minute == 1440:
                max_records = rolling_max_rain_seq(rain_inr1440, minute, num_rain, i)

            result[str(i)][str(minute) + 'min'] = max_records

    # 把result里面的数据拼成表
    for num1, key1 in enumerate(list(result.keys())):
        year_result = result[key1]

        for num2, key2 in enumerate(list(year_result.keys())):
            duration_result = year_result[key2]
            sum_pre = duration_result['sum_pre'].to_frame()

            if num2 == 0:
                sum_pre_all = sum_pre
            else:
                sum_pre_all = pd.concat([sum_pre_all, sum_pre], axis=1)

        sum_pre_all.columns = list(year_result.keys())
        sum_pre_all.insert(loc=0, column='year', value=duration_result['year'])

        if num1 == 0:
            table1 = sum_pre_all
        else:
            table1 = pd.concat([table1, sum_pre_all], axis=0).reset_index(drop=True)
    
    # table1为每年各历时N场最大雨量
    # 存在N>每年场雨数的极端情况，导致产生nan值，因此要dropna
    table1.dropna(how='any', axis=0, inplace=True)
    
    # 年最大值样本保存
    table0 = table1.groupby(['year']).apply(lambda x: x[0:1]).reset_index(drop=True)  # 用于后面重现期的计算
    csv_path0 = output_path + '/single_sample.csv'
    table0.to_csv(csv_path0, encoding='utf_8_sig')

    # 年多样本保存
    csv_path1 = output_path + '/multi_sample.csv'
    num_idx = int((num_rain/2) * (end_year - start_year + 1))
    table2 = table1.iloc[:, :].apply(lambda x: np.sort(x)[::-1][:num_idx])
    table2.to_csv(csv_path1, encoding='utf_8_sig')  # 4N

    # 创建result_json，给前端
    result_json = edict()
    result_json['table0'] = table0.round(2).to_dict(orient='records')  # 每年1个样本
    result_json['table1'] = table1.round(2).to_dict(orient='records')  # 每年8个样本
    result_json['table2'] = table2.round(2).to_dict(orient='records')  # 每年8个样本取前4N
    result_json['single_sample'] = csv_path0
    result_json['multi_sample'] = csv_path1

    return result_json, result


if __name__ == '__main__':
    pickle_path = r'C:/Users/MJY/Desktop/result/step1_result.txt' # 来自第一个页面的id路径
    output_path = r'C:/Users/MJY/Desktop/result'
    start_year = None
    end_year = None
    num_rain = 8
    result_2, test_1  = step2_run(pickle_path, output_path, start_year, end_year, num_rain)
