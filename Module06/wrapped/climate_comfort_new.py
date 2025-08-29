import os
import glob
import json
import simplejson
import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_processing import daily_data_processing


def I_BC_calculation(input_df):
    '''
    计算人体舒适度指数 I_BC
    输出：
    人体舒适度指数日变化
    '''
    sample_data = input_df[['TEM_Avg', 'RHU_Avg', 'WIN_S_2mi_Avg']]
    I_BC = (1.8 * sample_data['TEM_Avg'] + 32) - 0.55 * (1 - sample_data['RHU_Avg']) * (1.8 * sample_data['TEM_Avg'] - 26) - (3.2 * sample_data['WIN_S_2mi_Avg'].apply(np.sqrt))
    I_BC = round(I_BC, 0)
    I_BC = I_BC.to_frame()
    I_BC.columns = ['人体舒适度指数']

    return I_BC


def I_BC_stats(I_BC):
    '''
    基于人体舒适度指数 I_BC，进行统计
    
    输出：
    1.平均舒适指数 (逐年/逐月/累年各月)
    2.舒适及以上日数 (逐年/逐月)
    3.各等级日数统计 (逐年/逐月)
    4.规范统计
    '''
    # 添加日舒适指数对应等级
    I_BC['等级'] = pd.cut(I_BC['人体舒适度指数'], bins=[-np.inf, 25, 38, 50, 58, 70, 75, 79, 85, 89, np.inf], labels=list(range(1, 11)))
    I_BC['等级'] = I_BC['等级'].astype(int)

    # 1-1 平均舒适指数(逐年)
    I_BC_yearly = I_BC['人体舒适度指数'].resample('1A', closed='right', label='right').mean().round(0)  # 年平均
    I_BC_yearly = I_BC_yearly.to_frame()
    I_BC_yearly.insert(loc=0, column='年份', value=I_BC_yearly.index.year)
    I_BC_yearly.reset_index(drop=True, inplace=True)

    # 1-2 平均舒适指数(逐月)
    I_BC_monthly = I_BC['人体舒适度指数'].resample('1M', closed='right', label='right').mean().round(0)  # 月平均
    I_BC_monthly = I_BC_monthly.to_frame()
    I_BC_monthly.insert(loc=0, column='年份', value=I_BC_monthly.index.strftime('%Y-%m'))
    I_BC_monthly.reset_index(drop=True, inplace=True)

    # 1-3 平均舒适指数(累年各月)
    I_BC_accum = []
    for i in range(1, 13):
        month_i_mean = I_BC.loc[I_BC.index.month == i, '人体舒适度指数'].mean()
        I_BC_accum.append(month_i_mean)

    I_BC_accum = pd.DataFrame(I_BC_accum).round(0)
    I_BC_accum.columns = ['人体舒适度指数']
    I_BC_accum.insert(loc=0, column='日期', value=[str(i) + '月' for i in range(1, 13)])

    # 2-1 舒适及以上日数(逐年) 对应等级4/5/6的日数
    I_BC_sample = I_BC[I_BC['等级'].isin([4, 5, 6])]
    cozy_level_yearly = I_BC_sample['等级'].resample('1A', closed='right', label='right').apply(lambda x: len(x))
    cozy_level_yearly = cozy_level_yearly.to_frame()
    cozy_level_yearly.columns = ['舒适及以上等级日数']
    cozy_level_yearly.insert(loc=0, column='年份', value=cozy_level_yearly.index.year)
    cozy_level_yearly.reset_index(drop=True, inplace=True)

    # 2-2 舒适及以上日数(逐月) 对应等级4/5/6的日数
    I_BC_sample = I_BC[I_BC['等级'].isin([4, 5, 6])]
    cozy_level_monthly = I_BC_sample['等级'].resample('1M', closed='right', label='right').apply(lambda x: len(x))
    cozy_level_monthly = cozy_level_monthly.to_frame()
    cozy_level_monthly.columns = ['舒适及以上等级日数']
    cozy_level_monthly.insert(loc=0, column='年份', value=cozy_level_monthly.index.strftime('%Y-%m'))
    cozy_level_monthly.reset_index(drop=True, inplace=True)

    # 3-1 各等级日数统计(逐年)
    level_yearly = I_BC.groupby([I_BC.index.year])['等级'].value_counts().unstack(fill_value=0)
    level_yearly.columns = ['level_' + str(col) for col in level_yearly.columns]
    level_yearly.insert(loc=0, column='年', value=level_yearly.index.get_level_values(0))
    level_yearly.reset_index(drop=True, inplace=True)

    # 3-2 各等级日数统计(逐月)
    level_monthly = I_BC.groupby([I_BC.index.year, I_BC.index.month])['等级'].value_counts().unstack(fill_value=0)
    level_monthly.columns = ['level_' + str(col) for col in level_monthly.columns]
    level_monthly.insert(loc=0, column='月', value=level_monthly.index.get_level_values(1))
    level_monthly.insert(loc=0, column='年', value=level_monthly.index.get_level_values(0))
    level_monthly.reset_index(drop=True, inplace=True)

    # 4-1 历年最舒适(等级5)的月数
    def sample_comfortable1(x):
        x = np.array(x)
        values = np.where((x >= 59) & (x <= 70), 1, 0)
        return np.sum(values)

    monthly = I_BC['人体舒适度指数'].resample('1M', closed='right', label='right').mean().round(0)
    comfortable_months1 = monthly.resample('1A', closed='right', label='right').apply(sample_comfortable1).to_frame()
    comfortable_months1.columns = ['最舒适等级的月数']
    comfortable_months1.insert(loc=0, column='年', value=comfortable_months1.index.year)
    comfortable_months1.reset_index(drop=True, inplace=True)

    # 4-2 历年舒适及以上(等级4/5/6)的月数
    def sample_comfortable2(x):
        x = np.array(x)
        values = np.where((x >= 51) & (x <= 75), 1, 0)
        return np.sum(values)

    comfortable_months2 = monthly.resample('1A', closed='right', label='right').apply(sample_comfortable2).to_frame()
    comfortable_months2.columns = ['舒适及以上等级的月数']
    comfortable_months2.insert(loc=0, column='年', value=comfortable_months2.index.year)
    comfortable_months2.reset_index(drop=True, inplace=True)

    # 4-3 历年平均人体舒适指数对应的等级
    comfort_level_yearly = I_BC['等级'].resample('1A', closed='right', label='right').mean().round(0).to_frame()
    comfort_level_yearly.columns = ['平均人体舒适度等级']
    comfort_level_yearly.insert(loc=0, column='年', value=comfort_level_yearly.index.year)
    comfort_level_yearly.reset_index(drop=True, inplace=True)

    # 4-4 累年各月平均人体舒适指数对应的等级
    comfort_level_accum = []
    for i in range(1, 13):
        month_i_mean = I_BC.loc[I_BC.index.month == i, '等级'].mean()
        comfort_level_accum.append(month_i_mean)

    comfort_level_accum = pd.DataFrame(comfort_level_accum).round(0)
    comfort_level_accum.columns = ['累年各月平均人体舒适指数等级']
    comfort_level_accum.insert(loc=0, column='日期', value=[str(i) + '月' for i in range(1, 13)])
    comfort_level_accum.reset_index(drop=True, inplace=True)

    # 保存字典
    result = edict()
    result['平均舒适指数'] = edict()
    result['平均舒适指数']['逐年'] = I_BC_yearly.round(1).to_dict(orient='records')
    result['平均舒适指数']['逐月'] = I_BC_monthly.round(1).to_dict(orient='records')
    result['平均舒适指数']['累年各月'] = I_BC_accum.round(1).to_dict(orient='records')

    result['舒适及以上日数'] = edict()
    result['舒适及以上日数']['逐年'] = cozy_level_yearly.round(1).to_dict(orient='records')
    result['舒适及以上日数']['逐月'] = cozy_level_monthly.round(1).to_dict(orient='records')

    result['各等级日数统计'] = edict()
    result['各等级日数统计']['逐年'] = level_yearly.round(1).to_dict(orient='records')
    result['各等级日数统计']['逐月'] = level_monthly.round(1).to_dict(orient='records')

    result['规范统计'] = edict()
    result['规范统计']['历年最舒适(等级5)的月数'] = comfortable_months1.round(1).to_dict(orient='records')
    result['规范统计']['历年舒适及以上(等级4/5/6)的月数'] = comfortable_months2.round(1).to_dict(orient='records')
    result['规范统计']['历年平均人体舒适指数等级'] = comfort_level_yearly.round(1).to_dict(orient='records')
    result['规范统计']['累年各月平均人体舒适指数等级'] = comfort_level_accum.round(1).to_dict(orient='records')

    return result, comfortable_months1, comfortable_months2


