# -*- coding: utf-8 -*-
"""
Created on Thu Dec 12 21:23:21 2024

@author: EDY
"""
import sys
sys.path.append('/app/libs/nmc_met_io')
import os
import platform
import glob
import time
import logging
import datetime
import numpy as np
import pandas as pd
from tqdm import tqdm
from dateutil.relativedelta import relativedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from Utils.config import cfg
from Utils.cost_time import cost_time
from nmc_met_io.retrieve_cmadaas import cmadaas_obs_by_time_range_and_id, cmadaas_obs_by_time_range_and_id_radi
from nmc_met_io.retrieve_cmadaas import cmadaas_obs_in_rect_by_time_range



def get_cmadaas_monthly_data(years, elements, sta_ids):
    '''
    多线程月值数据下载
    '''

    def download_month(vals, ranges=None):
        '''
        数据下载代码
        '''
        time_range, elements, sta_ids = vals
        data_code = 'SURF_CHN_MUL_MON'
        default_elements = 'Station_Id_C,Station_Name,Lat,Lon,Datetime,Year,Mon'
        all_elements = default_elements + ',' + elements
        ranges = None
        df = cmadaas_obs_by_time_range_and_id(time_range=time_range, data_code=data_code, elements=all_elements, ranges=ranges, sta_ids=sta_ids)
        return df

    # 生成输入参数
    start_year, end_year = map(int, years.split(','))
    range_year = np.arange(start_year, end_year + 1, 1)
    time_range_template = '[{},{}]'
    all_params = [(time_range_template.format(str(year) + '0101000000', str(year) + '1231230000'), elements, sta_ids) for year in range_year]

    # 创建线程池
    with ThreadPoolExecutor(max_workers=cfg.INFO.NUM_THREADS) as pool:
        futures = [pool.submit(download_month, param) for param in all_params]

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

years='2014,2024'   
elements='PRS_Avg,TEM_Avg,TEM_Max,TEM_Min,RHU_Avg,RHU_Min,CLO_Cov_Avg,CLO_Cov_Low_Avg,PRE_Time_2020,SSH,WIN_S_2mi_Avg,WIN_S_Max,WIN_D_S_Max_C,WIN_S_Inst_Max,WIN_D_INST_Max_C,GST_Avg,GST_Max,GST_Min'
sta_ids ='53498, 53593, 54401, 54404, 54405, 54408, 53798, 54429, 54434, 54437, 54439, 54522, 54531, 54532, 54534, 53689, 53694, 53784, 53789, 54701, 54449, 54515, 54518, 54520, 54521, 54612, 54702, 54704, 54710, 53892, 53894, 53896, 54640, 54318, 54319, 54423, 54430, 54610, 54614, 54616, 54624, 54713, 53692, 53696, 54502, 54506, 54507, 54601, 54602, 54604, 54605, 54620, 54636, 50136, 50442, 50557, 50646, 50658, 50745, 50750, 50755, 50756, 50774, 50775, 50779, 50850, 50854, 50858, 50859, 50867, 50873, 50877, 50884, 50888, 50950, 50953, 50954, 50956, 50960, 50968, 50971, 50978, 50979, 50985, 54080, 54092, 54094, 54098, 50936, 50939, 50946, 50949, 54063, 54064, 54069, 54072, 54154, 54157, 54161, 54172, 54181, 54186, 54260, 54266, 54273, 54274, 54286, 54292, 54363, 54371, 54249, 54324, 54326, 54327, 54339, 54342, 54346, 54347, 54351, 54453, 54454, 54455, 54471, 54497, 54563, 54662, 54714, 54726, 54734, 54736, 54765, 54777, 54806, 54808, 54814, 54819, 54823, 54826, 54827, 54828, 54830, 54835, 54842, 54843, 54844, 54857, 54861, 54904, 54905, 54906, 54908, 54909, 54911, 54913, 54914, 54915, 54922, 54927, 54936, 54938, 54945, 58002, 58011, 58024, 53486, 53487, 53488, 53490, 53574, 53582, 53590, 53594, 53659, 53673, 53674, 53753, 53769, 53771, 53772, 53776, 53780, 53782, 53861, 53866, 53868, 53882, 53959, 53976, 54428, 54523, 54525, 54526, 54527, 54528, 54529, 54530, 54619, 54622, 54623, 54645'

df=get_cmadaas_monthly_data(years, elements, sta_ids)
df.to_csv('./result.csv')

