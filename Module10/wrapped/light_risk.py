# -*- coding: utf-8 -*-
"""
Created on Mon May 13 13:21:10 2024

@author: EDY
区域雷电风险评估计算
"""
import pandas as pd
from Module10.wrapped.FCE import calc_lightning_risk
from Utils.config import cfg
import numpy as np


def adtd(data, lon_min, lon_max, lat_min, lat_max):

    adtd = data[(data['Lon'] > lon_min) & (data['Lon'] < lon_max) & (data['Lat'] > lat_min) & (data['Lat'] < lat_max)]

    # 计算强度
    strength = np.abs(adtd['Lit_Current']).mean()

    # 计算密度
    start_index = adtd.index.sort_values()[0]
    end_index = adtd.index.sort_values()[-1]

    # 计算时间差
    time_difference = end_index - start_index

    # 使用 pandas 的 Timedelta 对象计算年份差
    # 注意：这里假设一年有 365.25 天，以考虑到闰年
    num_year = time_difference / pd.Timedelta(days=365.25)

    # 获取评估区域面积
    x = (lon_max - lon_min) * 111
    y = (lat_max - lat_min) * 111
    s = x * y
    density = len(adtd) / (s * num_year)

    return strength, density


def light_risk(Min_Lon, Max_Lon, Min_Lat, Max_Lat, data, Resistivity, Vertical_Resistivity, Horizontal_Resistivity, Topography, Safe_Distance, Relative_Height, Electromagnetic, Function, Crew_Size, Impact, Cover_Area, Material_Structure,
               Equivalent_Height, Electronic_Systems, Electrical_Systems, Set_Weights, weight_Lightning_Risk, weight_Geographical_Risk, weight_Carrier_Risk, weight_Lightning_Density, weight_Lightning_Intensity, weight_Soil_Structure,
               weight_Topography, weight_Environment, weight_Resistivity, weight_Vertical_Resistivity, weight_Horizontal_Resistivity, weight_Safe_Distance, weight_Relative_Height, weight_Electromagnetic, weight_Project_Properties,
               weight_Architectural_Features, weight_Electrical_Electronic_Systems, weight_Function, weight_Crew_Size, weight_Impact, weight_Cover_Area, weight_Material_Structure, weight_Equivalent_Height, weight_Electronic_Systems,
               weight_Electrical_Systems):

    # 数据输入处理
    # 计算因子数据处理
    Min_Lon = float(Min_Lon)
    Max_Lon = float(Max_Lon)
    Min_Lat = float(Min_Lat)
    Max_Lat = float(Max_Lat)

    Topography = int(Topography[:-1])
    Safe_Distance = int(Safe_Distance[:-1])
    Relative_Height = int(Relative_Height[:-1])
    Function = int(Function[:-1])
    Impact = int(Impact[:-1])
    Material_Structure = int(Material_Structure[:-1])
    Electronic_Systems = int(Electronic_Systems[:-1])
    Electrical_Systems = int(Electrical_Systems[:-1])

    factors = pd.DataFrame(columns=["value"])
    factors.loc["土壤电阻率"] = Resistivity
    factors.loc["土壤垂直分层"] = Vertical_Resistivity
    factors.loc["土壤水平分层"] = Horizontal_Resistivity
    factors.loc["地形地貌"] = Topography
    factors.loc["安全距离"] = Safe_Distance
    factors.loc["相对高度"] = Relative_Height
    factors.loc["电磁环境"] = Electromagnetic
    factors.loc["使用性质"] = Function
    factors.loc["人员数量"] = Crew_Size
    factors.loc["影响程度"] = Impact
    factors.loc["占地面积"] = Cover_Area
    factors.loc["材料结构"] = Material_Structure
    factors.loc["等效高度"] = Equivalent_Height
    factors.loc["电子系统"] = Electronic_Systems
    factors.loc["电气系统"] = Electrical_Systems

    strength, density = adtd(data, Min_Lon, Max_Lon, Min_Lat, Max_Lat)
    factors.loc["雷电流强度"] = strength
    factors.loc["雷击密度"] = density

    # 权重的确定 1-预设权重；2-人为填写
    if Set_Weights == 2:
        weights = pd.DataFrame(columns=["weights"])
        weights.loc["雷电风险"] = weight_Lightning_Risk
        weights.loc["地域风险"] = weight_Geographical_Risk
        weights.loc["承载体风险"] = weight_Carrier_Risk
        weights.loc["雷击密度"] = weight_Lightning_Density
        weights.loc["雷电流强度"] = weight_Lightning_Intensity
        weights.loc["土壤结构"] = weight_Soil_Structure
        weights.loc["地形地貌"] = weight_Topography
        weights.loc["周边环境"] = weight_Environment
        weights.loc["项目属性"] = weight_Project_Properties
        weights.loc["建筑特征"] = weight_Architectural_Features
        weights.loc["电子电气系统"] = weight_Electrical_Electronic_Systems
        weights.loc["土壤电阻率"] = weight_Resistivity
        weights.loc["土壤垂直分层"] = weight_Vertical_Resistivity
        weights.loc["土壤水平分层"] = weight_Horizontal_Resistivity
        weights.loc["安全距离"] = weight_Safe_Distance
        weights.loc["相对高度"] = weight_Relative_Height
        weights.loc["电磁环境"] = weight_Electromagnetic
        weights.loc["使用性质"] = weight_Function
        weights.loc["人员数量"] = weight_Crew_Size
        weights.loc["影响程度"] = weight_Impact
        weights.loc["占地面积"] = weight_Cover_Area
        weights.loc["材料结构"] = weight_Material_Structure
        weights.loc["等效高度"] = weight_Equivalent_Height
        weights.loc["电子系统"] = weight_Electronic_Systems
        weights.loc["电气系统"] = weight_Electrical_Systems
        weights_dict = weights.to_dict(orient="dict")["weights"]

    elif Set_Weights == 1:
        Parameters_File = cfg.FILES.ADTD_PARAM
        weights = pd.read_csv(Parameters_File, index_col=0)
        weights_dict = weights.to_dict(orient="dict")['weights']

    # 数据计算
    factors["type"] = [0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0]
    factors = factors.to_dict(orient="index")

    # 得到计算结果
    g, risk, degree_df, level1_norm = calc_lightning_risk(factors, weights_dict)
    # print()
    # print("最终结果:")
    # print("经过规范方法计算得到该评估区域的雷电灾害风险值R=" + str(g[0]) + ", 对应" + "[" + risk + "]")

    # 计算结果保存
    result = pd.concat([degree_df, weights], axis=1)
    result.columns = ["I级", "II级", "III级", "IV级", "V级", "相应的权重"]
    result.insert(loc=0, column='类别', value=result.index)
    result.reset_index(drop=True,inplace=True)

    resultz = dict()
    resultz['雷电灾害风险值'] = g[0]
    resultz['雷电灾害风险等级'] = risk
    resultz['各因子隶属度结果'] = result.to_dict(orient='records')
    resultz['区域雷电灾害风险'] = level1_norm.to_dict(orient='records')

    return resultz, factors


