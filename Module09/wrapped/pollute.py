# -*- coding: utf-8 -*-
"""
Created on Fri Jun 21 10:24:21 2024

@author: EDY

Function: 不同大气稳定度下的参证站污染系数、通风量、混合层厚度、大气自净能力计算
"""

import logging
import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.data_processing import monthly_data_processing


def basic_win_freq_statistics(win_freq):
    '''
    风向频率以及风向对应的风速要素，累年各月统计，
    使用天擎上的月数据，要素名称为天擎上默认的名称
    月值要素：['Station_Id_C', 'Year', 'Mon', 'WIN_S_Avg_NNE', 'WIN_S_Avg_NE',
              'WIN_S_Avg_ENE', 'WIN_S_Avg_E', 'WIN_S_Avg_ESE', 'WIN_S_Avg_SE',
              'WIN_S_Avg_SSE', 'WIN_S_Avg_S', 'WIN_S_Avg_SSW', 'WIN_S_Avg_SW',
              'WIN_S_Avg_WSW', 'WIN_S_Avg__W', 'WIN_S_Avg_WNW', 'WIN_S_Avg_NW',
              'WIN_S_Avg_NNW', 'WIN_S_Avg__N', 'WIN_NNE_Freq', 'WIN_NE_Freq',
              'WIN_ENE_Freq', 'WIN_E_Freq', 'WIN_ESE_Freq', 'WIN_SE_Freq',
              'WIN_SSE_Freq', 'WIN_S_Freq', 'WIN_SSW_Freq', 'WIN_SW_Freq',
              'WIN_WSW_Freq', 'WIN_W_Freq', 'WIN_WNW_Freq', 'WIN_NW_Freq',
              'WIN_NNW_Freq', 'WIN_N_Freq', 'WIN_C_Freq']
    return: dataframe
    '''
    try:
        # 累年各月风向频数
        win_d_freq = win_freq[[
            'WIN_NNE_Freq', 'WIN_NE_Freq', 'WIN_ENE_Freq', 'WIN_E_Freq', 'WIN_ESE_Freq', 'WIN_SE_Freq', 'WIN_SSE_Freq', 'WIN_S_Freq', 'WIN_SSW_Freq', 'WIN_SW_Freq', 'WIN_WSW_Freq', 'WIN_W_Freq', 'WIN_WNW_Freq', 'WIN_NW_Freq', 'WIN_NNW_Freq',
            'WIN_N_Freq', 'WIN_C_Freq'
        ]]

        mean_win_d_accum = []

        for i in range(1, 13):
            month_i_mean = win_d_freq[win_d_freq.index.month == i].mean().round(1).to_frame()
            mean_win_d_accum.append(month_i_mean)

            basic_win_d_accum = pd.concat(mean_win_d_accum, axis=1, ignore_index=True)
            basic_win_d_accum.index = ['NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW', 'N', 'C']

        # 增加月份
        basic_win_d_accum.columns = [str(i) + '月' for i in range(1, 13)]

        # 季度总频数和年度总频数
        basic_win_d_accum['春季'] = basic_win_d_accum.iloc[:, 2:5].mean(axis=1).round(1)
        basic_win_d_accum['夏季'] = basic_win_d_accum.iloc[:, 5:8].mean(axis=1).round(1)
        basic_win_d_accum['秋季'] = basic_win_d_accum.iloc[:, 8:11].mean(axis=1).round(1)
        basic_win_d_accum['冬季'] = basic_win_d_accum.iloc[:, [0, 1, 11]].mean(axis=1).round(1)
        basic_win_d_accum['全年'] = basic_win_d_accum.iloc[:, 0:12].mean(axis=1).round(1)

        basic_win_d_accum = basic_win_d_accum.T
        basic_win_d_accum.reset_index(inplace=True)
        basic_win_d_accum.rename(columns={'index': '月份'}, inplace=True)

        tmp = basic_win_d_accum.dropna(axis=1, how='all')
        if len(tmp.columns) == 1:  # 如果只有年份一列，说明全部没有数据
            basic_win_d_accum = None
        else:
            basic_win_d_accum = basic_win_d_accum  #.to_dict(orient='records')

    except Exception as e:
        logging.exception(e)
        basic_win_d_accum = None

    finally:
        try:
            # 累年各月风向对应的风速
            win_d_s = win_freq[[
                'WIN_S_Avg_NNE', 'WIN_S_Avg_NE', 'WIN_S_Avg_ENE', 'WIN_S_Avg_E', 'WIN_S_Avg_ESE', 'WIN_S_Avg_SE', 'WIN_S_Avg_SSE', 'WIN_S_Avg_S', 'WIN_S_Avg_SSW', 'WIN_S_Avg_SW', 'WIN_S_Avg_WSW', 'WIN_S_Avg__W', 'WIN_S_Avg_WNW', 'WIN_S_Avg_NW',
                'WIN_S_Avg_NNW', 'WIN_S_Avg__N'
            ]]
            mean_win_s_accum = []

            for i in range(1, 13):
                month_i_mean = win_d_s[win_d_s.index.month == i].mean().round(1).to_frame()
                mean_win_s_accum.append(month_i_mean)

                basic_win_s_accum = pd.concat(mean_win_s_accum, axis=1, ignore_index=True)
                basic_win_s_accum.index = ['NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW', 'N']

            # 增加月份
            basic_win_s_accum.columns = [str(i) + '月' for i in range(1, 13)]

            # 季度总频数和年度总频数
            basic_win_s_accum['春季'] = basic_win_s_accum.iloc[:, 2:5].mean(axis=1).round(1)
            basic_win_s_accum['夏季'] = basic_win_s_accum.iloc[:, 5:8].mean(axis=1).round(1)
            basic_win_s_accum['秋季'] = basic_win_s_accum.iloc[:, 8:11].mean(axis=1).round(1)
            basic_win_s_accum['冬季'] = basic_win_s_accum.iloc[:, [0, 1, 11]].mean(axis=1).round(1)
            basic_win_s_accum['全年'] = basic_win_s_accum.iloc[:, 0:12].mean(axis=1).round(1)

            basic_win_s_accum = basic_win_s_accum.T
            basic_win_s_accum.reset_index(inplace=True)
            basic_win_s_accum.rename(columns={'index': '月份'}, inplace=True)

            tmp = basic_win_s_accum.dropna(axis=1, how='all')
            if len(tmp.columns) == 1:
                basic_win_s_accum = None
            else:
                basic_win_s_accum = basic_win_s_accum  #.to_dict(orient='records')

        except Exception as e:
            logging.exception(e)
            basic_win_s_accum = None

        finally:
            return basic_win_d_accum, basic_win_s_accum


