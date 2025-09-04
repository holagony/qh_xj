# -*- coding: utf-8 -*-
"""
Created on Thu Feb 22 15:02:21 2024

@author: EDY
"""
import os
import uuid
import pandas as pd
from Utils.config import cfg
from Module09.wrapped.gaussian_puff_model import gaussianPuffModel
from Module09.wrapped.gaussian_plume_model import gaussianPlumeModel
from Module09.wrapped.pollute import pollute_run
from Utils.data_processing import monthly_data_processing
from Utils.data_loader_with_threads import get_cmadaas_monthly_data
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.get_local_data import get_local_data
from Module00.wrapped.check import check
from collections import OrderedDict
from Utils.get_url_path import save_cmadaas_data
from Module09.wrapped.gaussian_puff_model_3D import gaussianPuffModel3D
from Module09.wrapped.gaussian_plume_model_3D import gaussianPlumeModel3D
from Report.code.Module09.pollute_report import pollute_report
from Report.code.Module09.gaussian_puff_report import gaussian_puff_report
from Report.code.Module09.gaussian_plume_report import gaussian_plume_report

def gaussian_plume_deal(data_json):

    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    # 获取参数
    lon = data_json['lon']
    lat = data_json['lat']
    q = data_json['q']
    h = data_json['h']
    wind_s = data_json['wind_s']
    wind_d = data_json['wind_d']
    z1 = data_json['z1']
    humidify = data_json.get('humidify')
    acid = data_json.get('acid')
    rh = data_json.get('rh')

    # 生成结果
    result_dict = gaussianPlumeModel(lon, lat, q, h, wind_s, wind_d, z1, data_dir, humidify=humidify, acid=acid, rh=rh)
    result_dict_3d = gaussianPlumeModel3D(lon, lat, q, h, wind_s, 270, z1, data_dir, humidify=humidify, acid=acid, rh=rh)

    try:
        report_path = gaussian_plume_report(result_dict,result_dict_3d, lon, lat, q, h, wind_s, wind_d, z1, data_dir)
        report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
        result_dict['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
    except:
        result_dict['report'] = None

    for key, pic_path in result_dict.items():
        pic_path = pic_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
        result_dict[key] = pic_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)

    for key, pic_path in result_dict_3d.items():
        pic_path = pic_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
        result_dict[key] = pic_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)

    result_dict['uuid'] = uuid4

    return result_dict


def gaussian_puff_deal(data_json):

    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    lon = data_json['lon']
    lat = data_json['lat']
    q = data_json['q']
    h = data_json['h']
    wind_s = data_json['wind_s']
    wind_d = data_json['wind_d']
    z1 = data_json['z1']
    t = data_json['t']
    delt_t = data_json['delt_t']
    humidify = data_json.get('humidify')
    acid = data_json.get('acid')
    rh = data_json.get('rh')
    
    # delt_t处理
    delt_t = str(delt_t)
    lenth = len(lon.split(','))
    for i in range(lenth):
        if i == 0:
            delt_tt = delt_t
        else:
            delt_tt = delt_tt + ',' + delt_t
    
    result_dict = gaussianPuffModel(lon, lat, q, h, wind_s, wind_d, z1, data_dir, t, delt_tt, acid=acid, humidify=humidify, rh=rh)
    result_dict_3d = gaussianPuffModel3D(lon, lat, q, h, wind_s, 270, z1, data_dir, t, delt_tt, acid=acid, humidify=humidify, rh=rh)

    try:
        report_path = gaussian_puff_report(result_dict,result_dict_3d, lon, lat, q, h, wind_s, wind_d, z1,  t, delt_tt,data_dir)
        report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
        result_dict['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
    except:
        result_dict['report'] = None

    for key, pic_path in result_dict.items():
        pic_path = pic_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
        result_dict[key] = pic_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)

    for key, pic_path in result_dict_3d.items():
        pic_path = pic_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
        result_dict[key] = pic_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)

    result_dict['uuid'] = uuid4
    return result_dict


