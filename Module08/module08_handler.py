import os
import json
import simplejson
import uuid
import numpy as np
import pandas as pd
from flask import Blueprint, request, jsonify
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_loader_with_threads import get_cmadaas_hourly_data
from Utils.data_processing import hourly_data_processing
from Utils.get_local_data import get_local_data
from Module00.wrapped.check import check
from Module08.wrapped.airport_wind import calc_airport_wind_ds, calc_airport_wind_loading
from Report.code.Module08.airport_wind_ds_report import airport_wind_ds_report
from Report.code.Module08.airport_wind_loading_report import airport_wind_loading_report

def airport_wind_ds_handler(data_json):
    '''
    计算机场-统计不同风速区间的风向接口
    '''
    # 1.读取json中的信息
    # json_str = request.get_data(as_text=True) # 获取JSON字符串
    # data_json = json.loads(json_str)
    years = data_json['years']
    sta_ids = data_json['station_ids']
    numeric_interval = data_json['numeric_interval']

    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    if isinstance(sta_ids, list):
        sta_ids = [str(ids) for ids in sta_ids]
        sta_ids = ','.join(sta_ids)
    if isinstance(sta_ids, int):
        sta_ids = str(sta_ids)

    # 2.参数直接预设好
    years_split = years.split(',')
    num_years = int(years_split[1]) - int(years_split[0]) + 1
    start_date = years_split[0] + '010100000'
    hourly_elements = 'WIN_D_Avg_10mi,WIN_S_Avg_10mi'

    # 4.数据获取
    if cfg.INFO.READ_LOCAL:
        hour_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,' + hourly_elements).split(',')
        hourly_df = pd.read_csv(cfg.FILES.QH_DATA_HOUR)
        hourly_df = get_local_data(hourly_df, sta_ids, hour_eles, years, 'Hour')
    else:
        try:
            hourly_df = get_cmadaas_hourly_data(start_date, num_years, hourly_elements, sta_ids)
            hourly_df = hourly_data_processing(hourly_df, years)
        except Exception as e:
            raise Exception('天擎数据获取失败')

    # 5.生成结果
    try:
        # module00完整率统计
        result_dict = edict()
        result_dict['uuid'] = uuid4
    
        years_split = years.split(',')
        result_dict.check_result = edict()
        if hourly_df is not None and len(hourly_df) != 0:
            checker = check(hourly_df, 'H', hourly_elements.split(','), [sta_ids], years_split[0], years_split[1])
            result_dict.check_result['使用的天擎日要素'] = checker.run()
    
        result_table = calc_airport_wind_ds(hourly_df, numeric_interval)
        result_dict['不通风速区间风向统计表'] = result_table.to_dict(orient='records')
        
        try:
            report_path = airport_wind_ds_report(result_table,data_dir)
            report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
            result_dict['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
        except:
            result_dict['report'] = None
            

    except Exception as e:
        raise Exception('无法得到机场风速区间统计结果，请检查设定的风速区间是否正常/天擎是否有数据')

    return result_dict


def airport_wind_loading_handler(data_json):
    '''
    计算满足最大允许侧风值的侧风数，和相应的风保障率接口
    不用数据前处理
    '''
    # 1.读取json中的信息
    # json_str = request.get_data(as_text=True) # 获取JSON字符串
    # data_json = json.loads(json_str)
    years = data_json['years']
    sta_ids = data_json['station_ids']

    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    if isinstance(sta_ids, list):
        sta_ids = [str(ids) for ids in sta_ids]
        sta_ids = ','.join(sta_ids)
    if isinstance(sta_ids, int):
        sta_ids = str(sta_ids)

    # 2.参数直接预设好
    years_split = years.split(',')
    num_years = int(years_split[1]) - int(years_split[0]) + 1
    start_date = years_split[0] + '010100000'
    hourly_elements = 'WIN_D_Avg_10mi,WIN_S_Avg_10mi'

    # 3.数据获取
    if cfg.INFO.READ_LOCAL:
        hour_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,' + hourly_elements).split(',')
        hourly_df = pd.read_csv(cfg.FILES.QH_DATA_HOUR)
        hourly_df = get_local_data(hourly_df, sta_ids, hour_eles, years, 'Hour')
    else:
        try:
            hourly_df = get_cmadaas_hourly_data(start_date, num_years, hourly_elements, sta_ids)
            hourly_df = hourly_data_processing(hourly_df, years)
        except Exception as e:
            raise Exception('天擎数据获取失败')

    # 4.生成结果
    # module00完整率统计
    result_dict = edict()
    result_dict['uuid'] = uuid4

    years_split = years.split(',')
    result_dict.check_result = edict()
    if hourly_df is not None and len(hourly_df) != 0:
        checker = check(hourly_df, 'H', hourly_elements.split(','), [sta_ids], years_split[0], years_split[1])
        result_dict.check_result['使用的天擎日要素'] = checker.run()

    # 计算
    result_table = calc_airport_wind_loading(hourly_df)
    result_dict['风力负荷统计表'] = result_table.to_dict(orient='records')
    
    try:
        report_path = airport_wind_loading_report(result_table,data_dir)
        report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
        result_dict['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
    except:
        result_dict['report'] = None
            
    return result_dict