def depth_mixed_layer(post_monthly_df):
    omega = 7.292e-5
    f = 2 * omega * np.sin(post_monthly_df['Lat'][0] * np.pi / 180)

    post_monthly_df.loc[post_monthly_df['WIN_S_2mi_Avg'] > 6, 'WIN_S_2mi_Avg'] = 6

    data = pd.DataFrame(post_monthly_df['WIN_S_2mi_Avg'])
    # 大气稳定度为A、B、C、D

    a_s = [0.090, 0.067, 0.041, 0.031]
    data['A'] = a_s[0] * post_monthly_df['WIN_S_2mi_Avg'] / f
    data['B'] = a_s[1] * post_monthly_df['WIN_S_2mi_Avg'] / f
    data['C'] = a_s[2] * post_monthly_df['WIN_S_2mi_Avg'] / f
    data['D'] = a_s[3] * post_monthly_df['WIN_S_2mi_Avg'] / f
    # 大气稳定度为E、F
    b_s = [1.66, 0.7]
    data['E'] = b_s[0] * np.sqrt(post_monthly_df['WIN_S_2mi_Avg'] / f)
    data['F'] = b_s[1] * np.sqrt(post_monthly_df['WIN_S_2mi_Avg'] / f)

    data2 = data.copy()
    data.drop(['WIN_S_2mi_Avg'], axis=1, inplace=True)

    data_accum = []

    for i in range(1, 13):
        data_i_mean = data[data.index.month == i].mean().round(1).to_frame()
        data_accum.append(data_i_mean)

    data_accum = pd.concat(data_accum, axis=1, ignore_index=True)

    # 增加月份
    data_accum.columns = [str(i) + '月' for i in range(1, 13)]

    # 季度总频数和年度总频数
    data_accum['春季'] = data_accum.iloc[:, 2:5].mean(axis=1).round(1)
    data_accum['夏季'] = data_accum.iloc[:, 5:8].mean(axis=1).round(1)
    data_accum['秋季'] = data_accum.iloc[:, 8:11].mean(axis=1).round(1)
    data_accum['冬季'] = data_accum.iloc[:, [0, 1, 11]].mean(axis=1).round(1)
    data_accum['全年'] = data_accum.iloc[:, 0:12].mean(axis=1).round(1)

    data_accum = data_accum.T
    data_accum.reset_index(inplace=True, drop=False)
    data_accum.rename(columns={'index': '月份'}, inplace=True)

    return data2, data_accum


