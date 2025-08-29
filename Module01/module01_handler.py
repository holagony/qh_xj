import os
import logging
import uuid
import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_loader_with_threads import get_cmadaas_daily_data
from Utils.data_loader import get_data_postgresql, is_self_station
from Utils.data_processing import daily_data_processing
from Module01.wrapped.time_consistency_analysis import time_analysis
from Module01.wrapped.spatial_consistency_analysis import space_analysis
from Module01.wrapped.correlation_analysis import correlation_analysis
from Report.code.Module01.correlation_analysis_report import correlation_analysis_report
from Report.code.Module01.spatial_consistency_report import spatial_consistency_report
from Utils.get_url_path import save_cmadaas_data

# 时间一致性分析 删除小时参数
def time_consistency_handler(data_json):
    '''
    mk突变检验和滑动T检验接口
    '''
    # 1.读取json中的信息
    years = data_json['years']  # 选择的数据年份
    sta_ids = data_json['station_ids']  # 选择的参证站号,可以多站 list
    elements = data_json['elements']  # 选择的气象要素
    method = data_json['method']
    seq_len = data_json.get('seq_len')

    # 2.参数处理
    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    if isinstance(sta_ids, list):
        sta_ids = [str(ids) for ids in sta_ids]
        sta_ids_str = ','.join(sta_ids)
    elif isinstance(sta_ids, int):
        sta_ids = str(sta_ids)

    if seq_len is not None:
        seq_len = int(seq_len)
    else:
        seq_len = 5

    # 3.拼接需要下载的参数，直接预设好
    daily_elements = ','.join(elements)
    day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements).split(',')

    # 4.数据获取
    if cfg.INFO.READ_LOCAL:
        sta_ids_int = [int(ids) for ids in sta_ids]
        daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
        daily_df = daily_df.loc[daily_df['Station_Id_C'].isin(sta_ids_int), day_eles]
        daily_df = daily_data_processing(daily_df,years)
    else:
        try:
            daily_df = get_cmadaas_daily_data(years, daily_elements, sta_ids_str)
            daily_df = daily_data_processing(daily_df,years)
        except Exception as e:
            logging.exception(e)
            raise Exception('天擎数据获取失败')

    # 5.生成结果
    try:
        result_dict = time_analysis(daily_df, elements, method, sta_ids, seq_len)
        result_dict['uuid'] = uuid4
    except Exception as e:
        logging.exception(e)
        raise Exception('现有获取的数据不能满足突变检验计算条件，无法得到计算结果')

    if cfg.INFO.SAVE_RESULT:
        result_dict['csv'] = save_cmadaas_data(data_dir, day_data=daily_df)

    return result_dict