if __name__ == '__main__':

    def adtd_data_proccessing(data):
        data = data[data['Lit_Prov'] == '青海省']
        data = data[['Lat', 'Lon', 'Year', 'Mon', 'Day', 'Hour', 'Min', 'Second', 'Lit_Current']]
        time = {"Year": data["Year"], "Month": data["Mon"], "Day": data["Day"], "Hour": data["Hour"], "Minute": data["Min"], "Second": data["Second"]}
        data['Datetime'] = pd.to_datetime(time)
        data.set_index('Datetime', inplace=True)
        data.sort_index(inplace=True)

        if 'Unnamed: 0' in data.columns:
            data.drop(['Unnamed: 0'], axis=1, inplace=True)

        return data

    #- 雷电风险
    Min_Lon = 93
    Max_Lon = 98
    Min_Lat = 33
    Max_Lat = 38

    filename = r'C:/Users/MJY/Desktop/adtd.csv'
    data = pd.read_csv(filename)
    data = adtd_data_proccessing(data)

    #- 地域风险
    #-- 土壤结构
    Resistivity = 38.57  # 土壤电阻率(数值)
    Vertical_Resistivity = 18  # 土壤垂直分层(数值)
    Horizontal_Resistivity = 30  # 土壤水平分层(数值)
    #-- 地形地貌
    Topography = '4级'  # 地形地貌(等级)
    #-- 周边环境
    Safe_Distance = '1级'  # 安全距离(等级)
    Relative_Height = '4级'  # 相对高度(等级)
    Electromagnetic = 1.12  # 电磁环境(数值)

    #- 承载体风险
    #-- 项目属性
    Function = '4级'  # 使用性质(等级)
    Crew_Size = 30000  # 人员数量(数值)
    Impact = '1级'  # 影响程度(等级)
    #-- 建构住特性
    Cover_Area = 18000  # 占地面积(数值)
    Material_Structure = '4级'  # 材料结构(等级)
    Equivalent_Height = 40  # 等效高度(数值)
    #-- 电子电气系统
    Electronic_Systems = '3级'  # 电子系统(等级)
    Electrical_Systems = '3级'  # 电气系统(等级)

    # 权重设置方式
    Set_Weights = 1  # 1-预设权重；2-人为填写；

    #- 预设权重
    # Parameters_File=cfg['Module_light']['parameters']

    #- 人为填写
    #-- 区域雷击风险
    weight_Lightning_Risk = 5  # 雷电风险权重
    weight_Geographical_Risk = 1  # 地域风险权重
    weight_Carrier_Risk = 3  # 承载体风险权重

    #------ 雷电风险
    weight_Lightning_Density = 3  # 雷击密度权重
    weight_Lightning_Intensity = 1  # 雷电流强度权重

    #-- 地域风险
    weight_Soil_Structure = 2  # 土壤结构权重
    weight_Topography = 1  # 地形地貌权重
    weight_Environment = 5  # 周边环境权重
    #------ 土壤结构
    weight_Resistivity = 5  # 土壤电阻率权重
    weight_Vertical_Resistivity = 1  # 土壤垂直分层权重
    weight_Horizontal_Resistivity = 1  # 土壤水平分层权重
    #-------- 周边环境
    weight_Safe_Distance = 1  # 安全距离权重
    weight_Relative_Height = 1  # 对高度权重
    weight_Electromagnetic = 1  # 电磁环境权重

    #-- 承载体风险
    weight_Project_Properties = 3  # 项目属性权重
    weight_Architectural_Features = 2  # 建筑特征权重
    weight_Electrical_Electronic_Systems = 1  # 电子电气系统权重
    #-------- 项目属性
    weight_Function = 1  # 使用性质权重
    weight_Crew_Size = 3  # 人员数量权重
    weight_Impact = 1  # 影响程度
    #-------- 建构住特性
    weight_Cover_Area = 2  # 占地面积
    weight_Material_Structure = 3  # 材料结构
    weight_Equivalent_Height = 1  # 等效高度
    #-------- 电子电气系统
    weight_Electronic_Systems = 1  # 电子系统
    weight_Electrical_Systems = 2  # 电气系统

    result, factors = light_risk(Min_Lon, Max_Lon, Min_Lat, Max_Lat, data, Resistivity, Vertical_Resistivity, Horizontal_Resistivity, Topography, Safe_Distance, Relative_Height, Electromagnetic, Function, Crew_Size, Impact, Cover_Area,
                                 Material_Structure, Equivalent_Height, Electronic_Systems, Electrical_Systems, Set_Weights, weight_Lightning_Risk, weight_Geographical_Risk, weight_Carrier_Risk, weight_Lightning_Density, weight_Lightning_Intensity,
                                 weight_Soil_Structure, weight_Topography, weight_Environment, weight_Resistivity, weight_Vertical_Resistivity, weight_Horizontal_Resistivity, weight_Safe_Distance, weight_Relative_Height, weight_Electromagnetic,
                                 weight_Project_Properties, weight_Architectural_Features, weight_Electrical_Electronic_Systems, weight_Function, weight_Crew_Size, weight_Impact, weight_Cover_Area, weight_Material_Structure, weight_Equivalent_Height,
                                 weight_Electronic_Systems, weight_Electrical_Systems)
