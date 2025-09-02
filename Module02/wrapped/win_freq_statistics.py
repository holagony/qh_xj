import logging
import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.data_processing import monthly_data_processing


def basic_win_freq_statistics(win_freq):
    '''
    风向频率以及风向对应的风速要素，累年各月统计，
    使用天擎上的月数据，要素名称为天擎上默认的名称
    月值要素：['Station_Id_C', 'Year', 'Mon', 'WIN_S_Avg_NNE', 'WIN_S_Avg_NE',  'WIN_S_Avg__W',
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
            basic_win_d_accum = basic_win_d_accum.to_dict(orient='records')

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
                basic_win_s_accum = basic_win_s_accum.to_dict(orient='records')

        except Exception as e:
            logging.exception(e)
            basic_win_s_accum = None

        finally:
            return basic_win_d_accum, basic_win_s_accum


if __name__ == '__main__':
    monthly_df = pd.read_csv(cfg.FILES.module2_month_CSV)
    post_monthly_df = monthly_data_processing(monthly_df)
    # post_monthly_df = None
    basic_win_d_accum, basic_win_s_accum = basic_win_freq_statistics(post_monthly_df)