def ven_ability(post_monthly_df, data_depth):
    data = data_depth.copy()
    p_m = [0.07, 0.07, 0.1, 0.15, 0.25, 0.25]
    data_depth['a_200'] = data_depth['WIN_S_2mi_Avg'] * (200 / 10)**p_m[0]
    data_depth['b_200'] = data_depth['WIN_S_2mi_Avg'] * (200 / 10)**p_m[1]
    data_depth['c_200'] = data_depth['WIN_S_2mi_Avg'] * (200 / 10)**p_m[2]
    data_depth['d_200'] = data_depth['WIN_S_2mi_Avg'] * (200 / 10)**p_m[3]
    data_depth['e_200'] = data_depth['WIN_S_2mi_Avg'] * (200 / 10)**p_m[4]
    data_depth['f_200'] = data_depth['WIN_S_2mi_Avg'] * (200 / 10)**p_m[5]

    data['A'][data_depth['A'] <= 200] = (data_depth['a_200'][data_depth['A'] <= 200] + data_depth['WIN_S_2mi_Avg'][data_depth['A'] <= 200]) * 0.5 * data_depth['A'][data_depth['A'] <= 200]
    data['A'][data_depth['A'] > 200] = 200 * (data_depth['a_200'][data_depth['A'] > 200] + data_depth['WIN_S_2mi_Avg'][data_depth['A'] > 200]) * 0.5 + (data_depth['A'][data_depth['A'] > 200] - 200) * data_depth['a_200'][data_depth['A'] > 200]

    data['B'][data_depth['B'] <= 200] = (data_depth['b_200'][data_depth['B'] <= 200] + data_depth['WIN_S_2mi_Avg'][data_depth['B'] <= 200]) * 0.5 * data_depth['B'][data_depth['B'] <= 200]
    data['B'][data_depth['B'] > 200] = 200 * (data_depth['b_200'][data_depth['B'] > 200] + data_depth['WIN_S_2mi_Avg'][data_depth['B'] > 200]) * 0.5 + (data_depth['B'][data_depth['B'] > 200] - 200) * data_depth['b_200'][data_depth['B'] > 200]

    data['C'][data_depth['C'] <= 200] = (data_depth['c_200'][data_depth['C'] <= 200] + data_depth['WIN_S_2mi_Avg'][data_depth['C'] <= 200]) * 0.5 * data_depth['C'][data_depth['C'] <= 200]
    data['C'][data_depth['C'] > 200] = 200 * (data_depth['c_200'][data_depth['C'] > 200] + data_depth['WIN_S_2mi_Avg'][data_depth['C'] > 200]) * 0.5 + (data_depth['C'][data_depth['C'] > 200] - 200) * data_depth['c_200'][data_depth['C'] > 200]

    data['D'][data_depth['D'] <= 200] = (data_depth['d_200'][data_depth['D'] <= 200] + data_depth['WIN_S_2mi_Avg'][data_depth['D'] <= 200]) * 0.5 * data_depth['D'][data_depth['D'] <= 200]
    data['D'][data_depth['D'] > 200] = 200 * (data_depth['d_200'][data_depth['D'] > 200] + data_depth['WIN_S_2mi_Avg'][data_depth['D'] > 200]) * 0.5 + (data_depth['D'][data_depth['D'] > 200] - 200) * data_depth['d_200'][data_depth['D'] > 200]

    data['E'][data_depth['E'] <= 200] = (data_depth['e_200'][data_depth['E'] <= 200] + data_depth['WIN_S_2mi_Avg'][data_depth['E'] <= 200]) * 0.5 * data_depth['E'][data_depth['E'] <= 200]
    data['E'][data_depth['E'] > 200] = 200 * (data_depth['e_200'][data_depth['E'] > 200] + data_depth['WIN_S_2mi_Avg'][data_depth['E'] > 200]) * 0.5 + (data_depth['E'][data_depth['E'] > 200] - 200) * data_depth['e_200'][data_depth['E'] > 200]

    data['F'][data_depth['F'] <= 200] = (data_depth['f_200'][data_depth['F'] <= 200] + data_depth['WIN_S_2mi_Avg'][data_depth['F'] <= 200]) * 0.5 * data_depth['F'][data_depth['F'] <= 200]
    data['F'][data_depth['F'] > 200] = 200 * (data_depth['f_200'][data_depth['F'] > 200] + data_depth['WIN_S_2mi_Avg'][data_depth['F'] > 200]) * 0.5 + (data_depth['F'][data_depth['F'] > 200] - 200) * data_depth['f_200'][data_depth['F'] > 200]

    data.drop(['WIN_S_2mi_Avg'], axis=1, inplace=True)

    data_accum = []

    for i in range(1, 13):
        data_i_mean = data[data.index.month == i].mean().round(1).to_frame()
        data_accum.append(data_i_mean)

    data_accum = pd.concat(data_accum, axis=1, ignore_index=True)

    # 增加月份
    data_accum.columns = [str(i) + '月' for i in range(1, 13)]

    # 季度总频数和年度总频数
    data_accum['春季'] = data_accum.iloc[:, 2:5].mean(axis=1).round(1)
    data_accum['夏季'] = data_accum.iloc[:, 5:8].mean(axis=1).round(1)
    data_accum['秋季'] = data_accum.iloc[:, 8:11].mean(axis=1).round(1)
    data_accum['冬季'] = data_accum.iloc[:, [0, 1, 11]].mean(axis=1).round(1)
    data_accum['全年'] = data_accum.iloc[:, 0:12].mean(axis=1).round(1)

    data_accum = data_accum.T
    data_accum.reset_index(inplace=True, drop=False)
    data_accum.rename(columns={'index': '月份'}, inplace=True)

    return data, data_accum