# 空间一致性分析 删除小时参数
def spatial_consistency_handler(data_json):
    '''
    独立T检验和F检验接口
    气象站要累年各月要素组合展示
    '''
    years = data_json['years']
    main_sta_ids = data_json['main_sta_ids']  # 参证站站号，单选
    sub_sta_ids = data_json['sub_sta_ids']  # 对比站站号，多选
    elements = data_json['elements']  # 选择的气象要素
    method = data_json['method']  # 方法 t_test/f_test

    # 2.参数处理 最终字符串类型
    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    if isinstance(main_sta_ids, list):
        main_sta_ids = [str(ids) for ids in main_sta_ids]
        main_sta_ids = ','.join(main_sta_ids)
    if isinstance(main_sta_ids, int):
        main_sta_ids = str(main_sta_ids)

    if isinstance(sub_sta_ids, list):
        sub_sta_ids = [str(ids) for ids in sub_sta_ids]
        sub_sta_ids = ','.join(sub_sta_ids)
    if isinstance(sub_sta_ids, int):
        sub_sta_ids = str(sub_sta_ids)

    # 3.拼接需要下载的参数
    # 天擎站 vs 天擎站  PRS_Avg/PRS_Max/PRS_Min/TEM_Avg/TEM_Max/TEM_Min/RHU_Avg/PRE_Time_2020/WIN_S_Max/WIN_S_Avg_2mi
    daily_elements = ','.join(elements)
    day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements).split(',')

    # 3.数据获取/数据处理
    if cfg.INFO.READ_LOCAL:
        sta_ids = main_sta_ids + ',' + sub_sta_ids
        sta_ids1 = [int(ids) for ids in sta_ids.split(',')]
        daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
        daily_df = daily_df.loc[daily_df['Station_Id_C'].isin(sta_ids1), day_eles]
        daily_df = daily_data_processing(daily_df,years)
    else:
        try:
            sta_ids = main_sta_ids + ',' + sub_sta_ids
            daily_df = get_cmadaas_daily_data(years, daily_elements, sta_ids)
            daily_df = daily_data_processing(daily_df,years)
        except Exception as e:
            logging.exception(e)
            raise Exception('天擎数据获取失败')

    # 5.生成结果
    try:
        sub_sta_ids = sub_sta_ids.split(',')
        result_dict = space_analysis(daily_df, elements, main_sta_ids, sub_sta_ids, method)

        try:
            report_path = spatial_consistency_report(result_dict,main_sta_ids,sub_sta_ids,data_dir)
            report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
            result_dict['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
        except:
            result_dict['report'] = None
                
    except Exception as e:
        logging.exception(e)
        raise Exception('现有获取的数据不能满足一致性检验计算条件，无法得到计算结果')

    if cfg.INFO.SAVE_RESULT:
        result_dict['csv'] = save_cmadaas_data(data_dir, day_data=daily_df)
    
    result_dict['uuid'] = uuid4

    return result_dict


# 要素相关性分析
def calc_correlation_daily_data_handler(data_json):
    '''
    相关性分析接口，小时和日数据
    '''
    # 1.读取json中的信息
    years = data_json['years']
    main_sta_ids = data_json['main_sta_ids']  # 参证站站号，单个
    sub_sta_ids = data_json['sub_sta_ids']  # 对比站站号，多个
    elements = data_json['elements']  # 选择的气象要素
    method = data_json['method']

    # 2.参数处理
    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    if isinstance(main_sta_ids, list):
        main_sta_ids = [str(ids) for ids in main_sta_ids]
        main_sta_ids = ','.join(main_sta_ids)
    if isinstance(main_sta_ids, int):
        main_sta_ids = str(main_sta_ids)

    if isinstance(sub_sta_ids, list):
        sub_sta_ids = [str(ids) for ids in sub_sta_ids]
        sub_sta_ids = ','.join(sub_sta_ids)
    if isinstance(sub_sta_ids, int):
        sub_sta_ids = str(sub_sta_ids)

    # 3.拼接需要下载的参数
    # 天擎站 vs 天擎站  PRS_Avg/PRS_Max/PRS_Min/TEM_Avg/TEM_Max/TEM_Min/RHU_Avg/PRE_Time_2020/WIN_S_Max/WIN_S_Avg_2mi
    daily_elements = ','.join(elements)
    day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements).split(',')

    # 3.数据获取
    if cfg.INFO.READ_LOCAL:
        sta_ids = main_sta_ids + ',' + sub_sta_ids
        sta_ids1 = [int(ids) for ids in sta_ids.split(',')]
        daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
        daily_df = daily_df.loc[daily_df['Station_Id_C'].isin(sta_ids1), day_eles]
        daily_df = daily_data_processing(daily_df,years)
    else:
        try:
            sta_ids = main_sta_ids + ',' + sub_sta_ids
            daily_df = get_cmadaas_daily_data(years, daily_elements, sta_ids)
            daily_df = daily_data_processing(daily_df,years)
        except Exception as e:
            logging.exception(e)
            raise Exception('天擎数据获取失败')

    # 5.生成结果
    try:
        sub_sta_ids = sub_sta_ids.split(',')
        result_dict = correlation_analysis(daily_df, elements, main_sta_ids, sub_sta_ids, method,data_dir)
        result_dict['uuid'] = uuid4
        
        # url替换
        for key_1, values_1 in result_dict.items():
            if key_1 == 'picture':
                for  key_2, values_2 in values_1.items():
                    try:
                        for name, path in values_2.items():
                            # print(path)
                            path = path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)  # 图片容器内转容器外路径
                            values_2[name] = path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
                    except:
                        pass      
        
        try:
            report_path = correlation_analysis_report(result_dict,main_sta_ids,sub_sta_ids,daily_df,data_dir,method)
            report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
            result_dict['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
        except:
            result_dict['report'] = None

    except Exception as e:
        logging.exception(e)
        raise Exception('现有获取的数据不能相关性分析计算条件，无法得到计算结果')

    if cfg.INFO.SAVE_RESULT:
        result_dict['csv'] = save_cmadaas_data(data_dir, day_data=daily_df)

    return result_dict

if __name__ == '__main__':
    
    data_json=dict()
    
    data_json["years"]= "2009,2017"
    data_json["main_sta_ids"]= "56033"
    data_json["sub_sta_ids"]= "56151,52818,52602"
    data_json["elements"]= ["TEM_Avg","PRS_Avg","RHU_Avg","WIN_S_2mi_Avg","TEM_Max","PRS_Max","WIN_S_Max","TEM_Min","PRS_Min","PRE_Time_2020"]
    data_json["method"]= ["ratio"]
    
    result_dict = calc_correlation_daily_data_handler(data_json)