def I_HC_calculation(input_df):
    '''
    计算气候度假指数 I_HC
    输出：
    气候度假指数日变化
    '''
    sample_data = input_df[['TEM_Avg', 'TEM_Max', 'RHU_Avg', 'WIN_S_2mi_Avg', 'PRE_Time_2020', 'CLO_Cov_Avg']]

    # 计算有效温度T_E 以及有效温度分值ST_E
    def sample_tem_score(x):
        if (x >= 23) & (x <= 25):
            x = 10
        elif ((x >= 20) & (x <= 22)) ^ (x == 26):
            x = 9
        elif (x >= 27) & (x <= 28):
            x = 8
        elif ((x >= 18) & (x <= 19)) ^ ((x >= 29) & (x <= 30)):
            x = 7
        elif ((x >= 15) & (x <= 17)) ^ ((x >= 31) & (x <= 32)):
            x = 6
        elif ((x >= 11) & (x <= 14)) ^ ((x >= 33) & (x <= 34)):
            x = 5
        elif ((x >= 7) & (x <= 10)) ^ ((x >= 35) & (x <= 36)):
            x = 4
        elif (x >= 0) & (x <= 6):
            x = 3
        elif ((x >= -5) & (x <= -1)) ^ ((x >= 37) & (x <= 39)):
            x = 2
        elif x < -5:
            x = 1
        elif x > 39:
            x = 0
        return x

    T_E = sample_data['TEM_Max'] - 0.55 * (1 - sample_data['RHU_Avg']) * (sample_data['TEM_Max'] - 14.4)
    T_E = round(T_E, 0)
    ST_E = T_E.apply(sample_tem_score)  # 直接apply()对应的是逐行数据

    # 计算总云量分值SC
    def sample_cloud_score(x):
        if (x >= 11) & (x <= 20):
            x = 10
        elif ((x >= 1) & (x <= 10)) ^ ((x >= 21) & (x <= 30)):
            x = 9
        elif (x == 0) ^ ((x >= 31) & (x <= 40)):
            x = 8
        elif (x >= 41) & (x <= 50):
            x = 7
        elif (x >= 51) & (x <= 60):
            x = 6
        elif (x >= 61) & (x <= 70):
            x = 5
        elif (x >= 71) & (x <= 80):
            x = 4
        elif (x >= 81) & (x <= 90):
            x = 3
        elif x > 90:
            x = 2
        return x

    SC = round(sample_data['CLO_Cov_Avg'], 0)
    SC = SC.apply(sample_cloud_score)

    # 计算日降水量分值SR
    def sample_pre_score(x):
        if x == 0:
            x = 10
        elif (x > 0) & (x < 3):
            x = 9
        elif (x >= 3) & (x <= 5):
            x = 8
        elif (x >= 6) & (x <= 8):
            x = 5
        elif (x >= 9) & (x <= 12):
            x = 2
        elif (x > 12) & (x <= 25):
            x = 0
        elif x > 25:
            x = -1
        return x

    SR = round(sample_data['PRE_Time_2020'], 0)
    SR = SR.apply(sample_pre_score)

    # 计算日平均风速分值SV
    def sample_win_score(x):
        if (x >= 1) & (x <= 9):
            x = 10
        elif (x >= 10) & (x <= 19):
            x = 9
        elif ((x >= 20) & (x <= 29)) ^ (x == 0):
            x = 8
        elif (x >= 30) & (x <= 39):
            x = 6
        elif (x >= 40) & (x <= 49):
            x = 3
        elif (x >= 50) & (x <= 70):
            x = 0
        elif x > 70:
            x = -10
        return x

    SV = round(sample_data['WIN_S_2mi_Avg'] * 3.6, 0)  # 1米/秒(米每秒) = 3.6千米/时(千米每小时)
    SV = SV.apply(sample_win_score)

    # 在得到ST_E/SC/SR/SV后，计算每日的气候度假指数I_HC
    I_HC = (4 * ST_E) + (2 * SC) + (3 * SR + SV)
    I_HC = round(I_HC, 0)
    I_HC = I_HC.to_frame()
    I_HC.columns = ['气候度假指数']

    return I_HC