def ASC_caculate(post_monthly_df, data_ven_ability):
    data = pd.DataFrame(post_monthly_df['PRE_Time_2020'])

    data['A'] = 3.1536 * 10**(-3) * np.sqrt(np.pi / 2) * data_ven_ability['A'] + 1.7 * 10**(-3) * data['PRE_Time_2020'] * np.sqrt(100)
    data['B'] = 3.1536 * 10**(-3) * np.sqrt(np.pi / 2) * data_ven_ability['B'] + 1.7 * 10**(-3) * data['PRE_Time_2020'] * np.sqrt(100)
    data['C'] = 3.1536 * 10**(-3) * np.sqrt(np.pi / 2) * data_ven_ability['C'] + 1.7 * 10**(-3) * data['PRE_Time_2020'] * np.sqrt(100)
    data['D'] = 3.1536 * 10**(-3) * np.sqrt(np.pi / 2) * data_ven_ability['D'] + 1.7 * 10**(-3) * data['PRE_Time_2020'] * np.sqrt(100)
    data['E'] = 3.1536 * 10**(-3) * np.sqrt(np.pi / 2) * data_ven_ability['E'] + 1.7 * 10**(-3) * data['PRE_Time_2020'] * np.sqrt(100)
    data['F'] = 3.1536 * 10**(-3) * np.sqrt(np.pi / 2) * data_ven_ability['F'] + 1.7 * 10**(-3) * data['PRE_Time_2020'] * np.sqrt(100)

    data.drop(['PRE_Time_2020'], axis=1, inplace=True)

    data_accum = []

    for i in range(1, 13):
        data_i_mean = data[data.index.month == i].mean().round(1).to_frame()
        data_accum.append(data_i_mean)

    data_accum = pd.concat(data_accum, axis=1, ignore_index=True)

    # 增加月份
    data_accum.columns = [str(i) + '月' for i in range(1, 13)]

    # 季度总频数和年度总频数
    data_accum['春季'] = data_accum.iloc[:, 2:5].mean(axis=1).round(1)
    data_accum['夏季'] = data_accum.iloc[:, 5:8].mean(axis=1).round(1)
    data_accum['秋季'] = data_accum.iloc[:, 8:11].mean(axis=1).round(1)
    data_accum['冬季'] = data_accum.iloc[:, [0, 1, 11]].mean(axis=1).round(1)
    data_accum['全年'] = data_accum.iloc[:, 0:12].mean(axis=1).round(1)

    data_accum = data_accum.T

    def cond(values):
        conditions = [values > 30, values > 12, values > 7, values > 5, values > 3]
        return conditions

    choices = [1, 2, 3, 4, 5]

    data_accum.insert(loc=6, column='A-等级', value=np.select(cond(data_accum['A']), choices, default=6))
    data_accum.insert(loc=7, column='B-等级', value=np.select(cond(data_accum['B']), choices, default=6))
    data_accum.insert(loc=8, column='C-等级', value=np.select(cond(data_accum['C']), choices, default=6))
    data_accum.insert(loc=9, column='D-等级', value=np.select(cond(data_accum['D']), choices, default=6))
    data_accum.insert(loc=10, column='E-等级', value=np.select(cond(data_accum['E']), choices, default=6))
    data_accum.insert(loc=11, column='F-等级', value=np.select(cond(data_accum['F']), choices, default=6))

    data_accum.reset_index(inplace=True, drop=False)
    data_accum.rename(columns={'index': '月份'}, inplace=True)
    
    return data, data_accum