def pollute_deal(data_json):

    # 1.参数读取
    years = data_json['years']  # 选择的数据年份Q
    sta_ids = data_json['sta_ids']  # 主站

    # 2.参数处理
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

    # 3.拼接需要下载的参数

    month_ele_list = [
        'PRE_Time_2020', 'WIN_S_2mi_Avg', 'WIN_NNE_Freq', 'WIN_NE_Freq', 'WIN_ENE_Freq', 'WIN_E_Freq', 'WIN_ESE_Freq', 'WIN_SE_Freq', 'WIN_SSE_Freq', 'WIN_S_Freq', 'WIN_SSW_Freq', 'WIN_SW_Freq', 'WIN_WSW_Freq', 'WIN_W_Freq', 'WIN_WNW_Freq',
        'WIN_NW_Freq', 'WIN_NNW_Freq', 'WIN_N_Freq', 'WIN_C_Freq', 'WIN_S_Avg_NNE', 'WIN_S_Avg_NE', 'WIN_S_Avg_ENE', 'WIN_S_Avg_E', 'WIN_S_Avg_ESE', 'WIN_S_Avg_SE', 'WIN_S_Avg_SSE', 'WIN_S_Avg_S', 'WIN_S_Avg_SSW', 'WIN_S_Avg_SW', 'WIN_S_Avg_WSW',
        'WIN_S_AVG_W', 'WIN_S_Avg_WNW', 'WIN_S_Avg_NW', 'WIN_S_Avg_NNW', 'WIN_S_Avg__N']
    month_ele = ','.join(month_ele_list)

    if cfg.INFO.READ_LOCAL:
        month_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,' + month_ele).split(',')
        monthly_df = pd.read_csv(cfg.FILES.QH_DATA_MONTH, low_memory=False)
        monthly_df = get_local_data(monthly_df, sta_ids, month_eles, years, 'Month')
    else:
        # 天擎数据下载 and 数据前处理
        try:
            if len(set(month_ele_list)) != 0:
                monthly_df = get_cmadaas_monthly_data(years, month_ele, sta_ids)
                monthly_df = monthly_data_processing(monthly_df,years)
            else:
                monthly_df = None

        except Exception as e:
            raise Exception('天擎数据下载或处理失败')

    # 5.计算之前先检测数据完整率 check H小时 D天 MS月 YS年
    result_dict = edict()
    result_dict['uuid'] = uuid4

    years = years.split(',')
    result_dict.check_result = edict()

    if monthly_df is not None and len(monthly_df) != 0:
        checker = check(monthly_df, 'MS', month_ele_list, [sta_ids], years[0], years[1])
        check_result = checker.run()
        result_dict.check_result['使用的天擎月要素'] = check_result

    # 6.结果生成
    result_dict.data = edict()
    p_c, depth_mixed_accum, ven_ability_accum, data_asc_accum, data_asi_accum = pollute_run(monthly_df)
    
    try:
        report_path = pollute_report(monthly_df,p_c, depth_mixed_accum, ven_ability_accum, data_asc_accum, data_asi_accum,data_dir)
        report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
        result_dict['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
    except:
        result_dict['report'] = None
    
    # 安全处理各个结果，避免None值导致的错误
    if p_c is not None:
        p_c = p_c.to_dict(orient='records')
        result_dict.data['污染系数'] = p_c
    else:
        result_dict.data['污染系数'] = None
        
    if depth_mixed_accum is not None:
        depth_mixed_accum = depth_mixed_accum.reset_index().to_dict(orient='records')
        result_dict.data['混合层厚度'] = depth_mixed_accum # 单位: m
    else:
        result_dict.data['混合层厚度'] = None
        
    if ven_ability_accum is not None:
        ven_ability_accum = ven_ability_accum.reset_index().to_dict(orient='records')
        result_dict.data['通风量'] = ven_ability_accum # 单位: m2/s
    else:
        result_dict.data['通风量'] = None
        
    if data_asc_accum is not None:
        data_asc_accum = data_asc_accum.reset_index().to_dict(orient='records')
        result_dict.data['大气自净能力ASC'] = data_asc_accum # 大气自净能力 1e4 km2/a
    else:
        result_dict.data['大气自净能力ASC'] = None
        
    if data_asi_accum is not None:
        data_asi_accum = data_asi_accum.reset_index().to_dict(orient='records')
        result_dict.data['大气自净能力ASI'] = data_asi_accum # 大气自净能力指数 全天大气对污染物总体清除能力 单位: t/(d*km2)
    else:
        result_dict.data['大气自净能力ASI'] = None
    
    # 7.结果保存
    if cfg.INFO.SAVE_RESULT:
        result_dict['csv'] = save_cmadaas_data(data_dir, mon_data=monthly_df)
    
    return result_dict
