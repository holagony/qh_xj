# -*- coding: utf-8 -*-
"""
Created on Tue Dec 24 16:35:59 2024

@author: EDY
"""

import numpy as np
import pandas as pd
from Utils.data_processing import daily_data_processing, hourly_data_processing
from Utils.get_local_data import get_local_data
import logging


def generate_group_num(values, diff=1):
    group_ids = []
    group_id = 0
    last_v = 0

    for value in values:
        if value - last_v > diff:
            group_id += 1

        group_ids.append(group_id)
        last_v = value

    return group_ids


def get_cold_wave_idxs(df, cold_wave_level=(8, 10, 12)):
    cold_wave_idxs = set()
    ids = df.index[df['TEM_Min'].diff(-1) >= cold_wave_level[0]].values
    cold_wave_idxs.update(ids)
    cold_wave_idxs.update(ids + 1)

    ids = df.index[df['TEM_Min'].diff(-2) >= cold_wave_level[1]].values
    cold_wave_idxs.update(ids)
    cold_wave_idxs.update(ids + 1)
    cold_wave_idxs.update(ids + 2)

    ids = df.index[df['TEM_Min'].diff(-3) >= cold_wave_level[2]].values
    cold_wave_idxs.update(ids)
    cold_wave_idxs.update(ids + 1)
    cold_wave_idxs.update(ids + 2)
    cold_wave_idxs.update(ids + 3)

    return sorted(cold_wave_idxs)


def cold_wave_statistics(data_df):
    '''
    table1.多站点寒潮过程统计表
    table2.多站点寒潮大风统计表
    table3.多站寒潮大风风向频数统计表
    需要的要素：'TEM_Avg','TEM_Min','WIN_S_Max','WIN_D_S_Max'
    
    如果某个站缺少要素，导致不能统计，则输出结果的三个表里面没有这个站
    如果所有站都缺少要素，导致不能统计，则输出None
    '''

    def sample_row(x):
        '''
        table2寒潮大风的pandas apply函数
        '''
        x = x.to_frame().T
        name = x.iloc[0, 0]  # 站名
        start_date = x.iloc[0, 1]
        end_date = x.iloc[0, 2]

        data = sample_data[sample_data['Station_Name'] == name]
        rows = data[start_date:end_date]
        rows = rows[(rows['WIN_S_Max'] > 10.8) & (rows['WIN_D_S_Max'].isin(['WNW', 'NW', 'NNW', 'N', 'NNE', 'NE', 'ENE']))]

        if len(rows) != 0:
            rows = rows[rows['WIN_S_Max'] == rows['WIN_S_Max'].max()]  # 取风速最大的一行
            rows = rows.head(1)
            rows['降温幅度'] = x.loc[:, '降温幅度'].values
            rows['影响前日期'] = str(x.loc[:, '开始日期'].values[0])[5:]
            rows['影响前平均气温'] = str(x.loc[:, '开始日平均气温'].values[0])
            rows['影响前最低气温'] = str(x.loc[:, '开始日最低气温'].values[0])
            rows['过程最低气温'] = x.loc[:, '过程最低气温'].values
            rows['过程平均气温'] = x.loc[:, '过程平均气温'].values
            return rows

    def sample(x):
        '''
        table3的pandas apply函数
        '''
        t = x['当日风向'].value_counts().to_frame()
        t['频数'] = (t['当日风向'] / t['当日风向'].sum()).round(3)
        return t

    try:
      
        sample_data = data_df[['Station_Id_C', 'Station_Name', 'Year', 'Mon', 'Day', 'TEM_Avg', 'TEM_Min', 'WIN_S_Max', 'WIN_D_S_Max']]
        cold_wave_dict = {'cold_wave_temperature_diffs': (8, 10, 12), 'min_temperature_limit': 4, 'cold_wave_type': '寒潮'}

        # table1 寒潮过程
        cold_wave_result = []
        for number, tmp in sample_data.groupby('Station_Name'):
            tmp = tmp.reset_index()
            cold_wave_idxs = get_cold_wave_idxs(tmp, cold_wave_dict['cold_wave_temperature_diffs'])

            if len(cold_wave_idxs) < 2:
                continue

            for i, cold_wave_idx_serial in pd.Series(cold_wave_idxs).groupby(generate_group_num(cold_wave_idxs)):
                cold_wave_idx_serial = cold_wave_idx_serial.values
                start_id, end_id = cold_wave_idx_serial[0], cold_wave_idx_serial[-1]

                # 假如最低温度小于指定度数，则说明满足全部条件
                if tmp.loc[end_id, 'TEM_Min'] <= cold_wave_dict['min_temperature_limit']:
                    cold_wave_result.append((
                        number,
                        tmp.loc[start_id, 'index'], # 原来是Datetime
                        tmp.loc[end_id, 'index'], # 原来是Datetime
                        tmp.loc[start_id, 'TEM_Min'],
                        tmp.loc[end_id, 'TEM_Min'],
                        tmp.loc[start_id, 'TEM_Avg'],
                        tmp.loc[end_id, 'TEM_Avg'],
                        end_id - start_id + 1,
                        tmp.loc[start_id, 'TEM_Min'] - tmp.loc[end_id, 'TEM_Min'],  # 降温幅度
                        tmp.loc[start_id:end_id + 1, 'TEM_Min'].min(),
                        tmp.loc[start_id:end_id + 1, 'TEM_Avg'].mean(),
                        cold_wave_dict['cold_wave_type']))

        cold_wave_result = pd.DataFrame(cold_wave_result)
        cold_wave_result.columns = ['站名', '开始日期', '结束日期', '开始日最低气温', '结束日最低气温', '开始日平均气温', '结束日平均气温', '寒潮天数', '降温幅度', '过程最低气温', '过程平均气温', '类型']
        cold_wave_result['开始日期'] = cold_wave_result['开始日期'].dt.strftime('%Y-%m-%d')
        cold_wave_result['结束日期'] = cold_wave_result['结束日期'].dt.strftime('%Y-%m-%d')

        cold_wave_result = cold_wave_result.round(1)#.to_dict(orient='records')


    except Exception as e:
        logging.exception(e)
        cold_wave_result = None


    finally:
        return cold_wave_result

if __name__ == '__main__':
    day_eles = ('Station_Id_C,Station_Name,Lat,Lon,Datetime,Year,Mon,Day,' + 'TEM_Avg,TEM_Min,WIN_S_Max,WIN_D_S_Max,SSH,PRE_Time_2020').split(',')
    path = r'D:\Project\3_项目\2_气候评估和气候可行性论证\qhkxxlz\Files\test_data\qh_day.csv'
    df = pd.read_csv(path)
   
    years = '2000,2000'
    sta_ids = '52866,52862,56067'
    day_data = get_local_data(df, sta_ids, day_eles, years, 'Day')
    cold_wave_result = cold_wave_statistics(day_data)