def I_HC_stats(I_HC):
    '''
    基于气候度假指数 I_HC，进行统计
    
    输出：
    1.平均气候度假指数 (逐年/逐月/累年各月)
    2.适宜及以上日数 (逐年/逐月)
    3.各等级日数统计 (逐年/逐月)
    4.规范统计(规范/原型要求)
    '''
    # 添加日气候度假指数对应等级
    I_HC['等级'] = pd.cut(I_HC['气候度假指数'], bins=[-np.inf, 19, 29, 39, 49, 59, 69, 79, 89, np.inf], labels=list(range(1, 10)))
    I_HC['等级'] = I_HC['等级'].astype(int)

    # 1-1 平均气候度假指数(逐年)
    I_HC_yearly = I_HC['气候度假指数'].resample('1A', closed='right', label='right').mean().round(0)  # 年平均
    I_HC_yearly = I_HC_yearly.to_frame()
    I_HC_yearly.insert(loc=0, column='年份', value=I_HC_yearly.index.year)
    I_HC_yearly.reset_index(drop=True, inplace=True)

    # 1-2 平均气候度假指数(逐月)
    I_HC_monthly = I_HC['气候度假指数'].resample('1M', closed='right', label='right').mean().round(0)  # 月平均
    I_HC_monthly = I_HC_monthly.to_frame()
    I_HC_monthly.insert(loc=0, column='年份', value=I_HC_monthly.index.strftime('%Y-%m'))
    I_HC_monthly.reset_index(drop=True, inplace=True)

    # 1-3 平均气候度假指数(累年各月)
    I_HC_accum = []
    for i in range(1, 13):
        month_i_mean = I_HC.loc[I_HC.index.month == i, '气候度假指数'].mean()
        I_HC_accum.append(month_i_mean)

    I_HC_accum = pd.DataFrame(I_HC_accum).round(0)
    I_HC_accum.columns = ['气候度假指数']
    I_HC_accum.insert(loc=0, column='日期', value=[str(i) + '月' for i in range(1, 13)])

    # 2-1 适宜及以上日数(逐年) 对应等级6~9的日数
    I_HC_sample = I_HC[I_HC['等级'].isin([6, 7, 8, 9])]
    cozy_level_yearly = I_HC_sample['等级'].resample('1A', closed='right', label='right').apply(lambda x: len(x))
    cozy_level_yearly = cozy_level_yearly.to_frame()
    cozy_level_yearly.columns = ['适宜及以上等级日数']
    cozy_level_yearly.insert(loc=0, column='年份', value=cozy_level_yearly.index.year)
    cozy_level_yearly.reset_index(drop=True, inplace=True)

    # 2-2 适宜及以上日数(逐月) 对应等级6~9的日数
    cozy_level_monthly = I_HC_sample['等级'].resample('1M', closed='right', label='right').apply(lambda x: len(x))
    cozy_level_monthly = cozy_level_monthly.to_frame()
    cozy_level_monthly.columns = ['适宜及以上等级日数']
    cozy_level_monthly.insert(loc=0, column='年份', value=cozy_level_monthly.index.strftime('%Y-%m'))
    cozy_level_monthly.reset_index(drop=True, inplace=True)

    # 3-1 各等级日数统计(逐年)
    level_yearly = I_HC.groupby([I_HC.index.year])['等级'].value_counts().unstack(fill_value=0)
    level_yearly.columns = ['level_' + str(col) for col in level_yearly.columns]
    level_yearly.insert(loc=0, column='年', value=level_yearly.index.get_level_values(0))
    level_yearly.reset_index(drop=True, inplace=True)

    # 3-2 各等级日数统计(逐月)
    level_monthly = I_HC.groupby([I_HC.index.year, I_HC.index.month])['等级'].value_counts().unstack(fill_value=0)
    level_monthly.columns = ['level_' + str(col) for col in level_monthly.columns]
    level_monthly.insert(loc=0, column='月', value=level_monthly.index.get_level_values(1))
    level_monthly.insert(loc=0, column='年', value=level_monthly.index.get_level_values(0))
    level_monthly.reset_index(drop=True, inplace=True)

    # 4-1 历年适宜以上等级的月数 (对应等级6~97，val:60~np.inf)
    def sample_comfortable(x):
        x = np.array(x)
        values = np.where(x >= 60, 1, 0)
        return np.sum(values)

    monthly = I_HC['气候度假指数'].resample('1M', closed='right', label='right').mean().round(0)
    comfortable_months = monthly.resample('1A', closed='right', label='right').apply(sample_comfortable).to_frame()
    comfortable_months.columns = ['适宜以上等级的月数']
    comfortable_months.insert(loc=0, column='年', value=comfortable_months.index.year)
    comfortable_months.reset_index(drop=True, inplace=True)

    # 4-2 历年平均气候度假指数对应的等级
    comfort_level_yearly = I_HC['等级'].resample('1A', closed='right', label='right').mean().round(0).to_frame()
    comfort_level_yearly.columns = ['平均气候度假指数']
    comfort_level_yearly.insert(loc=0, column='年', value=comfort_level_yearly.index.year)
    comfort_level_yearly.reset_index(drop=True, inplace=True)

    # 4-3 累年各月平均气候度假指数对应的等级
    comfort_level_accum = []
    for i in range(1, 13):
        month_i_mean = I_HC.loc[I_HC.index.month == i, '等级'].mean()
        comfort_level_accum.append(month_i_mean)

    comfort_level_accum = pd.DataFrame(comfort_level_accum).round(0)
    comfort_level_accum.columns = ['累年各月平均气候度假指数等级']
    comfort_level_accum.insert(loc=0, column='日期', value=[str(i) + '月' for i in range(1, 13)])
    comfort_level_accum.reset_index(drop=True, inplace=True)

    # 4-4 累年各月平均气候度假适宜日数
    def sample_comfortable_days(x):
        x = np.array(x)
        values = np.where(x >= 60, 1, 0)
        return np.sum(values)

    comfort_days_monthly = I_HC['气候度假指数'].resample('1M', closed='right', label='right').apply(sample_comfortable_days)
    comfort_days_accum = []
    for i in range(1, 13):
        month_i_mean = comfort_days_monthly[comfort_days_monthly.index.month == i].mean()
        comfort_days_accum.append(month_i_mean)

    comfort_days_accum = pd.DataFrame(comfort_days_accum).round(0)
    comfort_days_accum.columns = ['累年各月平均气候度假适宜日数']
    comfort_days_accum.insert(loc=0, column='日期', value=[str(i) + '月' for i in range(1, 13)])

    # 保存字典
    result = edict()
    result['平均气候度假指数'] = edict()
    result['平均气候度假指数']['逐年'] = I_HC_yearly.round(1).to_dict(orient='records')
    result['平均气候度假指数']['逐月'] = I_HC_monthly.round(1).to_dict(orient='records')
    result['平均气候度假指数']['累年各月'] = I_HC_accum.round(1).to_dict(orient='records')

    result['适宜及以上日数'] = edict()
    result['适宜及以上日数']['逐年'] = cozy_level_yearly.round(1).to_dict(orient='records')
    result['适宜及以上日数']['逐月'] = cozy_level_monthly.round(1).to_dict(orient='records')

    result['各等级日数统计'] = edict()
    result['各等级日数统计']['逐年'] = level_yearly.round(1).to_dict(orient='records')
    result['各等级日数统计']['逐月'] = level_monthly.round(1).to_dict(orient='records')

    result['规范统计'] = edict()
    result['规范统计']['历年适宜以上等级的月数'] = comfortable_months.round(1).to_dict(orient='records')
    result['规范统计']['历年平均气候度假指数等级'] = comfort_level_yearly.round(1).to_dict(orient='records')
    result['规范统计']['累年各月平均气候度假指数等级'] = comfort_level_accum.round(1).to_dict(orient='records')
    result['规范统计']['累年各月平均气候度假适宜日数'] = comfort_days_accum.round(1).to_dict(orient='records')

    return result, comfortable_months


