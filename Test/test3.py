import sys  
sys.path.append('..')

import os
import numpy as np
import pandas as pd
import time
from libs.nmc_met_io.retrieve_cmadaas import cmadaas_obs_by_time_range_and_id, cmadaas_obs_in_admin_by_time_range
from libs.nmc_met_io.retrieve_cmadaas_history import get_hist_obs_id
import datetime
from dateutil.relativedelta import relativedelta
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from Utils.config import cfg
from Utils.data_loader_with_threads import get_cmadaas_hourly_data, get_cmadaas_daily_data, get_cmadaas_min_data


def get_cmadaas_daily_data_range(years, elements, adcode='630000', sta_ids=None):
    '''
    多线程日值数据下载 用区域码
    '''
    def download_day(vals, ranges=None):
        '''
        数据下载代码
        '''
        time_range, elements, sta_ids, adcode = vals
        data_code = 'SURF_CHN_MUL_HOR'
        default_elements = 'Station_Id_C,Station_Name,Lat,Lon,Datetime,Year'
        all_elements = default_elements + ',' + elements

        # 获取数据 dataframe形式
        df = cmadaas_obs_in_admin_by_time_range(time_range=time_range, 
                                                admin=adcode, 
                                                data_code=data_code,
                                                elements=all_elements,
                                                ranges=ranges,
                                                sta_levels='011,012,013')
        return df

    # 生成输入参数
    
    start_year, end_year = map(int, years.split(','))
    range_year = np.arange(start_year, end_year+1, 1)
    time_range_template = '[{},{}]'
    all_params = [(time_range_template.format(str(year)+'0101000000', str(year)+'1231230000'), elements, sta_ids, adcode) for year in range_year]

    # 创建线程池
    with ThreadPoolExecutor(max_workers=20) as pool:
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


# 保存路径
save_path = os.path.abspath(os.path.dirname(__file__))
qh_data = os.path.join(save_path,'qh_data.csv')
min_data = os.path.join(save_path,'min_data.csv')
hour_data = os.path.join(save_path,'hour_data.csv')
day_data = os.path.join(save_path,'day_data.csv')



# # 4.日数据下载
years = '2000,2020'
elements = 'PRE_Time_2020'
sta_ids = '51730'
df4 = get_cmadaas_daily_data(years, elements, sta_ids)
# df4.to_csv(day_data, encoding='utf_8_sig')
# print('日数据 finish')
print(df4.head(10))



