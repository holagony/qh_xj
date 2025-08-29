import os
import platform
import glob
import time
import datetime
import numpy as np
import pandas as pd
import psycopg2
from tqdm import tqdm
from psycopg2 import sql
from sqlalchemy import create_engine
from dateutil.relativedelta import relativedelta
from datetime import timedelta
from urllib.parse import quote_plus as urlquote
from Utils.config import cfg
from Utils.my_server import get_server_sshtunnel
from Utils.data_processing import database_data_processing
from libs.nmc_met_io.retrieve_cmadaas import cmadaas_obs_by_time_range_and_id
from libs.nmc_met_io.retrieve_cmadaas_history import get_hist_obs_id


def get_cmadaas_yearly_data(years, elements, sta_ids):
    '''
    以年为跨度，获取天擎年值数据
    '''
    years = years.split(',')
    start_year = int(years[0])
    end_year = int(years[1])
    range_year = np.arange(start_year, end_year + 1, 1)

    default_elements = 'Station_Id_C,Station_Name,Lat,Lon,Datetime,Year'
    all_elements = default_elements + ',' + elements
    data_code = 'SURF_CHN_MUL_YER'

    # 获取数据 dataframe形式
    data = get_hist_obs_id(years=range_year, data_code=data_code, elements=all_elements, sta_ids=sta_ids)
    #data.to_csv(r'C:\Users\mjynj\Desktop\result.csv',encoding='utf_8_sig')

    return data


def get_cmadaas_monthly_data(years, elements, sta_ids):
    '''
    以年为跨度，获取天擎月值数据
    '''
    years = years.split(',')
    start_year = int(years[0])
    end_year = int(years[1])
    range_year = np.arange(start_year, end_year + 1, 1)

    default_elements = 'Station_Id_C,Station_Name,Lat,Lon,Datetime,Year,Mon'
    all_elements = default_elements + ',' + elements
    data_code = 'SURF_CHN_MUL_MON'

    # 获取数据 dataframe形式
    data = get_hist_obs_id(years=range_year, data_code=data_code, elements=all_elements, sta_ids=sta_ids)
    #data.to_csv(r'C:\Users\mjynj\Desktop\result.csv',encoding='utf_8_sig')

    return data


def get_cmadaas_daily_data(years, elements, sta_ids):
    '''
    以年为跨度，获取天擎日值数据
    '''
    years = years.split(',')
    start_year = int(years[0])
    end_year = int(years[1])
    range_year = np.arange(start_year, end_year + 1, 1)

    default_elements = 'Station_Id_C,Station_Name,Lat,Lon,Datetime,Year,Mon,Day'
    all_elements = default_elements + ',' + elements
    data_code = 'SURF_CHN_MUL_DAY'

    # 获取数据 dataframe形式
    data = get_hist_obs_id(years=range_year, data_code=data_code, elements=all_elements, sta_ids=sta_ids)
    #data.to_csv(r'C:\Users\mjynj\Desktop\result.csv',encoding='utf_8_sig')

    return data


def get_cmadaas_hourly_data(start_date, num_years, elements, sta_ids, ranges=None):
    '''
    以年为跨度，获取天擎小时数据
    '''
    fmt = '%Y%m%d%H%M%S'
    date = datetime.datetime.strptime(str(start_date), fmt)
    date = date - relativedelta(hours=8)

    default_elements = 'Station_Id_C,Station_Name,Lat,Lon,Datetime,Year,Mon,Day,Hour'
    all_elements = default_elements + ',' + elements
    data_code = 'SURF_CHN_MUL_HOR'
    interval = 6 * num_years

    for i in tqdm(range(0, interval)):
        start = (date + relativedelta(months=2) * i).strftime(fmt)
        end = (date + relativedelta(months=2) * (i + 1)).strftime(fmt)
        time_range = '[' + start + ',' + end + ')'
        df = cmadaas_obs_by_time_range_and_id(time_range, data_code=data_code, elements=all_elements, ranges=ranges, sta_ids=sta_ids)

        if i == 0:
            data = df

        else:
            data = pd.concat([data, df], axis=0)

    #data.to_csv(r'C:\Users\mjynj\Desktop\result.csv',encoding='utf_8_sig')

    return data