def I_TC_calculation(input_df):
    '''
    计算气候旅游指数 I_TC
    输出：
    气候旅游指数日变化
    '''
    sample_data = input_df[['TEM_Avg', 'TEM_Max', 'TEM_Min', 'RHU_Avg', 'RHU_Min', 'WIN_S_2mi_Avg', 'PRE_Time_2020', 'SSH']]

    # 计算白天有效温度T_Ed，以及白天有效温度分值ST_Ed/全天有效温度T_Ea，以及全天有效温度分值ST_Ea
    def sample_tem_score(x):
        if (x >= 20) & (x <= 26):
            x = 5.0
        elif (x == 19) ^ (x == 27):
            x = 4.5
        elif (x == 18) ^ (x == 28):
            x = 4.0
        elif (x == 17) ^ (x == 29):
            x = 3.5
        elif (x == 16) ^ (x == 30):
            x = 3.0
        elif ((x >= 10) & (x <= 15)) ^ (x == 31):
            x = 2.5
        elif ((x >= 5) & (x <= 9)) ^ (x == 32):
            x = 2.0
        elif ((x >= 0) & (x <= 4)) ^ (x == 33):
            x = 1.5
        elif ((x >= -5) & (x <= 1)) ^ (x == 34):
            x = 1.0
        elif x == 35:
            x = 0.5
        elif (x > 36) ^ ((x >= -10) & (x <= -6)):
            x = 0
        elif (x >= -15) & (x <= -11):
            x = -1.0
        elif (x >= -20) & (x <= -16):
            x = -2.0
        elif x < -20:
            x = -3.0
        return x

    T_Ed = sample_data['TEM_Max'] - 0.55 * (1 - sample_data['RHU_Min']) * (sample_data['TEM_Max'] - 14.4)
    T_Ed = round(T_Ed, 0)

    T_Ea = sample_data['TEM_Avg'] - 0.55 * (1 - sample_data['RHU_Avg']) * (sample_data['TEM_Avg'] - 14.4)
    T_Ea = round(T_Ea, 0)

    ST_Ed = T_Ed.apply(sample_tem_score)
    ST_Ea = T_Ea.apply(sample_tem_score)

    # 计算日降水量分值SR1
    def sample_pre_score(x):
        if x < 0.5:
            x = 5.0
        elif (x >= 0.5) & (x <= 0.9):
            x = 4.5
        elif (x >= 1.0) & (x <= 1.4):
            x = 4.0
        elif (x >= 1.5) & (x <= 1.9):
            x = 3.5
        elif (x >= 2.0) & (x <= 2.4):
            x = 3.0
        elif (x >= 2.5) & (x <= 2.9):
            x = 2.5
        elif (x >= 3.0) & (x <= 3.4):
            x = 2.0
        elif (x >= 3.5) & (x <= 3.9):
            x = 1.5
        elif (x >= 4.0) & (x <= 4.4):
            x = 1.0
        elif (x >= 4.5) & (x <= 4.9):
            x = 0.5
        elif x >= 5.0:
            x = 0
        return x

    SR1 = round(sample_data['PRE_Time_2020'], 1)
    SR1 = SR1.apply(sample_pre_score)

    # 计算日日照时分值SE
    def sample_ssd_score(x):
        if x >= 10:
            x = 5.0
        elif x == 9:
            x = 4.5
        elif x == 8:
            x = 4.0
        elif x == 7:
            x = 3.5
        elif x == 6:
            x = 3.0
        elif x == 5:
            x = 2.5
        elif x == 4:
            x = 2.0
        elif x == 3:
            x = 1.5
        elif x == 2:
            x = 1.0
        elif x == 1:
            x = 0.5
        elif x < 1:
            x = 0
        return x

    SE = round(sample_data['SSH'], 0)
    SE = SE.apply(sample_ssd_score)

    # 计算日平均风速分值SV
    # 当日最高气温低于15度时，采用风寒指数I_K代替日平均风速
    # 规范里面提到使用风寒指数时，同时需要日平均风速大于8km/h，实现的版本没有按照这个要求，因为会有数据不符合条件，无法进行赋分
    data = input_df[['TEM_Max', 'TEM_Avg', 'WIN_S_2mi_Avg']]
    data1 = data.copy()
    data1['TEM_Max'] = data1['TEM_Max'].round(1)
    data1['平均风速换算'] = (data1['WIN_S_2mi_Avg'] * 3.6).round(1)  # 1米/秒(米每秒) = 3.6千米/时(千米每小时)
    data1['风寒指数'] = ((12.1452 + 11.6222 * data1['WIN_S_2mi_Avg'].apply(np.sqrt) - 1.1622 * data1['WIN_S_2mi_Avg']) * (33 - data1['TEM_Avg'])).round(0)

    data2 = data1.copy()
    data2['SV'] = 999

    data2[(data2['TEM_Max'] >= 15) & (data2['TEM_Max'] <= 23.9) & (data2['平均风速换算'] < 2.88)] = 5.0
    data2[(data2['TEM_Max'] >= 15) & (data2['TEM_Max'] <= 23.9) & (data2['平均风速换算'] >= 2.88) & (data2['平均风速换算'] <= 5.75)] = 4.5
    data2[(data2['TEM_Max'] >= 15) & (data2['TEM_Max'] <= 23.9) & (data1['平均风速换算'] >= 5.76) & (data2['平均风速换算'] <= 9.03)] = 4.0
    data2[(data2['TEM_Max'] >= 15) & (data2['TEM_Max'] <= 23.9) & (data2['平均风速换算'] >= 9.04) & (data2['平均风速换算'] <= 12.23)] = 3.5
    data2[(data2['TEM_Max'] >= 15) & (data2['TEM_Max'] <= 23.9) & (data2['平均风速换算'] >= 12.24) & (data2['平均风速换算'] <= 19.79)] = 3.0
    data2[(data2['TEM_Max'] >= 15) & (data2['TEM_Max'] <= 23.9) & (data2['平均风速换算'] >= 19.80) & (data2['平均风速换算'] <= 24.29)] = 2.5
    data2[(data2['TEM_Max'] >= 15) & (data2['TEM_Max'] <= 23.9) & (data2['平均风速换算'] >= 24.30) & (data2['平均风速换算'] <= 28.79)] = 2.0
    data2[(data2['TEM_Max'] >= 15) & (data2['TEM_Max'] <= 23.9) & (data2['平均风速换算'] >= 28.80) & (data2['平均风速换算'] <= 38.52)] = 1.5
    data2[(data2['TEM_Max'] >= 15) & (data2['TEM_Max'] <= 23.9) & (data2['平均风速换算'] > 38.52)] = 0

    data2[(data2['TEM_Max'] >= 24) & (data2['TEM_Max'] <= 33) & (data2['平均风速换算'] >= 12.24) & (data2['平均风速换算'] <= 19.79)] = 5.0
    data2[(data2['TEM_Max'] >= 24) & (data2['TEM_Max'] <= 33) & (data2['平均风速换算'] >= 9.04) & (data2['平均风速换算'] <= 12.23)] = 4.0
    data2[(data2['TEM_Max'] >= 24) & (data2['TEM_Max'] <= 33) & (data2['平均风速换算'] >= 19.80) & (data2['平均风速换算'] <= 24.29)] = 4.0
    data2[(data2['TEM_Max'] >= 24) & (data2['TEM_Max'] <= 33) & (data2['平均风速换算'] >= 5.76) & (data2['平均风速换算'] <= 9.03)] = 3.0
    data2[(data2['TEM_Max'] >= 24) & (data2['TEM_Max'] <= 33) & (data2['平均风速换算'] >= 24.30) & (data2['平均风速换算'] <= 28.79)] = 3.0
    data2[(data2['TEM_Max'] >= 24) & (data2['TEM_Max'] <= 33) & (data2['平均风速换算'] >= 2.88) & (data2['平均风速换算'] <= 5.75)] = 2.5
    data2[(data2['TEM_Max'] >= 24) & (data2['TEM_Max'] <= 33) & (data2['平均风速换算'] >= 28.80) & (data2['平均风速换算'] <= 38.52)] = 2.0
    data2[(data2['TEM_Max'] >= 24) & (data2['TEM_Max'] <= 33) & (data2['平均风速换算'] < 2.88)] = 2.0
    data2[(data2['TEM_Max'] >= 24) & (data2['TEM_Max'] <= 33) & (data2['平均风速换算'] > 38.52)] = 0

    data2[(data2['TEM_Max'] >= 33) & (data2['平均风速换算'] < 2.88)] = 2.0
    data2[(data2['TEM_Max'] >= 33) & (data2['平均风速换算'] >= 2.88) & (data2['平均风速换算'] <= 5.75)] = 1.5
    data2[(data2['TEM_Max'] >= 33) & (data2['平均风速换算'] >= 5.76) & (data2['平均风速换算'] <= 9.03)] = 1.0
    data2[(data2['TEM_Max'] >= 33) & (data2['平均风速换算'] >= 9.04) & (data2['平均风速换算'] <= 12.23)] = 0.5
    data2[(data2['TEM_Max'] >= 33) & (data2['平均风速换算'] > 12.23)] = 0

    data2[(data2['TEM_Max'] < 15) & (data2['风寒指数'] < 500)] = 4.0
    data2[(data2['TEM_Max'] < 15) & (data2['风寒指数'] >= 500) & (data2['风寒指数'] < 625)] = 3.0
    data2[(data2['TEM_Max'] < 15) & (data2['风寒指数'] >= 625) & (data2['风寒指数'] < 750)] = 2.0
    data2[(data2['TEM_Max'] < 15) & (data2['风寒指数'] >= 750) & (data2['风寒指数'] < 875)] = 1.5
    data2[(data2['TEM_Max'] < 15) & (data2['风寒指数'] >= 875) & (data2['风寒指数'] < 1000)] = 1.0
    data2[(data2['TEM_Max'] < 15) & (data2['风寒指数'] >= 1000) & (data2['风寒指数'] < 1125)] = 0.5
    data2[(data2['TEM_Max'] < 15) & (data2['风寒指数'] >= 1125) & (data2['风寒指数'] < 1250)] = 0.25
    data2[(data2['TEM_Max'] < 15) & (data2['风寒指数'] >= 1250)] = 0

    SV1 = data2['SV']

    # 计算气候旅游指数I_TC
    I_TC = 2 * (4 * ST_Ed + ST_Ea + 2 * SR1 + 2 * SE + SV1)
    I_TC = round(I_TC, 0)
    I_TC = I_TC.to_frame()
    I_TC.columns = ['气候旅游指数']

    return I_TC


