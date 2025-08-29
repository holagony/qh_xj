import os
import logging
import uuid
import pandas as pd
from flask import Blueprint, request, jsonify
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_loader_with_threads import get_cmadaas_daily_data
from Utils.data_processing import daily_data_processing
from Utils.get_local_data import get_local_data
from Module11.wrapped.wind_dataloader import wind_tower_upload, set_data_heights, get_data_postgresql, wind_tower_processing
from Module11.wrapped.wind_func1 import wind_stats1
from Module11.wrapped.wind_func2 import wind_stats2
from Module11.wrapped.wind_func3 import wind_stats3
from Module11.wrapped.wind_func4 import wind_stats4
from Module11.wrapped.wind_func5 import wind_stats5
from Report.code.Module11.wind_func1_report import wind_func1_report
from Report.code.Module11.wind_func2_report import wind_func2_report
from Report.code.Module11.wind_func3_report import wind_func3_report
from docx import Document
from docxcompose.composer import Composer


module11 = Blueprint('module11', __name__)
'''
主要包含5部分：
1.测风塔数据质量检验(缺测时间统计+有效数据完整率)
2.风速&风功率参数统计
3.风能参数统计&风频曲线计算
4.湍流强度&风切变&阵风系数计算 todo
'''


def data_upload_handler(data_json):
    '''
    读取原始excel格式测风塔数据的文件夹路径，处理为特定格式入库
    '''
    input_path = data_json['input_path'] # 路径是完整的挂载文件夹路径
    stations = data_json['stations']
    lon = data_json.get('lon')
    lat = data_json.get('lat')

    input_path = input_path.replace(cfg.INFO.OUT_UPLOAD_FILE, cfg.INFO.IN_UPLOAD_FILE)  # inupt_path要转换为容器内的路径

    if '\\' in input_path:
        input_path = input_path.replace('\\', '/') # windows to linux

    # logging.info(input_path)
    wind_tower_upload(input_path, stations, lon, lat)



def data_set_height_handler(data_json):
    '''
    修改数据库测风塔数据的高度值，一次修改一个高度
    '''
    stations = data_json['stations']
    cur_val = data_json['cur_val']  # 现在的高度值 str
    new_val = data_json['new_val']  # 修改的高度值 str
    set_data_heights(stations, cur_val, new_val)


def data_quality_check_handler(data_json):
    '''
    子页面1:
    数据选择(从数据库)
    测风塔数据质量检验(缺测时间统计+有效数据完整率)
    '''
    stations = data_json['stations']  # 'QH001'
    time_range = data_json['time_range']  # 年月日 '20230801,20240630'
    consider_diff = data_json['consider_diff']

    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    # main
    df = get_data_postgresql(stations, time_range)
    after_process = wind_tower_processing(df)
    check_result1 = wind_stats1(after_process, time_range)
    check_result2 = wind_stats2(after_process, time_range, consider_diff)

    result_dict = edict()
    result_dict['数据缺测时间检验'] = check_result1
    result_dict['有效数据完整率'] = check_result2
    result_dict['uuid'] = uuid4
    
    try:
        report_path=wind_func1_report(check_result1,check_result2,time_range,data_dir)
        report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
        result_dict['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
    except Exception as e:
        print(f"报告 发生了错误：{e}")
        result_dict['report'] = None
    
    return result_dict


def data_params_stats1_handler(data_json):
    '''
    子页面2:
    数据选择(从数据库)
    风速&风功率参数统计
    '''
    sta_ids = data_json['sta_ids']  # 天擎站点
    years = data_json['years']  # 天擎的时间段选择
    stations = data_json['stations']  # 'QH001'
    time_range = data_json['time_range']  # 年月日 '20230801,20240630'
    input_ws = data_json['input_ws']
    output_ws = data_json['output_ws']

    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    # 天擎数据和处理
    if cfg.INFO.READ_LOCAL:
        day_eles = ['Station_Id_C','Station_Name','Lat','Lon','Datetime','Year','Mon','Day','TEM_Avg', 'PRS_Avg']
        daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
        daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')
    else:
        try:
            daily_elements = 'TEM_Avg,PRS_Avg'
            daily_df = get_cmadaas_daily_data(years, daily_elements, sta_ids)
            daily_df = daily_data_processing(daily_df, years)
        except Exception as e:
            logging.exception(e)
            raise Exception('天擎数据下载或处理失败')

    # 计算
    df = get_data_postgresql(stations, time_range)
    after_process = wind_tower_processing(df)
    result_dict = wind_stats3(after_process, daily_df, input_ws, output_ws)
    result_dict['uuid'] = uuid4
    
    try:
        report_path=wind_func2_report(result_dict,data_dir)
        report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
        result_dict['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
    except Exception as e:
        print(f"报告 发生了错误：{e}")
        result_dict['report'] = None

    return result_dict


def data_params_stats2_handler(data_json):
    '''
    子页面3
    数据选择(从数据库)
    风能参数统计&风频率曲线统计
    '''
    sta_ids = data_json['sta_ids']  # 天擎站点
    years = data_json['years']  # 天擎的时间段选择
    stations = data_json['stations']  # 'QH001'
    time_range = data_json['time_range']  # 年月日 '20230801,20240630'
    input_ws = data_json['input_ws']
    output_ws = data_json['output_ws']

    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    # 天擎数据和处理
    if cfg.INFO.READ_LOCAL:
        day_eles = ['Station_Id_C','Station_Name','Lat','Lon','Datetime','Year','Mon','Day','TEM_Avg', 'PRS_Avg']
        daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
        daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')
    else:
        try:
            daily_elements = 'TEM_Avg,PRS_Avg'
            daily_df = get_cmadaas_daily_data(years, daily_elements, sta_ids)
            daily_df = daily_data_processing(daily_df,years)
        except Exception as e:
            logging.exception(e)
            raise Exception('天擎数据下载或处理失败')

    # 计算
    df = get_data_postgresql(stations, time_range)
    after_process = wind_tower_processing(df)
    result1 = wind_stats4(after_process, daily_df, input_ws, output_ws)
    result2 = wind_stats5(after_process, data_dir)
    result_dict = edict()

    try:
        report_path=wind_func3_report(result1,result2,data_dir)
        report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
        result_dict['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
    except Exception as e:
        logging.exception(e)
        print(f"报告 发生了错误：{e}")
        result_dict['report'] = None
        
    # result2 url替换
    for key, sub_dict in result2.items():
        for key1, sub_dict1 in sub_dict.items():
            if key1 == 'img_save_path':
                try:
                    for name, path in sub_dict1.items():
                        path = path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)  # 图片容器内转容器外路径
                        sub_dict1[name] = path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
                except:
                    pass

    # 保存
    result_dict['风能参数统计'] = result1
    result_dict['风频曲线统计'] = result2
    result_dict['uuid'] = uuid4

    return result_dict
