# -*- coding: utf-8 -*-
"""
Created on Wed Dec 25 11:15:10 2024

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
    
elements =  ('Station_Id_C,Station_Name,Lat,Lon,Datetime,Year,Mon,Day,' + 'TEM_Avg,TEM_Min,WIN_S_Max,WIN_D_S_Max,SSH,PRE_Time_2020').split(',')
sta_ids = '51886,52602,52633,52645,52657,52707,52713,52737,52745,52754,52765,52818,52825,52833,52836,52842,52853,52855,52856,52862,52863,52866,52868,52869,52874,52876,52877,52908,52943,52955,52957,52963,52968,52972,52974,56004,56016,56018,56021,56029,56033,56034,56043,56045,56046,56065,56067,56125,56151'
year='2021'
df=get_cmadaas_daily_data(year, elements, sta_ids)