def ASI_caculate(post_monthly_df, data_ven_ability):
    data = pd.DataFrame(post_monthly_df['PRE_Time_2020'])

    data['A'] = 8.64 * 10**(-2) * (np.sqrt(np.pi / 2) * data_ven_ability['A'] + 0.17 * 10**(3) * data['PRE_Time_2020'] * np.sqrt(100)) * 0.075 / np.sqrt(100)
    data['B'] = 8.64 * 10**(-2) * (np.sqrt(np.pi / 2) * data_ven_ability['B'] + 0.17 * 10**(3) * data['PRE_Time_2020'] * np.sqrt(100)) * 0.075 / np.sqrt(100)
    data['C'] = 8.64 * 10**(-2) * (np.sqrt(np.pi / 2) * data_ven_ability['C'] + 0.17 * 10**(3) * data['PRE_Time_2020'] * np.sqrt(100)) * 0.075 / np.sqrt(100)
    data['D'] = 8.64 * 10**(-2) * (np.sqrt(np.pi / 2) * data_ven_ability['D'] + 0.17 * 10**(3) * data['PRE_Time_2020'] * np.sqrt(100)) * 0.075 / np.sqrt(100)
    data['E'] = 8.64 * 10**(-2) * (np.sqrt(np.pi / 2) * data_ven_ability['E'] + 0.17 * 10**(3) * data['PRE_Time_2020'] * np.sqrt(100)) * 0.075 / np.sqrt(100)
    data['F'] = 8.64 * 10**(-2) * (np.sqrt(np.pi / 2) * data_ven_ability['F'] + 0.17 * 10**(3) * data['PRE_Time_2020'] * np.sqrt(100)) * 0.075 / np.sqrt(100)

    data.drop(['PRE_Time_2020'], axis=1, inplace=True)

    data_accum = []

    for i in range(1, 13):
        data_i_mean = data[data.index.month == i].mean().round(1).to_frame()
        data_accum.append(data_i_mean)

    data_accum = pd.concat(data_accum, axis=1, ignore_index=True)

    # 增加月份
    data_accum.columns = [str(i) + '月' for i in range(1, 13)]

    # 季度总频数和年度总频数
    data_accum['春季'] = data_accum.iloc[:, 2:5].mean(axis=1).round(1)
    data_accum['夏季'] = data_accum.iloc[:, 5:8].mean(axis=1).round(1)
    data_accum['秋季'] = data_accum.iloc[:, 8:11].mean(axis=1).round(1)
    data_accum['冬季'] = data_accum.iloc[:, [0, 1, 11]].mean(axis=1).round(1)
    data_accum['全年'] = data_accum.iloc[:, 0:12].mean(axis=1).round(1)
    data_accum = data_accum.T
    
    # def cond(values):
    #     conditions = [values > 30, values > 12, values > 7, values > 5, values > 3]
    #     return conditions

    # choices = [1, 2, 3, 4, 5]
    # data_accum.insert(loc=6, column='A(对应等级)', value=np.select(cond(data_accum['A']), choices, default=6))
    # data_accum.insert(loc=7, column='B(对应等级)', value=np.select(cond(data_accum['B']), choices, default=6))
    # data_accum.insert(loc=8, column='C(对应等级)', value=np.select(cond(data_accum['C']), choices, default=6))
    # data_accum.insert(loc=9, column='D(对应等级)', value=np.select(cond(data_accum['D']), choices, default=6))
    # data_accum.insert(loc=10, column='E(对应等级)', value=np.select(cond(data_accum['E']), choices, default=6))
    # data_accum.insert(loc=11, column='F(对应等级)', value=np.select(cond(data_accum['F']), choices, default=6))
    data_accum.reset_index(inplace=True, drop=False)
    data_accum.rename(columns={'index': '月份'}, inplace=True)

    return data, data_accum


