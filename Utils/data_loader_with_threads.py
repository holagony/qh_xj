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
from libs.nmc_met_io.retrieve_cmadaas import cmadaas_obs_by_time_range_and_id, cmadaas_obs_by_time_range_and_id_radi
from libs.nmc_met_io.retrieve_cmadaas import cmadaas_obs_in_rect_by_time_range


@cost_time
def get_cmadaas_yearly_data(years, elements, sta_ids):
    '''
    多线程年值数据下载
    '''

    def download_year(vals, ranges=None):
        '''
        数据下载代码
        '''
        time_range, elements, sta_ids = vals
        data_code = 'SURF_CHN_MUL_YER'
        default_elements = 'Station_Id_C,Station_Name,Datetime'
        all_elements = default_elements + ',' + elements
        df = cmadaas_obs_by_time_range_and_id(time_range=time_range, data_code=data_code, elements=all_elements, ranges=ranges, sta_ids=sta_ids)
        return df

    # 生成输入参数
    start_year, end_year = map(int, years.split(','))
    range_year = np.arange(start_year, end_year + 1, 1)
    time_range_template = '[{},{}]'
    all_params = [(time_range_template.format(str(year) + '0101000000', str(year) + '1231235959'), elements, sta_ids) for year in range_year]

    # 创建线程池
    with ThreadPoolExecutor(max_workers=cfg.INFO.NUM_THREADS) as pool:
        futures = [pool.submit(download_year, param) for param in all_params]

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


@cost_time
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
        default_elements = 'Station_Id_C,Station_Name,Datetime,Lon,Lat'
        all_elements = default_elements + ',' + elements
        ranges = None
        df = cmadaas_obs_by_time_range_and_id(time_range=time_range, data_code=data_code, elements=all_elements, ranges=ranges, sta_ids=sta_ids)
        return df

    # 生成输入参数
    start_year, end_year = map(int, years.split(','))
    range_year = np.arange(start_year, end_year + 1, 1)
    time_range_template = '[{},{}]'
    all_params = [(time_range_template.format(str(year) + '0101000000', str(year) + '1231235959'), elements, sta_ids) for year in range_year]

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


@cost_time
def get_cmadaas_daily_data(years, elements, sta_ids):
    '''
    多线程日值数据下载
    '''

    def download_day(vals, ranges=None):
        '''
        数据下载代码
        '''
        time_range, elements, sta_ids = vals
        data_code = 'SURF_CHN_MUL_DAY'
        default_elements = 'Station_Id_C,Station_Name,Datetime'
        all_elements = default_elements + ',' + elements
        df = cmadaas_obs_by_time_range_and_id(time_range=time_range, data_code=data_code, elements=all_elements, ranges=ranges, sta_ids=sta_ids)
        return df

    # 生成输入参数
    start_year, end_year = map(int, years.split(','))
    range_year = np.arange(start_year, end_year + 1, 1)
    time_range_template = '[{},{}]'
    all_params = [(time_range_template.format(str(year) + '0101000000', str(year) + '1231235959'), elements, sta_ids) for year in range_year]

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


@cost_time
def get_cmadaas_hourly_data(start_date, num_years, elements, sta_ids):
    '''
    以年为跨度，获取天擎小时数据
    '''

    def download_hour(vals, ranges=None):
        '''
        数据下载代码
        '''
        time_range, elements, sta_ids = vals
        data_code = 'SURF_CHN_MUL_HOR'
        default_elements = 'Station_Id_C,Station_Name,Datetime'
        all_elements = default_elements + ',' + elements
        ranges = None
        # df = pd.DataFrame([time_range, elements, sta_ids]).T
        df = cmadaas_obs_by_time_range_and_id(time_range=time_range, data_code=data_code, elements=all_elements, ranges=ranges, sta_ids=sta_ids)
        return df

    # 生成输入参数
    fmt = '%Y%m%d%H%M%S'
    date = datetime.datetime.strptime(str(start_date), fmt)
    date = date - relativedelta(hours=8)  # 由于是世界时，减8
    interval = 6 * num_years

    all_params = []
    for i in range(0, interval):
        start = (date + relativedelta(months=2) * i).strftime(fmt)
        end = (date + relativedelta(months=2) * (i + 1)).strftime(fmt)
        time_range = '[' + start + ',' + end + ')'
        p = [time_range, elements, sta_ids]
        all_params.append(p)

    # 创建线程
    with ThreadPoolExecutor(max_workers=cfg.INFO.NUM_THREADS) as pool:
        futures = [pool.submit(lambda params: download_hour(*params), (vals, )) for vals in all_params]

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


@cost_time
def get_cmadaas_min_data(start_date, num_years, elements, sta_ids):
    '''
    以年为跨度，获取天擎分钟数据
    '''

    def download_hour(vals, ranges=None):
        '''
        数据下载代码
        '''
        time_range, elements, sta_ids = vals
        data_code = 'SURF_CHN_MUL_MIN'
        default_elements = 'Station_Id_C,Station_Name,Lat,Lon,Datetime'
        all_elements = default_elements + ',' + elements
        ranges = None
        # df = pd.DataFrame([time_range, elements, sta_ids]).T
        df = cmadaas_obs_by_time_range_and_id(time_range=time_range, data_code=data_code, elements=all_elements, ranges=ranges, sta_ids=sta_ids)
        return df

    # 生成输入参数
    fmt = '%Y%m%d%H%M%S'
    date = datetime.datetime.strptime(str(start_date), fmt)
    interval = 12 * num_years

    all_params = []
    for i in range(0, interval):
        start = (date + relativedelta(months=1) * i).strftime(fmt)
        end = (date + relativedelta(months=1) * (i + 1)).strftime(fmt)
        time_range = '[' + start + ',' + end + ')'
        p = [time_range, elements, sta_ids]
        all_params.append(p)

    # 创建线程
    with ThreadPoolExecutor(max_workers=30) as pool:
        futures = [pool.submit(lambda params: download_hour(*params), (vals, )) for vals in all_params]

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