def I_TC_stats(I_TC):
    '''
    基于气候旅游指数 I_TC，进行统计
    
    输出：
    1.平均气候旅游指数 (逐年/逐月/累年各月)
    2.舒适及以上日数 (逐年/逐月)
    3.各等级日数统计 (逐年/逐月)
    4.规范统计(规范/原型要求)
    '''
    # 添加日气候旅游指数对应等级
    I_TC['等级'] = pd.cut(I_TC['气候旅游指数'], bins=[-np.inf, 9, 19, 29, 39, 49, 59, 69, 79, 89, np.inf], labels=list(range(0, 10)))
    I_TC['等级'] = I_TC['等级'].astype(int)

    # 1-1 平均气候旅游指数(逐年)
    I_TC_yearly = I_TC['气候旅游指数'].resample('1A', closed='right', label='right').mean().round(0)  # 年平均
    I_TC_yearly = I_TC_yearly.to_frame()
    I_TC_yearly.insert(loc=0, column='年份', value=I_TC_yearly.index.year)
    I_TC_yearly.reset_index(drop=True, inplace=True)

    # 1-2 平均气候旅游指数(逐月)
    I_TC_monthly = I_TC['气候旅游指数'].resample('1M', closed='right', label='right').mean().round(0)  # 月平均
    I_TC_monthly = I_TC_monthly.to_frame()
    I_TC_monthly.insert(loc=0, column='年份', value=I_TC_monthly.index.strftime('%Y-%m'))
    I_TC_monthly.reset_index(drop=True, inplace=True)

    # 1-3 平均气候旅游指数(累年各月)
    I_TC_accum = []
    for i in range(1, 13):
        month_i_mean = I_TC.loc[I_TC.index.month == i, '气候旅游指数'].mean()
        I_TC_accum.append(month_i_mean)

    I_TC_accum = pd.DataFrame(I_TC_accum).round(0)
    I_TC_accum.columns = ['气候旅游指数']
    I_TC_accum.insert(loc=0, column='日期', value=[str(i) + '月' for i in range(1, 13)])

    # 2-1 舒适及以上日数(逐年) 对应等级6~9的日数
    I_TC_sample = I_TC[I_TC['等级'].isin([6, 7, 8, 9])]
    cozy_level_yearly = I_TC_sample['等级'].resample('1A', closed='right', label='right').apply(lambda x: len(x))
    cozy_level_yearly = cozy_level_yearly.to_frame()
    cozy_level_yearly.columns = ['舒适及以上等级日数']
    cozy_level_yearly.insert(loc=0, column='年份', value=cozy_level_yearly.index.year)
    cozy_level_yearly.reset_index(drop=True, inplace=True)

    # 2-2 舒适及以上日数(逐月) 对应等级6~9的日数
    cozy_level_monthly = I_TC_sample['等级'].resample('1M', closed='right', label='right').apply(lambda x: len(x))
    cozy_level_monthly = cozy_level_monthly.to_frame()
    cozy_level_monthly.columns = ['舒适及以上等级日数']
    cozy_level_monthly.insert(loc=0, column='年份', value=cozy_level_monthly.index.strftime('%Y-%m'))
    cozy_level_monthly.reset_index(drop=True, inplace=True)

    # 3-1 各等级日数统计(逐年)
    level_yearly = I_TC.groupby([I_TC.index.year])['等级'].value_counts().unstack(fill_value=0)
    level_yearly.columns = ['level_' + str(col) for col in level_yearly.columns]
    level_yearly.insert(loc=0, column='年', value=level_yearly.index.get_level_values(0))
    level_yearly.reset_index(drop=True, inplace=True)

    # 3-2 各等级日数统计(逐月)
    level_monthly = I_TC.groupby([I_TC.index.year, I_TC.index.month])['等级'].value_counts().unstack(fill_value=0)
    level_monthly.columns = ['level_' + str(col) for col in level_monthly.columns]
    level_monthly.insert(loc=0, column='月', value=level_monthly.index.get_level_values(1))
    level_monthly.insert(loc=0, column='年', value=level_monthly.index.get_level_values(0))
    level_monthly.reset_index(drop=True, inplace=True)

    # 4-1 历年舒适以上等级的月数 (对应等级6,7,8,9，val:60-79)
    def sample_comfortable(x):
        x = np.array(x)
        values = np.where(x >= 60, 1, 0)
        return np.sum(values)

    monthly = I_TC['气候旅游指数'].resample('1M', closed='right', label='right').mean().round(0)
    comfortable_months = monthly.resample('1A', closed='right', label='right').apply(sample_comfortable).to_frame()
    comfortable_months.columns = ['舒适以上等级的月数']
    comfortable_months.insert(loc=0, column='年', value=comfortable_months.index.year)
    comfortable_months.reset_index(drop=True, inplace=True)

    # 4-2 历年平均气候旅游指数对应的等级
    comfort_level_yearly = I_TC['等级'].resample('1A', closed='right', label='right').mean().round(0).to_frame()
    comfort_level_yearly.columns = ['平均气候旅游指数']
    comfort_level_yearly.insert(loc=0, column='年', value=comfort_level_yearly.index.year)
    comfort_level_yearly.reset_index(drop=True, inplace=True)

    # 4-3 累年各月平均气候旅游指数对应的等级
    comfort_level_accum = []
    for i in range(1, 13):
        month_i_mean = I_TC.loc[I_TC.index.month == i, '等级'].mean()
        comfort_level_accum.append(month_i_mean)

    comfort_level_accum = pd.DataFrame(comfort_level_accum).round(0)
    comfort_level_accum.columns = ['累年各月平均气候旅游指数等级']
    comfort_level_accum.insert(loc=0, column='日期', value=[str(i) + '月' for i in range(1, 13)])
    comfort_level_accum.reset_index(drop=True, inplace=True)

    # 4-4 累年各月平均气候旅游舒适日数
    def sample_comfortable_days(x):
        x = np.array(x)
        values = np.where(x >= 60, 1, 0)
        return np.sum(values)

    comfort_days_monthly = I_TC['气候旅游指数'].resample('1M', closed='right', label='right').apply(sample_comfortable_days)
    comfort_days_accum = []
    for i in range(1, 13):
        month_i_mean = comfort_days_monthly[comfort_days_monthly.index.month == i].mean()
        comfort_days_accum.append(month_i_mean)

    comfort_days_accum = pd.DataFrame(comfort_days_accum).round(0)
    comfort_days_accum.columns = ['累年各月平均气候旅游舒适日数']
    comfort_days_accum.insert(loc=0, column='日期', value=[str(i) + '月' for i in range(1, 13)])

    # 保存字典
    result = edict()
    result['平均气候旅游指数'] = edict()
    result['平均气候旅游指数']['逐年'] = I_TC_yearly.round(1).to_dict(orient='records')
    result['平均气候旅游指数']['逐月'] = I_TC_monthly.round(1).to_dict(orient='records')
    result['平均气候旅游指数']['累年各月'] = I_TC_accum.round(1).to_dict(orient='records')

    result['舒适及以上日数'] = edict()
    result['舒适及以上日数']['逐年'] = cozy_level_yearly.round(1).to_dict(orient='records')
    result['舒适及以上日数']['逐月'] = cozy_level_monthly.round(1).to_dict(orient='records')

    result['各等级日数统计'] = edict()
    result['各等级日数统计']['逐年'] = level_yearly.round(1).to_dict(orient='records')
    result['各等级日数统计']['逐月'] = level_monthly.round(1).to_dict(orient='records')

    result['规范统计'] = edict()
    result['规范统计']['历年舒适以上等级的月数'] = comfortable_months.round(1).to_dict(orient='records')
    result['规范统计']['历年平均气候旅游指数等级'] = comfort_level_yearly.round(1).to_dict(orient='records')
    result['规范统计']['累年各月平均气候旅游指数等级'] = comfort_level_accum.round(1).to_dict(orient='records')
    result['规范统计']['累年各月平均气候旅游适宜日数'] = comfort_days_accum.round(1).to_dict(orient='records')

    return result, comfortable_months