def pollute_run(post_monthly_df):

    # 污染系数
    basic_win_d_accum, basic_win_s_accum = basic_win_freq_statistics(post_monthly_df)
    
    # 检查返回值是否为None，如果是则污染系数部分设为None
    if basic_win_d_accum is None or basic_win_s_accum is None:
        result = None
    else:
        basic_win_d_accum.insert(loc=1, column='要素', value='风向频率(%)')
        basic_win_s_accum.insert(loc=1, column='要素', value='平均风速(m/s)')
        basic_win_d_accum.drop(['C'], axis=1, inplace=True)

        basic_wu_accum = round(basic_win_d_accum.iloc[:, 2::] / basic_win_s_accum.iloc[:, 2::], 2)
        basic_wu_accum.insert(loc=0, column='月份', value=basic_win_s_accum['月份'])
        basic_wu_accum.insert(loc=1, column='要素', value='污染系数')

        merged_rows = []

        for i in range(len(basic_win_d_accum)):
            merged_rows.append(basic_win_d_accum.iloc[i])
            merged_rows.append(basic_win_s_accum.iloc[i])
            merged_rows.append(basic_wu_accum.iloc[i])

        result = pd.concat(merged_rows, axis=1).transpose()

    # 混合层高度
    data_depth_mixed, depth_mixed_accum = depth_mixed_layer(post_monthly_df)

    data_ven_ability, ven_ability_accum = ven_ability(post_monthly_df, data_depth_mixed)

    data_asc, data_asc_accum = ASC_caculate(post_monthly_df, data_ven_ability)

    data_asi, data_asi_accum = ASI_caculate(post_monthly_df, data_ven_ability)

    return result, depth_mixed_accum, ven_ability_accum, data_asc_accum, data_asi_accum


if __name__ == '__main__':
    main_sta_ids = '56067'
    monthly_df = pd.read_csv(cfg.FILES.QH_DATA_MONTH, low_memory=False)
    monthly_df = monthly_df[monthly_df['Station_Id_C'] == int(main_sta_ids)]
    post_monthly_df = monthly_data_processing(monthly_df)
    p_c, depth_mixed_accum, ven_ability_accum, data_asc_accum, data_asi_accum = pollute_run(post_monthly_df)