# start_date = '20220101000000'
# num_years = 2
# elements = 'PRE'
# sta_ids = '59948'
# df = get_cmadaas_min_data(start_date,num_years,elements,sta_ids)


@cost_time
def get_adtd_data_threads(date_range, limit):
    '''
    多线程ADTD数据下载 
    输入北京时，输出世界时，有北京时向世界时的转换
    '''

    def download_adtd(vals, limit):
        '''
        数据下载代码
        '''
        time_range = vals
        data_code = 'UPAR_LIGHT_ADTD_MUL'
        #limit = [31, 89.5, 39.3, 103.1]
        default_elements = 'Lat,Lon,Year,Mon,Day,Hour,Min,Second,MSecond,Lit_Current,Lit_Prov,Lit_City,Lit_Cnty'
        df = cmadaas_obs_in_rect_by_time_range(time_range=time_range, limit=limit, data_code=data_code, elements=default_elements)
        return df

    # 生成输入参数
    start_date, end_date = date_range.split(',')
    start_year = int(start_date[:4])
    end_year = int(end_date[:4])
    range_year = np.arange(start_year, end_year + 1, 1)
    time_range_template = '[{},{}]'
    all_params = []

    if len(start_date) and len(end_date) == 4:  # 年
        all_params = [(time_range_template.format(str(year) + '0101000000', str(year) + '1231235959')) for year in range_year]

    elif len(start_date) and len(end_date) == 6:  # 年月
        for num, year in enumerate(range_year):
            if num == 0:
                all_params.append((time_range_template.format(str(year) + start_date[4:] + '01000000', str(year) + '1231235959')))
            elif num > 0 and num != len(range_year) - 1:
                all_params.append((time_range_template.format(str(year) + '0101000000', str(year) + '1231235959')))
            else:
                all_params.append((time_range_template.format(str(year) + '0101000000', str(year) + end_date[4:] + '31235959')))

    elif len(start_date) and len(end_date) == 8:  # 年月日 2020080910
        for num, year in enumerate(range_year):
            if num == 0:
                all_params.append((time_range_template.format(str(year) + start_date[4:] + '000000', str(year) + '1231235959')))
            elif num > 0 and num != len(range_year) - 1:
                all_params.append((time_range_template.format(str(year) + '0101000000', str(year) + '1231235959')))
            else:
                all_params.append((time_range_template.format(str(year) + '0101000000', str(year) + end_date[4:] + '235959')))

    else:  # 年月日时分秒
        for num, year in enumerate(range_year):
            if num == 0:
                all_params.append((time_range_template.format(str(year) + start_date[4:], str(year) + '1231235959')))
            elif num > 0 and num != len(range_year) - 1:
                all_params.append((time_range_template.format(str(year) + '0101000000', str(year) + '1231235959')))
            else:
                all_params.append((time_range_template.format(str(year) + '0101000000', str(year) + end_date[4:])))

    # 创建线程池
    with ThreadPoolExecutor(max_workers=cfg.INFO.NUM_THREADS) as pool:
        futures = [pool.submit(download_adtd, param, limit) for param in all_params]

    # 获取结果并合并数据
    dfs = []
    for f in as_completed(futures):
        if f.result() is not None:
            tmp = f.result().drop_duplicates()
            dfs.append(tmp)

    if len(dfs) == 0:
        return None
    else:
        return pd.concat(dfs, axis=0, ignore_index=True)


@cost_time
def get_cmadaas_radi_data(start_date, num_years, elements, sta_ids):
    '''
    以年为跨度，获取天擎辐射小时数据
    '''

    def download_hour(vals, ranges=None):
        '''
        数据下载代码
        '''
        time_range, elements, sta_ids = vals
        data_code = 'RADI_CHN_MUL_HOR'
        default_elements = 'Station_Id_C,Datetime,Lat,Lon'
        all_elements = default_elements + ',' + elements
        ranges = None
        # df = pd.DataFrame([time_range, elements, sta_ids]).T
        df = cmadaas_obs_by_time_range_and_id_radi(time_range=time_range, data_code=data_code, elements=all_elements, ranges=ranges, sta_ids=sta_ids)
        return df

    # 生成输入参数
    fmt = '%Y%m%d%H%M%S'
    date = datetime.datetime.strptime(str(start_date), fmt)
    date = date - relativedelta(hours=8)  # 由于是世界时，减8
    interval = 6 * num_years

    all_params = []
    for i in range(0, interval):
        start = (date + relativedelta(months=2) * i).strftime(fmt)
        end = (date + relativedelta(months=2) * (i + 1)).strftime(fmt)
        time_range = '[' + start + ',' + end + ')'
        p = [time_range, elements, sta_ids]
        all_params.append(p)

    # 创建线程
    with ThreadPoolExecutor(max_workers=cfg.INFO.NUM_THREADS) as pool:
        futures = [pool.submit(lambda params: download_hour(*params), (vals, )) for vals in all_params]

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
