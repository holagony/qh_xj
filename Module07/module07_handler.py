import os
import json
import time
import uuid
import logging
import simplejson
import numpy as np
import pandas as pd
from collections import OrderedDict
from flask import Blueprint, request, jsonify, current_app
from Utils.config import cfg
from Utils.name_utils import equalsIgnoreCase
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_loader_with_threads import get_cmadaas_daily_data
from Utils.data_processing import daily_data_processing
from Utils.get_local_data import get_local_data
from Module00.wrapped.check import check
from Module07.wrapped.garden_city import calc_heat_island_garden_city
from Module07.wrapped.heat_island import calc_heat_island
from Report.code.Module07.heat_island import heat_island_report
from Report.code.Module07.garden_city_report import garden_city_report

def garden_city_handler(data_json):
    '''
    园林城市热岛接口   园林城市
    主站和副站排列组合，如果所有主站或所有副站都没数据，则结果表全是nan
    '''
    # 1.读取json中的信息
    # json_str = request.get_data(as_text=True)  # 获取JSON字符串
    # data_json = json.loads(json_str)
    years = data_json['years']
    main_sta_ids = data_json['main_sta_ids']  # 主站
    sub_sta_ids = data_json['sub_sta_ids']  # 对比站

    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    # 2.参数处理
    if isinstance(main_sta_ids, list):
        main_sta_ids = [str(ids) for ids in main_sta_ids]
        main_sta_ids_str = ','.join(main_sta_ids)
    if isinstance(main_sta_ids, (int, str)):
        main_sta_ids = [str(main_sta_ids)]
        main_sta_ids_str = str(main_sta_ids)

    if isinstance(sub_sta_ids, list):
        sub_sta_ids = [str(ids) for ids in sub_sta_ids]
        sub_sta_ids_str = ','.join(sub_sta_ids)
    if isinstance(sub_sta_ids, (int, str)):  # 只有单个值的情况
        sub_sta_ids = [str(sub_sta_ids)]
        sub_sta_ids_str = str(sub_sta_ids)

    # 3.参数直接预设好
    daily_elements = 'TEM_Max'

    # 3.数据获取
    if cfg.INFO.READ_LOCAL:
        sta_ids = main_sta_ids_str + ',' + sub_sta_ids_str
        day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements).split(',')
        daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
        daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')
    else:
        try:
            sta_ids = main_sta_ids_str + ',' + sub_sta_ids_str
            daily_df = get_cmadaas_daily_data(years, daily_elements, sta_ids)

            if daily_df is not None:
                daily_df = daily_data_processing(daily_df, years)

        except Exception as e:
            logging.exception(e)
            raise Exception('天擎数据获取失败')

    # 4.生成结果
    try:
        result_dict = edict()
        result_dict['uuid'] = uuid4

        # module00完整率统计
        years_split = years.split(',')
        result_dict.check_result = edict()
        if daily_df is not None and len(daily_df) != 0:
            checker = check(daily_df, 'D', daily_elements.split(','), sta_ids.split(','), years_split[0], years_split[1])
            result_dict.check_result['使用的天擎日要素'] = checker.run()

        # 计算
        result_table = calc_heat_island_garden_city(daily_df, main_sta_ids, sub_sta_ids)
        
        try:
            report_path = garden_city_report(result_table,data_dir)
            report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
            result_dict['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
        except:
            result_dict['report'] = None
        
        result_dict['result'] = result_table.to_dict(orient='records')

    except Exception as e:
        logging.exception(e)
        raise Exception('现有获取的数据不能满足园林城市热岛计算条件，无法得到计算结果')

    return result_dict


def heat_island_handler(data_json):
    '''
    气象站热岛接口   城市气候规划
    主站和副站排列组合，如果所有主站或所有副站都没数据，则结果表全是nan
    '''
    # 1.读取json中的信息
    # json_str = request.get_data(as_text=True)  # 获取JSON字符串
    # data_json = json.loads(json_str)
    years = data_json['years']
    main_sta_ids = data_json['main_sta_ids']  # 主站
    sub_sta_ids = data_json['sub_sta_ids']  # 对比站
    time_resolution = data_json['time_resolution']
    data_types = data_json['data_types']

    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    # 2.参数处理
    if isinstance(years, dict):
        years = list(years.values())
        years.sort()

    if isinstance(data_types, str):
        data_types = [data_types]

    if isinstance(main_sta_ids, list):
        main_sta_ids = [str(ids) for ids in main_sta_ids]
        main_sta_ids_str = ','.join(main_sta_ids)
    if isinstance(main_sta_ids, (int, str)):
        main_sta_ids = [str(main_sta_ids)]
        main_sta_ids_str = str(main_sta_ids)

    if isinstance(sub_sta_ids, list):
        sub_sta_ids = [str(ids) for ids in sub_sta_ids]
        sub_sta_ids_str = ','.join(sub_sta_ids)
    if isinstance(sub_sta_ids, (int, str)):  # 只有单个值的情况
        sub_sta_ids = [str(sub_sta_ids)]
        sub_sta_ids_str = str(sub_sta_ids)

    # 3.参数直接预设好
    daily_elements = ''
    for type_ in data_types:
        if equalsIgnoreCase(type_, 'Avg'):
            daily_elements += 'TEM_Avg,'
        elif equalsIgnoreCase(type_, 'Max'):
            daily_elements += 'TEM_Max,'
        elif equalsIgnoreCase(type_, 'Min'):
            daily_elements += 'TEM_Min,'

    # 3.数据获取
    if cfg.INFO.READ_LOCAL:
        sta_ids = main_sta_ids_str + ',' + sub_sta_ids_str
        day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements[:-1]).split(',')
        daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
        daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')
    else:
        try:
            sta_ids = main_sta_ids_str + ',' + sub_sta_ids_str
            daily_df = get_cmadaas_daily_data(years, daily_elements, sta_ids)
            daily_df = daily_data_processing(daily_df, years)
        except Exception as e:
            logging.exception(e)
            raise Exception('现有获取的数据不能满足园林城市热岛计算条件，无法得到计算结果')

    # 5.生成结果
    try:
        result_dict = calc_heat_island(daily_df, main_sta_ids, sub_sta_ids, time_resolution, data_types)
        result_dict['uuid'] = uuid4
    
        try:
            report_path = heat_island_report(time_resolution,result_dict,daily_df, main_sta_ids,data_types,data_dir)
            report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
            result_dict['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
        except:
            result_dict['report'] = None
    
        # module00完整率统计
        daily_elements = daily_elements[:-1]
        years_split = years.split(',')
        result_dict.check_result = edict()
        if daily_df is not None and len(daily_df) != 0:
            checker = check(daily_df, 'D', daily_elements.split(','), sta_ids.split(','), years_split[0], years_split[1])
            result_dict.check_result['使用的天擎日要素'] = checker.run()

    except Exception as e:
        logging.exception(e)
        raise Exception('现有获取的数据不能满足普通热岛计算条件，无法得到计算结果')

    return result_dict
