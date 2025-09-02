# -*- coding: utf-8 -*-
"""
Created on Thu Feb 22 15:02:21 2024

@author: EDY
"""
import os
import uuid
import pandas as pd
from Utils.config import cfg
from Utils.data_loader_with_threads import get_adtd_data_threads
from Module10.wrapped.light_density import light_density
from Module10.wrapped.light_risk import light_risk
from Module10.wrapped.light_statistics import light_status
from Module10.wrapped.light_disater import get_regional_risk
from Module10.wrapped.light_mfi import light_mfi
from Report.code.Module10.light_report_1 import light_report_1
from Report.code.Module10.light_report_2 import light_report_2
from Utils.get_url_path import save_cmadaas_data

def adtd_data_proccessing(data, years):
    data['Datetime'] = pd.to_datetime(data['Datetime'])
    data.set_index('Datetime', inplace=True)
    data.sort_index(inplace=True)
    data['Lon'] = data['Lon'].astype(float)
    data['Lat'] = data['Lat'].astype(float)
    data.rename(columns={'强度': 'Lit_Current'}, inplace=True)
    data['Year'] = data.index.year
    data['Mon'] = data.index.month
    data['Day'] = data.index.day

    start_year = years.split(',')[0]
    end_year = years.split(',')[1]
    data = data[data.index.year >= int(start_year)]
    data = data[data.index.year <= int(end_year)]

    if 'Unnamed: 0' in data.columns:
        data.drop(['Unnamed: 0'], axis=1, inplace=True)

    return data


def light_statistics_deal(data_json):
    '''
    雷电数据特征分析+电磁强度
    '''
    # 1.参数读取
    date_range = data_json['date_range']
    start_lon = data_json['start_lon']
    start_lat = data_json['start_lat']
    end_lon = data_json['end_lon']
    end_lat = data_json['end_lat']
    point_list = data_json['point_list']

    start_lon = float(start_lon)
    start_lat = float(start_lat)
    end_lon = float(end_lon)
    end_lat = float(end_lat)

    # 2.参数处理
    resolution = 0.005 # 500米
    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    # 3.拼接需要下载的参数
    # if cfg.INFO.READ_LOCAL:
    #     adtd_df = pd.read_csv(cfg.FILES.ADTD)
    #     adtd_df = adtd_data_proccessing(adtd_df)
    # else:
    #     try:
    #         limit = [start_lat, end_lat, start_lon, end_lon]
    #         # limit = [start_lat - 3 / 111, end_lat + 3 / 111, start_lon - 3 / 111, end_lon + 3 / 111]
    #         adtd_df = get_adtd_data_threads(date_range, limit)
    #         adtd_df = adtd_data_proccessing(adtd_df)
    #     except Exception as e:
    #         raise Exception('天擎数据下载或处理失败')
    
    adtd_df = pd.read_csv(cfg.FILES.ADTD)
    adtd_df = adtd_data_proccessing(adtd_df, date_range)

    # 4.结果生成
    result_dict = light_status(adtd_df, start_lon, start_lat, end_lon, end_lat, data_dir)  # 图表统计
    lonlat, save_path_picture_p1 = light_mfi(adtd_df, start_lon, start_lat, end_lon, end_lat, point_list, data_dir)  # 电磁强度
    save_path_picture_p = light_density(adtd_df, start_lon, start_lat, end_lon, end_lat, resolution, point_list, data_dir)  # 地闪密度
    result_dict['电磁'] = dict()
    result_dict['电磁']['result'] = lonlat.to_dict(orient='records')
    result_dict['图片路径']['电磁'] = save_path_picture_p1
    result_dict['图片路径']['地闪密度'] = save_path_picture_p

    try:
        if point_list is not None:
            report_path = light_report_1(result_dict, save_path_picture_p, data_dir, lonlat, save_path_picture_p1)
        else:
            report_path = light_report_1(result_dict, save_path_picture_p, data_dir)
    
        report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
        result_dict['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)

    except Exception as e:
        print(f"报告 发生了错误：{e}")
        result_dict['report'] = None

    # url 替换
    for key, sub_dict in result_dict.items():
        if key == '图片路径':
            try:
                for name, path in sub_dict.items():
                    path = path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)  # 图片容器内转容器外路径
                    sub_dict[name] = path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
            except:
                pass

    if cfg.INFO.SAVE_RESULT:
        result_dict['csv'] = save_cmadaas_data(data_dir, adtd_data=adtd_df)

    return result_dict


