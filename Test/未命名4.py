# -*- coding: utf-8 -*-
"""
Created on Tue Dec 24 16:48:30 2024

@author: EDY
"""

import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.data_loader_with_threads import get_cmadaas_daily_data
from libs.nmc_met_io.retrieve_cmadaas import cmadaas_obs_by_time_range_and_id
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_cmadaas_daily_data(year, elements, sta_ids):
    '''
    多线程日值数据下载
    '''

    def download_day(vals, ranges=None):
        '''
        数据下载代码
        '''
        time_range, elements, sta_ids = vals
        data_code = 'SURF_CHN_MUL_DAY'
        default_elements = 'Station_Id_C,Station_Name,Lat,Lon,Datetime,Year,Mon,Day'
        all_elements = default_elements + ',' + elements
        df = cmadaas_obs_by_time_range_and_id(time_range=time_range, data_code=data_code, elements=all_elements, ranges=ranges, sta_ids=sta_ids)
        return df

    # 生成输入参数
    time_range_template = '[{},{}]'
    all_params = [time_range_template.format(str(year) + '0101000000', str(year) + '1231230000'), elements, sta_ids]

    # 创建线程池
    with ThreadPoolExecutor(max_workers=cfg.INFO.NUM_THREADS) as pool:
        futures = [pool.submit(download_day, param) for param in all_params]

    # 获取结果并合并数据
    # dfs = [f.result() for f in as_completed(futures)]
    dfs = []
    for f in as_completed(futures):
        if f.result() is not None:
            tmp = f.result().drop_duplicates()
            dfs.append(tmp)

    # concentrate dataframes
    if len(dfs) == 0:
        return None
    else:
        return pd.concat(dfs, axis=0, ignore_index=True).sort_values(by='Datetime')
    
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
        cold_wave_result = None


    finally:
        return cold_wave_result
        
        
elements =  ('Station_Id_C,Station_Name,Lat,Lon,Datetime,Year,Mon,Day,' + 'TEM_Avg,TEM_Min,WIN_S_Max,WIN_D_S_Max,SSH,PRE_Time_2020').split(',')
sta_ids = '51886,52602,52633,52645,52657,52707,52713,52737,52745,52754,52765,52818,52825,52833,52836,52842,52853,52855,52856,52862,52863,52866,52868,52869,52874,52876,52877,52908,52943,52955,52957,52963,52968,52972,52974,56004,56016,56018,56021,56029,56033,56034,56043,56045,56046,56065,56067,56125,56151'
year='2021'
