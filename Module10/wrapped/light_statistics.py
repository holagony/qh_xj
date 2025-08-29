# -*- coding: utf-8 -*-
"""
Created on Sat May 11 16:51:25 2024

@author: EDY
"""
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from scipy.optimize import curve_fit
from Utils.config import cfg


matplotlib.use('Agg')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


def light_status(data1, start_lon, start_lat, end_lon, end_lat, save_path):
    '''
    ADTD数据统计
    '''
    data1 = data1[(data1['Lon'] > start_lon) & (data1['Lon'] < end_lon) & (data1['Lat'] > start_lat) & (data1['Lat'] < end_lat)]
    data1['num'] = 1

    # 分正闪和负闪
    data11 = data1[data1['Lit_Current'] > 0]
    data12 = data1[data1['Lit_Current'] < 0]
    data21 = data11[['num']]
    data22 = data12[['num']]

    # 数据统计
    #---------- 年统计
    yearly_means_z = data21.resample('Y').sum()
    yearly_means_f = data22.resample('Y').sum()

    yearly_means_combined = pd.concat([yearly_means_z, yearly_means_f], axis=1)
    yearly_means_combined.columns = ['正闪数量', '负闪数量']
    years = yearly_means_combined.index.year.unique()
    
    yearly_means_combined.insert(loc=0, column='年份', value=yearly_means_combined.index.year)
    yearly_means_combined.reset_index(drop=True, inplace=True)
    yearly_means_combined_dict = yearly_means_combined.to_dict(orient='records')

    # 画柱状图
    fig, ax = plt.subplots(figsize=(7, 5))    
    ax.bar(years - 0.1, yearly_means_combined.iloc[:, 1], width=0.2, color='skyblue', label='正闪')
    ax.bar(years + 0.1, yearly_means_combined.iloc[:, 2], width=0.2, color='salmon', label='负闪')
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.grid(axis='x', linestyle='--', alpha=0.7)

    ax.set_xlabel('年份')
    ax.set_ylabel('闪电频次（次）')
    ax.set_xticks(years)
    ax.legend()
    save_path_picture_yearnum = os.path.join(save_path, '年_次数.png')
    plt.savefig(save_path_picture_yearnum, bbox_inches='tight', dpi=200)
    plt.cla()

    #---------- 月统计
    monthly_means_z = data21['num'].groupby(data21.index.month).sum()
    monthly_means_f = data22['num'].groupby(data22.index.month).sum()

    monthly_means_combined = pd.concat([monthly_means_z, monthly_means_f], axis=1)
    monthly_means_combined.columns = ['正闪数量', '负闪数量']
    monthly_means_combined = monthly_means_combined.reindex(range(1, 13))
    monthly_means_combined.fillna(0, inplace=True)
    monthly_means_combined.insert(loc=0, column='月份', value=[str(i)+'月' for i in monthly_means_combined.index])
    months = monthly_means_combined.index.astype(int)
    
    monthly_means_combined.reset_index(drop=True, inplace=True)
    monthly_means_combined_dict = monthly_means_combined.to_dict(orient='records')

    # 画柱状图
    fig, ax = plt.subplots(figsize=(7, 5))    
    ax.bar(months - 0.1, monthly_means_combined.iloc[:, 1], width=0.2, color='skyblue', label='正闪')
    ax.bar(months + 0.1, monthly_means_combined.iloc[:, 2], width=0.2, color='salmon', label='负闪')
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.grid(axis='x', linestyle='--', alpha=0.7)
    ax.set_xlabel('月份')
    ax.set_ylabel('闪电频次（次）')
    ax.legend()
    ax.set_xticks(months)
    save_path_picture_monnum = os.path.join(save_path, '月_次数.png')
    plt.savefig(save_path_picture_monnum, bbox_inches='tight', dpi=200)
    plt.cla()

    #---------- 小时统计
    hourly_means_z = data21['num'].groupby(data21.index.hour).sum()
    hourly_means_f = data22['num'].groupby(data22.index.hour).sum()

    hourly_means_combined = pd.concat([hourly_means_z, hourly_means_f], axis=1)
    hourly_means_combined.columns = ['正闪数量', '负闪数量']
    hourly_means_combined = hourly_means_combined.reindex(range(0, 24))
    hourly_means_combined.fillna(0, inplace=True)
    hours = hourly_means_combined.index
    
    hourly_means_combined.insert(loc=0, column='小时', value=[str(i)+'时' for i in range(0,24)])
    hourly_means_combined.reset_index(drop=True, inplace=True)
    hourly_means_combined_dict = hourly_means_combined.to_dict(orient='records')

    # 绘制柱状图
    fig, ax = plt.subplots(figsize=(7, 5))    
    ax.bar(hours - 0.1, hourly_means_combined.iloc[:, 1], width=0.2, color='skyblue', label='正闪')
    ax.bar(hours + 0.1, hourly_means_combined.iloc[:, 2], width=0.2, color='salmon', label='负闪')
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.grid(axis='x', linestyle='--', alpha=0.7)
    ax.set_xlabel('小时')
    ax.set_ylabel('闪电频次（次）')
    ax.legend()
    ax.set_xticks(hours)
    save_path_picture_hournum = os.path.join(save_path, '小时_次数.png')
    plt.savefig(save_path_picture_hournum, bbox_inches='tight', dpi=200)
    plt.cla()

    #---------- 闪电日数统计
    data_part2 = data1.copy()
    data_part2 = data_part2[['Year', 'Mon', 'Day', 'num', 'Lit_Current']]
    data_part2 = data_part2.drop_duplicates(subset=['Year', 'Mon', 'Day'])

    data_part2_11 = data_part2[data_part2['Lit_Current'] > 0]
    data_part2_12 = data_part2[data_part2['Lit_Current'] < 0]
    hours = hourly_means_combined.index

    # 年统计
    yearly_sum_days_z = data_part2_11['num'].groupby(data_part2_11['Year']).sum()
    yearly_sum_days_z = pd.DataFrame(yearly_sum_days_z)
    yearly_sum_days_f = data_part2_12['num'].groupby(data_part2_12['Year']).sum()
    yearly_sum_days_f = pd.DataFrame(yearly_sum_days_f)
    yearly_sum_days = pd.concat([yearly_sum_days_z, yearly_sum_days_f], axis=1)
    yearly_sum_days.columns = ['正闪日数', '负闪日数']
    years = yearly_sum_days.index
    
    yearly_sum_days.insert(loc=0, column='年份', value=yearly_sum_days.index)
    yearly_sum_days.reset_index(drop=True, inplace=True)
    yearly_sum_days_dict = yearly_sum_days.to_dict(orient='records')

    # 画柱状图
    fig, ax = plt.subplots(figsize=(7, 5))    
    ax.bar(years - 0.1, yearly_sum_days.iloc[:, 1], width=0.2, color='skyblue', label='正闪')
    ax.bar(years + 0.1, yearly_sum_days.iloc[:, 2], width=0.2, color='salmon', label='负闪')
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.grid(axis='x', linestyle='--', alpha=0.7)
    ax.set_xlabel('年份')
    ax.set_ylabel('闪电日数')
    ax.set_xticks(years)
    ax.legend()
    save_path_picture_yearday = os.path.join(save_path, '年_日数.png')
    plt.savefig(save_path_picture_yearday, bbox_inches='tight', dpi=200)
    plt.cla()

    # 月统计
    monthly_sum_days_z = data_part2_11['num'].groupby([data_part2_11['Year'], data_part2_11['Mon']]).sum().round(1)
    monthly_sum_days_z = pd.DataFrame(monthly_sum_days_z)
    monthly_sum_days_z.reset_index(inplace=True)
    monthly_mean_days_z = monthly_sum_days_z['num'].groupby(monthly_sum_days_z['Mon']).mean().round(1)
    monthly_mean_days_z = pd.DataFrame(monthly_mean_days_z)

    monthly_sum_days_f = data_part2_12['num'].groupby([data_part2_12['Year'], data_part2_12['Mon']]).sum().round(1)
    monthly_sum_days_f = pd.DataFrame(monthly_sum_days_f)
    monthly_sum_days_f.reset_index(inplace=True)
    monthly_mean_days_f = monthly_sum_days_f['num'].groupby(monthly_sum_days_f['Mon']).mean().round(1)
    monthly_mean_days_f = pd.DataFrame(monthly_mean_days_f)
    monthly_mean_days = pd.concat([monthly_mean_days_z, monthly_mean_days_f], axis=1)
    monthly_mean_days.columns = ['正闪日数', '负闪日数']    
    monthly_mean_days = monthly_mean_days.reindex(range(1, 13))
    monthly_mean_days.fillna(0, inplace=True)
    months = monthly_mean_days.index
    
    monthly_mean_days.insert(loc=0, column='月份', value=[str(i)+'月' for i in range(1,13)])
    monthly_mean_days.reset_index(drop=True, inplace=True)
    monthly_mean_days_dict = monthly_mean_days.to_dict(orient='records')
    
    #-- 画柱状图
    fig, ax = plt.subplots(figsize=(7, 5))    
    ax.bar(months - 0.1, monthly_mean_days.iloc[:, 1], width=0.2, color='skyblue', label='正闪')
    ax.bar(months + 0.1, monthly_mean_days.iloc[:, 2], width=0.2, color='salmon', label='负闪')
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.grid(axis='x', linestyle='--', alpha=0.7)

    ax.set_xlabel('月')
    ax.set_ylabel('闪电日数')
    ax.set_xticks(months)
    ax.legend()
    save_path_picture_monday = os.path.join(save_path, '月_日数.png')
    plt.savefig(save_path_picture_monday, bbox_inches='tight', dpi=200)
    plt.cla()

    # 雷电流参数
    Lit_Current = np.array(data1['Lit_Current'])
    Lit_Current_abs = np.sort(np.abs(Lit_Current))
    Lit_Current_abs = Lit_Current_abs[~np.isnan(Lit_Current_abs)]
    p = 1 - np.arange(1, len(Lit_Current_abs) + 1) / len(Lit_Current_abs)

    def light_model(x, a, b):
        return 1 / (1 + (x / a)**b)

    params, _ = curve_fit(light_model, Lit_Current_abs, p)

    # 输出拟合参数
    a_fit, b_fit = params

    #--绘图
    fig, ax = plt.subplots(figsize=(7, 5))    
    ax.scatter(Lit_Current_abs, p, color='blue', label='原始数据', s=2)
    ax.plot(Lit_Current_abs, light_model(Lit_Current_abs, a_fit, b_fit), color='red', label='拟合线')
    ax.legend()
    ax.set_xlabel('雷电流强度（kA）')
    ax.set_ylabel('累计概率（p）')
    save_path_picture_p = os.path.join(save_path, '累积概率曲线.png')
    plt.savefig(save_path_picture_p, bbox_inches='tight', dpi=200)
    plt.cla()
    plt.close('all')

    # 结果保存
    result = dict()
    result['累积概率曲线'] = dict()
    result['累积概率曲线']['a'] = a_fit.round(3)
    result['累积概率曲线']['b'] = b_fit.round(3)

    result['次数统计'] = dict()
    result['次数统计']['年'] = yearly_means_combined_dict
    result['次数统计']['月'] = monthly_means_combined_dict
    result['次数统计']['小时'] = hourly_means_combined_dict
    
    result['天数统计'] = dict()
    result['天数统计']['年'] = yearly_sum_days_dict
    result['天数统计']['月'] = monthly_mean_days_dict

    result['图片路径'] = dict()
    result['图片路径']['年次数'] = save_path_picture_yearnum
    result['图片路径']['月次数'] = save_path_picture_monnum
    result['图片路径']['小时次数'] = save_path_picture_hournum
    result['图片路径']['年天数'] = save_path_picture_yearday
    result['图片路径']['月天数'] = save_path_picture_monday
    result['图片路径']['累积概率曲线'] = save_path_picture_p

    return result


if __name__ == '__main__':
    
    def adtd_data_proccessing(data):
        data = data[data['Lit_Prov']=='青海省']
        data = data[['Lat', 'Lon', 'Year', 'Mon', 'Day', 'Hour', 'Min', 'Second','Lit_Current']]
        time = {"Year": data["Year"], "Month": data["Mon"], "Day": data["Day"], "Hour": data["Hour"], "Minute": data["Min"], "Second": data["Second"]}
        data['Datetime'] = pd.to_datetime(time)
        data.set_index('Datetime', inplace=True)
        data.sort_index(inplace=True)

        if 'Unnamed: 0' in data.columns:
            data.drop(['Unnamed: 0'], axis=1, inplace=True)

        return data

    start_lon = 100.8
    start_lat = 36.2
    end_lon = 101.9
    end_lat = 37.5
    resolution = 0.005
    path = cfg.FILES.ADTD
    df = pd.read_csv(path)
    df = adtd_data_proccessing(df)
    save_path = r'D:\Project\3_项目\2_气候评估和气候可行性论证\qhkxxlz\Report\report\Modules10'
    result = light_status(df, start_lon, start_lat, end_lon, end_lat, save_path)

    
    