def light_risk_deal(data_json):

    # 1.参数读取
    date_range = data_json['date_range']
    start_lon = data_json['start_lon']
    start_lat = data_json['start_lat']
    end_lon = data_json['end_lon']
    end_lat = data_json['end_lat']

    start_lon = float(start_lon)
    start_lat = float(start_lat)
    end_lon = float(end_lon)
    end_lat = float(end_lat)

    # 2.填写数值
    #- 地域风险
    #-- 土壤结构
    Resistivity = data_json['Resistivity']  # 土壤电阻率(数值)
    Vertical_Resistivity = data_json['Vertical_Resistivity']  # 土壤垂直分层(数值)
    Horizontal_Resistivity = data_json['Horizontal_Resistivity']  # 土壤水平分层(数值)
    #-- 地形地貌
    Topography = data_json['Topography']  # 地形地貌(等级)
    #-- 周边环境
    Safe_Distance = data_json['Safe_Distance']  # 安全距离(等级)
    Relative_Height = data_json['Relative_Height']  # 相对高度(等级)
    Electromagnetic = data_json['Electromagnetic']  # 电磁环境(数值)

    #- 承载体风险
    #-- 项目属性
    Function = data_json['Function']  # 使用性质(等级)
    Crew_Size = data_json['Crew_Size']  # 人员数量(数值)
    Impact = data_json['Impact']  # 影响程度(等级)
    #-- 建构住特性
    Cover_Area = data_json['Cover_Area']  #占地面积(数值)
    Material_Structure = data_json['Material_Structure']  # 材料结构(等级)
    Equivalent_Height = data_json['Equivalent_Height']  # 等效高度(数值)
    #-- 电子电气系统
    Electronic_Systems = data_json['Electronic_Systems']  # 电子系统(等级)
    Electrical_Systems = data_json['Electrical_Systems']  # 电气系统(等级)

    # 3.权重设置方式
    Set_Weights = data_json['Set_Weights']  # 1-预设权重；2-人为填写；

    #- 人为填写
    #-- 区域雷击风险
    weight_Lightning_Risk = data_json.get('weight_Lightning_Risk')  # 雷电风险权重
    weight_Geographical_Risk = data_json.get('weight_Geographical_Risk')  # 地域风险权重
    weight_Carrier_Risk = data_json.get('weight_Carrier_Risk')  # 承载体风险权重

    #------ 雷电风险
    weight_Lightning_Density = data_json.get('weight_Lightning_Density')  # 雷击密度权重
    weight_Lightning_Intensity = data_json.get('weight_Lightning_Intensity')  # 雷电流强度权重

    #-- 地域风险
    weight_Soil_Structure = data_json.get('weight_Soil_Structure')  # 土壤结构权重
    weight_Topography = data_json.get('weight_Topography')  # 地形地貌权重
    weight_Environment = data_json.get('weight_Environment')  # 周边环境权重
    #------ 土壤结构
    weight_Resistivity = data_json.get('weight_Resistivity')  # 土壤电阻率权重
    weight_Vertical_Resistivity = data_json.get('weight_Vertical_Resistivity')  # 土壤垂直分层权重
    weight_Horizontal_Resistivity = data_json.get('weight_Horizontal_Resistivity')  # 土壤水平分层权重
    #-------- 周边环境
    weight_Safe_Distance = data_json.get('weight_Safe_Distance')  # 安全距离权重
    weight_Relative_Height = data_json.get('weight_Relative_Height')  # 对高度权重
    weight_Electromagnetic = data_json.get('weight_Electromagnetic')  # 电磁环境权重

    #-- 承载体风险
    weight_Project_Properties = data_json.get('weight_Project_Properties')  # 项目属性权重
    weight_Architectural_Features = data_json.get('weight_Architectural_Features')  # 建筑特征权重
    weight_Electrical_Electronic_Systems = data_json.get('weight_Electrical_Electronic_Systems')  # 电子电气系统权重
    #-------- 项目属性
    weight_Function = data_json.get('weight_Function')  # 使用性质权重
    weight_Crew_Size = data_json.get('weight_Crew_Size')  # 人员数量权重
    weight_Impact = data_json.get('weight_Impact')  # 影响程度
    #-------- 建构住特性
    weight_Cover_Area = data_json.get('weight_Cover_Area')  # 占地面积
    weight_Material_Structure = data_json.get('weight_Material_Structure')  # 材料结构
    weight_Equivalent_Height = data_json.get('weight_Equivalent_Height')  # 等效高度
    #-------- 电子电气系统
    weight_Electronic_Systems = data_json.get('weight_Electronic_Systems')  # 电子系统
    weight_Electrical_Systems = data_json.get('weight_Electrical_Systems')  # 电气系统

    # 2.参数处理
    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    # 3.拼接需要下载的参数
    adtd_df = pd.read_csv(cfg.FILES.ADTD)
    adtd_df = adtd_data_proccessing(adtd_df, date_range)

    # if cfg.INFO.READ_LOCAL:
    #     adtd_df = pd.read_csv(cfg.FILES.ADTD)
    #     adtd_df = adtd_data_proccessing(adtd_df)
    # else:
    #     # 天擎数据下载
    #     try:
    #         limit = [start_lat, end_lat, start_lon, end_lon]
    #         adtd_df = get_adtd_data_threads(date_range, limit)
    #         adtd_df = adtd_data_proccessing(adtd_df)
    #     except Exception as e:
    #         raise Exception('天擎数据下载或处理失败')

    # 6.结果生成
    result_dict, factors = light_risk(start_lon, end_lon, start_lat, end_lat, adtd_df, Resistivity, Vertical_Resistivity, Horizontal_Resistivity, Topography, Safe_Distance, Relative_Height, Electromagnetic, Function, Crew_Size, Impact, Cover_Area,
                                      Material_Structure, Equivalent_Height, Electronic_Systems, Electrical_Systems, Set_Weights, weight_Lightning_Risk, weight_Geographical_Risk, weight_Carrier_Risk, weight_Lightning_Density,
                                      weight_Lightning_Intensity, weight_Soil_Structure, weight_Topography, weight_Environment, weight_Resistivity, weight_Vertical_Resistivity, weight_Horizontal_Resistivity, weight_Safe_Distance,
                                      weight_Relative_Height, weight_Electromagnetic, weight_Project_Properties, weight_Architectural_Features, weight_Electrical_Electronic_Systems, weight_Function, weight_Crew_Size, weight_Impact, weight_Cover_Area,
                                      weight_Material_Structure, weight_Equivalent_Height, weight_Electronic_Systems, weight_Electrical_Systems)

    try:
        report_path = light_report_2(result_dict, factors, data_dir)
        report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
        result_dict['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)

    except Exception as e:
        print(f"报告 发生了错误：{e}")
        result_dict['report'] = None

    if cfg.INFO.SAVE_RESULT:
        result_dict['csv'] = save_cmadaas_data(data_dir, adtd_data=adtd_df)

    return result_dict