def climate_comfort_main(input_df):
    '''
    气候舒适性主流程
    '''
    rank_result = np.zeros(4)

    # 人体舒适度
    tmp = input_df[['TEM_Avg', 'RHU_Avg', 'WIN_S_2mi_Avg']]
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        result_BC = None
        rank_result[0] = np.nan
        rank_result[1] = np.nan

    else:
        I_BC = I_BC_calculation(input_df)
        result_BC, factor_A, factor_B = I_BC_stats(I_BC)
        factor_A = factor_A.iloc[:, 1].mean()
        factor_B = factor_B.iloc[:, 1].mean()

        if factor_A >= 4:
            rank_result[0] = 1
        elif factor_A >= 3 and factor_A < 4:
            rank_result[0] = 2
        elif factor_A < 3:
            rank_result[0] = 3

        if factor_B >= 8:
            rank_result[1] = 1
        elif factor_B >= 6 and factor_B < 8:
            rank_result[1] = 2
        elif factor_B < 6:
            rank_result[1] = 3

    # 气候度假指数
    tmp = input_df[['TEM_Avg', 'TEM_Max', 'RHU_Avg', 'WIN_S_2mi_Avg', 'PRE_Time_2020', 'CLO_Cov_Avg']]
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        result_HC = None
        rank_result[2] = np.nan

    else:
        I_HC = I_HC_calculation(input_df)
        result_HC, factor_C = I_HC_stats(I_HC)
        factor_C = factor_C.iloc[:, 1].mean()

        if factor_C >= 10:
            rank_result[2] = 1
        elif factor_C >= 8 and factor_C < 10:
            rank_result[2] = 2
        elif factor_C < 8:
            rank_result[2] = 3

    # 气候旅游指数
    tmp = input_df[['TEM_Avg', 'TEM_Max', 'TEM_Min', 'RHU_Avg', 'RHU_Min', 'WIN_S_2mi_Avg', 'PRE_Time_2020', 'SSH']]
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        result_TC = None
        rank_result[3] = np.nan

    else:
        I_TC = I_TC_calculation(input_df)
        result_TC, factor_D = I_TC_stats(I_TC)
        factor_D = factor_D.iloc[:, 1].mean()

        if factor_D >= 8:
            rank_result[3] = 1
        elif factor_D >= 6 and factor_D < 8:
            rank_result[3] = 2
        elif factor_D < 6:
            rank_result[3] = 3

    # 气候舒适性最终结果
    if np.all(rank_result == np.nan):
        rank_result_df = None

    else:
        rank_result_df = pd.DataFrame(rank_result, columns=['评价等级'])
        rank_result_df['选取因子'] = ['人体舒适指数(最舒适等级的月数)', '人体舒适指数(舒适等级以上的月数)', '气候度假指数(适宜等级以上的月数)', '气候旅游指数(舒适等级以上的月数)']
        rank_result_df = rank_result_df[['选取因子', '评价等级']]
        rank_result_df['因子数值'] = [factor_A, factor_B, factor_C, factor_D]
        rank_result_df['单位'] = [np.nan] * 4
        rank_result_df = rank_result_df.round(1).to_dict(orient='records')

    # 创建结果字典
    result_dict = edict()

    tables = edict()
    tables['人体舒适度指数'] = result_BC
    tables['气候度假指数'] = result_HC
    tables['气候旅游指数'] = result_TC

    assessments = edict()
    assessments['level'] = rank_result_df

    result_dict.tables = tables
    result_dict.assessments = assessments

    return result_dict