def get_connection(server=None):
    '''
    获取数据库连接信息
    server = get_server_sshtunnel() 生成的实例
    '''
    if server is not None:  # 有server实例
        host = '127.0.0.1'
        port = server.local_bind_port

    else:
        host = cfg.FILES.db_host
        port = cfg.FILES.db_port

    conn = psycopg2.connect(database=cfg.FILES.db_name, user=cfg.FILES.db_user, password=cfg.FILES.db_pwd, host=host, port=port)
    return conn


def is_self_station(sta_id):
    """
    返回1 代表自建站
    """
    # 为空当天擎站处理
    if not sta_id:
        return 0
    if (platform.node() != cfg.FILES.node) and (cfg.FILES.flag == 'server'):  # 在非服务器平台连接flag='server'
        # 就调取sshtunnel信息
        server_case = get_server_sshtunnel()
        server_case.start()
        conn = get_connection(server=server_case)

    else:
        conn = get_connection(server=None)

    query = sql.SQL("SELECT station_levl From {schema}.tbl_station WHERE station_id_c = %s").format(schema=sql.Identifier(cfg.FILES.schema_name))
    cur = conn.cursor()
    cur.execute(query, (sta_id, ))

    data = cur.fetchall()
    conn.close()

    if (platform.node() != cfg.FILES.node) and (cfg.FILES.flag == 'server'):
        server_case.close()

    # 类型为00的是自建站
    if len(data) == 0:
        # abort(500, f'{sta_id}此站不存在.')
        raise Exception(f'{sta_id}此站不存在')

    if data[0][0] == '00':
        flag = 1

    else:
        flag = 0

    return flag


def get_data_postgresql(sta_id, time_range, use, module01_elements=None):
    '''
    从psycopg2读取数据，目前在用的
    '''
    times = time_range.split(',')
    start = times[0]
    end = times[1]

    if (platform.node() != cfg.FILES.node) and (cfg.FILES.flag == 'server'):
        server_case = get_server_sshtunnel()
        server_case.start()
        conn = get_connection(server=server_case)

    else:
        conn = get_connection(server=None)

    if use == 'module04':
        query = sql.SQL("SELECT station_no,year,month,day,hour,height,min10_ws,sec3_ws,tem_avg,tem_max,tem_min,rhu,prs,pre From {schema}.tbl_station_data WHERE station_no = %s AND year >= %s AND year <= %s").format(
            schema=sql.Identifier(cfg.FILES.schema_name))
        cur = conn.cursor()
        cur.execute(query, (sta_id, start, end))

        data = cur.fetchall()
        df = pd.DataFrame(data)
        df.columns = ['station_no', 'year', 'month', 'day', 'hour', 'height', 'min10_ws', 'sec3_ws', 'tem_avg', 'tem_max', 'tem_min', 'rhu', 'prs', 'pre']

    elif use == 'module01':
        module01_elements = 'station_no,year,month,day,hour,height' + ',' + module01_elements
        module01_elements = module01_elements.split(',')
        fields = sql.SQL(',').join(sql.Identifier(*f.split('.')) for f in module01_elements)

        query = sql.SQL("SELECT {fields} From {schema}.tbl_station_data WHERE station_no = %s AND year >= %s AND year <= %s").format(fields=fields, schema=sql.Identifier(cfg.FILES.schema_name))
        cur = conn.cursor()
        cur.execute(query, (sta_id, start, end))

        data = cur.fetchall()
        df = pd.DataFrame(data)
        df.columns = module01_elements

    conn.close()

    if (platform.node() != cfg.FILES.node) and (cfg.FILES.flag == 'server'):
        server_case.close()

    return df


# flag = is_self_station('Z0001')
# df = get_data_postgresql(sta_id='Z0001',time_range='2000,2020', use='module04')
# data_meteo, data_10min_wind, data_3s_wind = database_data_processing(df)