if __name__ == '__main__':
    daily_elements = 'PRS_Avg,TEM_Avg,TEM_Max,TEM_Min,RHU_Avg,RHU_Min,PRE_Time_2020,WIN_S_2mi_Avg,SSH,CLO_Cov_Avg,WIN_S_Max,FlSa,SaSt,Haze,Hail,Thund,Tord,Squa'
    day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements).split(',')
    daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    daily_df = daily_df.loc[daily_df['Station_Id_C'] == 52866, day_eles]
    daily_df = daily_data_processing(daily_df)
    daily_df = daily_df[(daily_df.index.year>=1994) & (daily_df.index.year<=2023)]
    daily_df['RHU_Avg'] = daily_df['RHU_Avg'] / 100
    daily_df['RHU_Min'] = daily_df['RHU_Min'] / 100
    cols = ['TEM_Max', 'TEM_Min', 'PRE_Time_2020', 'WIN_S_Max', 'WIN_S_2mi_Avg', 'PRS_Avg', 'TEM_Avg', 'RHU_Avg', 'RHU_Min', 'SSH', 'CLO_Cov_Avg']
    daily_df[cols] = daily_df[cols].interpolate(method='linear', axis=0)  # 缺失值插值填充
    daily_df[cols] = daily_df[cols].fillna(method='bfill')  # 填充后一条数据的值，但是后一条也不一定有值
    daily_df[['Hail', 'Tord', 'SaSt', 'FlSa', 'Haze', 'Thund', 'Squa']] = daily_df[['Hail', 'Tord', 'SaSt', 'FlSa', 'Haze', 'Thund', 'Squa']].fillna(0)
    result = climate_comfort_main(daily_df)
