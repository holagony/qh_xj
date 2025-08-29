import os
import glob
import json
import numpy as np
import pandas as pd
import simplejson
import datetime
from datetime import timedelta
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_processing import daily_data_processing
from dateutil.relativedelta import relativedelta


def calc_climate_livable_factors(input_df):
    '''
    气候宜居禀赋的计算要素，使用日数据
    要素: TEM_Avg,TEM_Min,TEM_Max,PRE_Time_2020,RHU_Avg,WIN_S_2mi_Avg,SSH,PRS_Avg
    '''
    # 建立最后评价结果的array
    rank_result = np.zeros(19)

    #########################################################
    # 1.年适宜温度 T在[15,25]之间的天数
    def sample_tem1(x):
        x = np.array(x)
        values = np.where((x >= 15) & (x <= 25), 1, 0)
        return np.sum(values)

    tmp = input_df['TEM_Avg']
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_1 = None
        rank_result[0] = np.nan
        Part_A_1 = np.nan

    else:
        sample_data = input_df['TEM_Avg'].resample('1A', closed='right', label='right').apply(sample_tem1).reset_index()
        Part_A_1 = sample_data['TEM_Avg'].mean()
        sample_data.rename(columns={'index': 'Datetime'}, inplace=True)

        sample_data['日期'] = sample_data['Datetime'].dt.year
        sample_data.columns = ['Datetime', '历年适宜温度日数', '日期']
        output_table_1 = sample_data[['日期', '历年适宜温度日数']]
        output_table_1 = output_table_1.round(1).to_dict(orient='records')

        # 分级
        if Part_A_1 >= 150:
            rank_result[0] = 1

        elif Part_A_1 >= 120 and Part_A_1 < 150:
            rank_result[0] = 2

        elif Part_A_1 < 120:
            rank_result[0] = 3

    #########################################################
    # 2.7月平均最低气温
    tmp = input_df['TEM_Min']
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_2 = None
        rank_result[1] = np.nan
        Part_A_2 = np.nan

    else:
        sample_data = input_df['TEM_Min'].resample('1M', closed='right', label='right').mean()
        Part_A_2 = sample_data[sample_data.index.month == 7].mean()

        output_table_2 = sample_data[sample_data.index.month == 7].to_frame().reset_index()
        output_table_2.rename(columns={'index': 'Datetime'}, inplace=True)

        output_table_2['日期'] = output_table_2['Datetime'].dt.strftime('%Y-%m')
        output_table_2.columns = ['Datetime', '历年7月平均最低气温', '日期']
        output_table_2 = output_table_2[['日期', '历年7月平均最低气温']]
        output_table_2 = output_table_2.round(1).to_dict(orient='records')

        # 分级
        if Part_A_2 >= 10 and Part_A_2 <= 20:
            rank_result[1] = 1

        elif Part_A_2 > 20 and Part_A_2 <= 24:
            rank_result[1] = 2

        elif Part_A_2 < 10 or Part_A_2 > 24:
            rank_result[1] = 3

    #########################################################
    # 3.1月平均最高气温
    tmp = input_df['TEM_Max']
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_3 = None
        rank_result[2] = np.nan
        Part_A_3 = np.nan

    else:
        sample_data = input_df['TEM_Max'].resample('1M', closed='right', label='right').mean()
        Part_A_3 = sample_data[sample_data.index.month == 1].mean()

        output_table_3 = sample_data[sample_data.index.month == 1].to_frame().reset_index()
        output_table_3.rename(columns={'index': 'Datetime'}, inplace=True)

        output_table_3['日期'] = output_table_3['Datetime'].dt.strftime('%Y-%m')
        output_table_3.columns = ['Datetime', '历年1月平均最高气温', '日期']
        output_table_3 = output_table_3[['日期', '历年1月平均最高气温']]
        output_table_3 = output_table_3.round(1).to_dict(orient='records')

        # 分级
        if Part_A_3 >= 10:
            rank_result[2] = 1

        elif Part_A_3 >= 5 and Part_A_3 < 10:
            rank_result[2] = 2

        elif Part_A_3 < 5:
            rank_result[2] = 3

    #########################################################
    # 4.年平均气温日较差
    def sample_tem2(x):
        x = np.array(x)
        values = np.mean(x[:, 0] - x[:, 1])
        return values

    tmp = input_df[['TEM_Max', 'TEM_Min']]
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_4 = None
        rank_result[3] = np.nan
        Part_A_4 = np.nan

    else:
        sample_data = input_df.resample('1A', closed='right', label='right')['TEM_Max', 'TEM_Min'].apply(sample_tem2)
        Part_A_4 = sample_data.mean()

        output_table_4 = sample_data.to_frame().reset_index()
        output_table_4.rename(columns={'index': 'Datetime'}, inplace=True)

        output_table_4['日期'] = output_table_4['Datetime'].dt.strftime('%Y')
        output_table_4.columns = ['Datetime', '历年平均气温日较差', '日期']
        output_table_4 = output_table_4[['日期', '历年平均气温日较差']]
        output_table_4 = output_table_4.round(1).to_dict(orient='records')

        # 分级
        if Part_A_4 >= 8 and Part_A_4 <= 10:
            rank_result[3] = 1

        elif (Part_A_4 >= 6 and Part_A_4 < 8) or (Part_A_4 > 10 and Part_A_4 <= 14):
            rank_result[3] = 2

        elif Part_A_4 < 6 or Part_A_4 > 14:
            rank_result[3] = 3

    #########################################################
    # 5.夏季平均气温日较差
    def sample_tem3(x):
        x = x[(x.index.month == 6) ^ (x.index.month == 7) ^ (x.index.month == 8)]  # 选取每年夏季三个月
        x = np.array(x)
        values = np.mean(x[:, 0] - x[:, 1])
        return values

    tmp = input_df[['TEM_Max', 'TEM_Min']]
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_5 = None
        rank_result[4] = np.nan
        Part_A_5 = np.nan

    else:
        sample_data = input_df.resample('1A', closed='right', label='right')['TEM_Max', 'TEM_Min'].apply(sample_tem3)
        Part_A_5 = sample_data.mean()

        output_table_5 = sample_data.to_frame().reset_index()
        output_table_5.rename(columns={'index': 'Datetime'}, inplace=True)

        output_table_5['日期'] = output_table_5['Datetime'].dt.strftime('%Y')
        output_table_5.columns = ['Datetime', '历年夏季平均气温日较差', '日期']
        output_table_5 = output_table_5[['日期', '历年夏季平均气温日较差']]
        output_table_5 = output_table_5.round(1).to_dict(orient='records')

        # 分级
        if Part_A_5 >= 10:
            rank_result[4] = 1

        elif Part_A_5 >= 8 and Part_A_5 < 10:
            rank_result[4] = 2

        elif Part_A_5 < 8:
            rank_result[4] = 3

    #########################################################
    # 6.冬季平均气温日较差
    def sample_tem4(x):
        x = x[(x.index.month == 1) ^ (x.index.month == 2) ^ (x.index.month == 12)]  # 选取每年冬季三个月
        x = np.array(x)
        values = np.mean(x[:, 0] - x[:, 1])
        return values

    tmp = input_df[['TEM_Max', 'TEM_Min']]
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_6 = None
        rank_result[5] = np.nan
        Part_A_6 = np.nan

    else:
        sample_data = input_df.resample('1A', closed='right', label='right')['TEM_Max', 'TEM_Min'].apply(sample_tem4)
        Part_A_6 = sample_data.mean()

        output_table_6 = sample_data.to_frame().reset_index()
        output_table_6.rename(columns={'index': 'Datetime'}, inplace=True)

        output_table_6['日期'] = output_table_6['Datetime'].dt.strftime('%Y')
        output_table_6.columns = ['Datetime', '历年冬季平均气温日较差', '日期']
        output_table_6 = output_table_6[['日期', '历年冬季平均气温日较差']]
        output_table_6 = output_table_6.round(1).to_dict(orient='records')

        # 分级
        if Part_A_6 <= 8:
            rank_result[5] = 1

        elif Part_A_6 > 8 and Part_A_6 < 12:
            rank_result[5] = 2

        elif Part_A_6 > 12:
            rank_result[5] = 3

    #########################################################
    # 7.年降水量
    tmp = input_df['PRE_Time_2020']
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_7 = None
        rank_result[6] = np.nan
        Part_A_7 = np.nan

    else:
        sample_data = input_df['PRE_Time_2020'].resample('1A', closed='right', label='right').sum()
        Part_A_7 = sample_data.mean()

        output_table_7 = sample_data.to_frame().reset_index()
        output_table_7.rename(columns={'index': 'Datetime'}, inplace=True)

        output_table_7['日期'] = output_table_7['Datetime'].dt.strftime('%Y')
        output_table_7.columns = ['Datetime', '历年总降水量', '日期']
        output_table_7 = output_table_7[['日期', '历年总降水量']]
        output_table_7 = output_table_7.round(1).to_dict(orient='records')

        # 分级
        if Part_A_7 >= 800 and Part_A_7 <= 1200:
            rank_result[6] = 1

        elif (Part_A_7 >= 400 and Part_A_7 < 800) or (Part_A_7 > 1200 and Part_A_7 <= 1600):
            rank_result[6] = 2

        elif Part_A_7 < 400 or Part_A_7 > 1600:
            rank_result[6] = 3

    #########################################################
    # 8.年降水变差系数
    def sample_pre1(x):
        # modulus_ratio = x/np.mean(x) # 模比系数
        # Cv = np.sqrt(np.sum((modulus_ratio-1)**2)/(len(x)-1)) # 变差系数
        x = np.array(x)
        Ex = np.mean(x)  # 均值
        Std = np.std(x, ddof=1)
        Cv = Std / Ex
        return Cv

    tmp = input_df['PRE_Time_2020']
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_8 = None
        rank_result[7] = np.nan
        Part_A_8 = np.nan

    else:
        sample_data = input_df['PRE_Time_2020'].resample('1A', closed='right', label='right').apply(sample_pre1)
        Part_A_8 = sample_data.mean()

        output_table_8 = sample_data.to_frame().reset_index()
        output_table_8.rename(columns={'index': 'Datetime'}, inplace=True)

        output_table_8['日期'] = output_table_8['Datetime'].dt.strftime('%Y')
        output_table_8.columns = ['Datetime', '历年降水变差系数', '日期']
        output_table_8 = output_table_8[['日期', '历年降水变差系数']]
        output_table_8 = output_table_8.round(1).to_dict(orient='records')

        # 分级
        if Part_A_8 <= 0.18:
            rank_result[7] = 1

        elif Part_A_8 > 0.18 and Part_A_8 <= 0.22:
            rank_result[7] = 2

        elif Part_A_8 > 0.22:
            rank_result[7] = 3

    #########################################################
    # 9.季节降水均匀度 冬季降水量与夏季降水量之比
    def sample_pre2(x):
        x1 = x[(x.index.month == 1) ^ (x.index.month == 2) ^ (x.index.month == 12)]  # 选取每年冬季三个月
        x2 = x[(x.index.month == 6) ^ (x.index.month == 7) ^ (x.index.month == 8)]  # 选取每年夏季三个月
        return x1.sum() / x2.sum()

    tmp = input_df['PRE_Time_2020']
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_9 = None
        rank_result[8] = np.nan
        Part_A_9 = np.nan

    else:
        sample_data = input_df['PRE_Time_2020'].resample('1A', closed='right', label='right').apply(sample_pre2)
        Part_A_9 = sample_data.mean()

        output_table_9 = sample_data.to_frame().reset_index()
        output_table_9.rename(columns={'index': 'Datetime'}, inplace=True)

        output_table_9['日期'] = output_table_9['Datetime'].dt.strftime('%Y')
        output_table_9.columns = ['Datetime', '历年季节降水均匀度', '日期']
        output_table_9 = output_table_9[['日期', '历年季节降水均匀度']]
        output_table_9 = output_table_9.round(1).to_dict(orient='records')

        # 分级
        if Part_A_9 >= 0.15:
            rank_result[8] = 1

        elif Part_A_9 >= 0.05 and Part_A_9 < 0.15:
            rank_result[8] = 2

        elif Part_A_9 < 0.05:
            rank_result[8] = 3

    #########################################################
    # 10.年适宜降水日数 [0.1,10)
    def sample_pre3(x):
        x = np.array(x)
        values = np.where((x >= 0.1) & (x < 10), 1, 0)
        return np.sum(values)

    tmp = input_df['PRE_Time_2020']
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_10 = None
        rank_result[9] = np.nan
        Part_A_10 = np.nan

    else:
        sample_data = input_df['PRE_Time_2020'].resample('1A', closed='right', label='right').apply(sample_pre3).reset_index()
        sample_data.rename(columns={'index': 'Datetime'}, inplace=True)

        sample_data['日期'] = sample_data['Datetime'].dt.year
        sample_data.columns = ['Datetime', '历年适宜降水日数', '日期']

        # output
        Part_A_10 = sample_data['历年适宜降水日数'].mean()
        output_table_10 = sample_data[['日期', '历年适宜降水日数']]
        output_table_10 = output_table_10.round(1).to_dict(orient='records')

        # 分级
        if Part_A_10 >= 90 and Part_A_10 <= 120:
            rank_result[9] = 1

        elif (Part_A_10 >= 60 and Part_A_10 < 90) or (Part_A_10 > 120 and Part_A_10 <= 150):
            rank_result[9] = 2

        elif Part_A_10 < 60 or Part_A_10 > 150:
            rank_result[9] = 3

    #########################################################
    # 11.年平均相对湿度
    tmp = input_df['RHU_Avg']
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_11 = None
        rank_result[10] = np.nan
        Part_A_11 = np.nan

    else:
        sample_data = input_df['RHU_Avg'].resample('1A', closed='right', label='right').mean()
        Part_A_11 = sample_data.mean() * 100

        output_table_11 = sample_data.to_frame().reset_index()
        output_table_11.rename(columns={'index': 'Datetime'}, inplace=True)

        output_table_11['日期'] = output_table_11['Datetime'].dt.strftime('%Y')
        output_table_11.columns = ['Datetime', '历年平均相对湿度', '日期']
        output_table_11 = output_table_11[['日期', '历年平均相对湿度']]
        output_table_11['历年平均相对湿度'] = output_table_11['历年平均相对湿度'] * 100
        output_table_11 = output_table_11.round(1).to_dict(orient='records')

        # 分级
        if Part_A_11 >= 65 and Part_A_11 <= 75:
            rank_result[10] = 1

        elif (Part_A_11 >= 50 and Part_A_11 < 65) or (Part_A_11 > 75 and Part_A_11 <= 80):
            rank_result[10] = 2

        elif Part_A_11 < 50 or Part_A_11 > 80:
            rank_result[10] = 3

    #########################################################
    # 12.夏季平均相对湿度
    def sample_rh1(x):
        x = x[(x.index.month == 6) ^ (x.index.month == 7) ^ (x.index.month == 8)]  # 选取每年夏季三个月
        return x.mean()

    tmp = input_df['RHU_Avg']
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_12 = None
        rank_result[11] = np.nan
        Part_A_12 = np.nan

    else:
        sample_data = input_df['RHU_Avg'].resample('1A', closed='right', label='right').apply(sample_rh1)
        Part_A_12 = sample_data.mean() * 100

        output_table_12 = sample_data.to_frame().reset_index()
        output_table_12.rename(columns={'index': 'Datetime'}, inplace=True)

        output_table_12['日期'] = output_table_12['Datetime'].dt.strftime('%Y')
        output_table_12.columns = ['Datetime', '历年夏季平均相对湿度', '日期']
        output_table_12 = output_table_12[['日期', '历年夏季平均相对湿度']]
        output_table_12['历年夏季平均相对湿度'] = output_table_12['历年夏季平均相对湿度'] * 100
        output_table_12 = output_table_12.round(1).to_dict(orient='records')

        # 分级
        if Part_A_12 <= 70:
            rank_result[11] = 1

        elif Part_A_12 > 70 and Part_A_12 <= 80:
            rank_result[11] = 2

        elif Part_A_12 > 80:
            rank_result[11] = 3

    #########################################################
    # 13.年适宜湿度日数 [0.5,0.8]
    def sample_rh2(x):
        x = np.array(x)
        values = np.where((x >= 0.5) & (x <= 0.8), 1, 0)
        return np.sum(values)

    tmp = input_df['RHU_Avg']
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_13 = None
        output_table_13_accum = None
        rank_result[12] = np.nan
        Part_A_13 = np.nan

    else:
        sample_data = input_df['RHU_Avg'].resample('1A', closed='right', label='right').apply(sample_rh2).reset_index()
        sample_data.rename(columns={'index': 'Datetime'}, inplace=True)

        sample_data['日期'] = sample_data['Datetime'].dt.year
        sample_data.columns = ['Datetime', '历年适宜湿度日数', '日期']

        # 历年结果output
        Part_A_13 = sample_data['历年适宜湿度日数'].mean()
        output_table_13 = sample_data[['日期', '历年适宜湿度日数']]
        output_table_13 = output_table_13.round(1).to_dict(orient='records')

        # 累年各月结果output
        sample_data = input_df['RHU_Avg'].resample('1M', closed='right', label='right').apply(sample_rh2)
        rh_day_accum = []

        for i in range(1, 13):
            month_i_mean = sample_data[sample_data.index.month == i].mean()
            rh_day_accum.append(month_i_mean)

        rh_day_accum = pd.DataFrame(rh_day_accum)
        rh_day_accum.columns = ['累年各月适宜湿度日数']
        rh_day_accum['日期'] = [str(i) + '月' for i in range(1, 13)]
        output_table_13_accum = rh_day_accum[['日期', '累年各月适宜湿度日数']]
        output_table_13_accum = output_table_13_accum.round(1).to_dict(orient='records')

        # 分级
        if Part_A_13 >= 210:
            rank_result[12] = 1

        elif Part_A_13 >= 180 and Part_A_13 < 210:
            rank_result[12] = 2

        elif Part_A_13 < 180:
            rank_result[12] = 3

    #########################################################
    # 14.年平均风速
    tmp = input_df['WIN_S_2mi_Avg']
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_14 = None
        rank_result[13] = np.nan
        Part_A_14 = np.nan

    else:
        sample_data = input_df['WIN_S_2mi_Avg'].resample('1A', closed='right', label='right').mean()
        Part_A_14 = sample_data.mean()

        output_table_14 = sample_data.to_frame().reset_index()
        output_table_14.rename(columns={'index': 'Datetime'}, inplace=True)

        output_table_14['日期'] = output_table_14['Datetime'].dt.strftime('%Y')
        output_table_14.columns = ['Datetime', '历年平均风速', '日期']
        output_table_14 = output_table_14[['日期', '历年平均风速']]
        output_table_14 = output_table_14.round(1).to_dict(orient='records')

        # 分级
        if Part_A_14 >= 1.5 and Part_A_14 <= 2.5:
            rank_result[13] = 1

        elif (Part_A_14 >= 1 and Part_A_14 < 1.5) or (Part_A_14 > 2.5 and Part_A_14 <= 3.3):
            rank_result[13] = 2

        elif Part_A_14 < 1 or Part_A_14 > 3.3:
            rank_result[13] = 3

    #########################################################
    # 15.年适宜风日数 [0.3,3.3]
    def sample_win1(x):
        x = np.array(x)
        values = np.where((x >= 0.3) & (x <= 3.3), 1, 0)
        return np.sum(values)

    tmp = input_df['WIN_S_2mi_Avg']
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_15 = None
        output_table_15_accum = None
        rank_result[14] = np.nan
        Part_A_15 = np.nan

    else:
        sample_data = input_df['WIN_S_2mi_Avg'].resample('1A', closed='right', label='right').apply(sample_win1).reset_index()
        sample_data.rename(columns={'index': 'Datetime'}, inplace=True)

        sample_data['日期'] = sample_data['Datetime'].dt.year
        sample_data.columns = ['Datetime', '历年适宜风日数', '日期']

        # 历年结果output
        Part_A_15 = sample_data['历年适宜风日数'].mean()
        output_table_15 = sample_data[['日期', '历年适宜风日数']]
        output_table_15 = output_table_15.round(1).to_dict(orient='records')

        # 累年各月结果output
        sample_data = input_df['WIN_S_2mi_Avg'].resample('1M', closed='right', label='right').apply(sample_win1)
        win_day_accum = []

        for i in range(1, 13):
            month_i_mean = sample_data[sample_data.index.month == i].mean()
            win_day_accum.append(month_i_mean)

        win_day_accum = pd.DataFrame(win_day_accum)
        win_day_accum.columns = ['累年各月适宜风日数']
        win_day_accum['日期'] = [str(i) + '月' for i in range(1, 13)]
        output_table_15_accum = win_day_accum[['日期', '累年各月适宜风日数']]
        output_table_15_accum = output_table_15_accum.round(1).to_dict(orient='records')

        # 分级
        if Part_A_15 >= 300:
            rank_result[14] = 1

        elif Part_A_15 >= 240 and Part_A_15 < 300:
            rank_result[14] = 2

        elif Part_A_15 < 240:
            rank_result[14] = 3

    #########################################################
    # 16.夏季日照时数
    def sample_ssd1(x):
        x = x[(x.index.month == 6) ^ (x.index.month == 7) ^ (x.index.month == 8)]  # 选取每年夏季三个月
        return x.sum()

    tmp = input_df['SSH']
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_16 = None
        rank_result[15] = np.nan
        Part_A_16 = np.nan

    else:
        sample_data = input_df['SSH'].resample('1A', closed='right', label='right').apply(sample_ssd1)
        Part_A_16 = sample_data.mean()

        output_table_16 = sample_data.to_frame().reset_index()
        output_table_16.rename(columns={'index': 'Datetime'}, inplace=True)

        output_table_16['日期'] = output_table_16['Datetime'].dt.strftime('%Y')
        output_table_16.columns = ['Datetime', '历年夏季日照时数', '日期']
        output_table_16 = output_table_16[['日期', '历年夏季日照时数']]
        output_table_16 = output_table_16.round(1).to_dict(orient='records')

        # 分级
        if Part_A_16 >= 500 and Part_A_16 <= 700:
            rank_result[15] = 1

        elif (Part_A_16 >= 400 and Part_A_16 < 500) or (Part_A_16 > 700 and Part_A_16 <= 800):
            rank_result[15] = 2

        elif Part_A_16 < 400 or Part_A_16 > 800:
            rank_result[15] = 3

    #########################################################
    # 17.冬季日照时数
    def sample_ssd2(x):
        x = x[(x.index.month == 1) ^ (x.index.month == 2) ^ (x.index.month == 12)]
        return x.sum()

    tmp = input_df['SSH']
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_17 = None
        rank_result[16] = np.nan
        Part_A_17 = np.nan

    else:
        sample_data = input_df['SSH'].resample('1A', closed='right', label='right').apply(sample_ssd2)
        Part_A_17 = sample_data.mean()

        output_table_17 = sample_data.to_frame().reset_index()
        output_table_17.rename(columns={'index': 'Datetime'}, inplace=True)

        output_table_17['日期'] = output_table_17['Datetime'].dt.strftime('%Y')
        output_table_17.columns = ['Datetime', '历年冬季日照时数', '日期']
        output_table_17 = output_table_17[['日期', '历年冬季日照时数']]
        output_table_17 = output_table_17.round(1).to_dict(orient='records')

        # 分级
        if Part_A_17 >= 450:
            rank_result[16] = 1

        elif Part_A_17 >= 250 and Part_A_17 < 450:
            rank_result[16] = 2

        elif Part_A_17 < 250:
            rank_result[16] = 3

    #########################################################
    # 18.大气含氧量 本站年平均大气压与标准大气压之比
    tmp = input_df['PRS_Avg']
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_18 = None
        rank_result[17] = np.nan
        Part_A_18 = np.nan

    else:
        standard_prs = 1013.25  # hpa
        sample_data = input_df['PRS_Avg'].resample('1A', closed='right', label='right').mean()
        sample_data = sample_data / standard_prs
        Part_A_18 = sample_data.mean() * 100

        output_table_18 = sample_data.to_frame().reset_index()
        output_table_18.rename(columns={'index': 'Datetime'}, inplace=True)

        output_table_18['日期'] = output_table_18['Datetime'].dt.strftime('%Y')
        output_table_18.columns = ['Datetime', '历年大气含氧量', '日期']
        output_table_18 = output_table_18[['日期', '历年大气含氧量']]
        output_table_18['历年大气含氧量'] = output_table_18['历年大气含氧量'] * 100
        output_table_18 = output_table_18.round(1).to_dict(orient='records')

        # 分级
        if Part_A_18 >= 85:
            rank_result[17] = 1

        elif Part_A_18 >= 75 and Part_A_18 < 85:
            rank_result[17] = 2

        elif Part_A_18 < 75:
            rank_result[17] = 3

    #########################################################
    # 19.春秋季总长 一年中春季日数与秋季日数之和
    def sample_season(x):

        moving_avg = x.rolling(5, min_periods=1).mean()

        try:
            # 春
            spring = moving_avg.rolling(5).agg(lambda x: min(x) >= 10).to_frame()
            spring_agg_idx = spring[spring['TEM_Avg'] == 1].index[0]  # 第一个滑动序列连续5天都符合条件的日期
            spring_move_idx = spring_agg_idx - relativedelta(days=4)  # 往前倒4天，这一天开始滑动平均序列开始大于等于10，连续5天
            seq = x[spring_move_idx - relativedelta(days=4):spring_move_idx + relativedelta(days=4)]  # seq为第一个原始数据序列(9天)，对其滑动平均后连续5天都大于等于10
            spring_start = seq[seq >= 10].index[0]  # seq第一个大于10的日期为春季起始日

            # 夏
            summer = moving_avg.rolling(5).agg(lambda x: min(x) >= 22).to_frame()
            summer_agg_idx = summer[summer['TEM_Avg'] == 1].index[0]
            summer_move_idx = summer_agg_idx - relativedelta(days=4)
            seq = x[summer_move_idx - relativedelta(days=4):summer_move_idx + relativedelta(days=4)]
            summer_start = seq[seq >= 22].index[0]

            # 春季日数
            spring_days = (summer_start - spring_start).days

            # 秋
            autumn = moving_avg.rolling(5).agg(lambda x: max(x) < 22).to_frame()
            autumn = autumn[autumn.index.month >= 9]
            autumn_agg_idx = autumn[autumn['TEM_Avg'] == 1].index[0]
            autumn_move_idx = autumn_agg_idx - relativedelta(days=4)
            seq = x[autumn_move_idx - relativedelta(days=4):autumn_move_idx + relativedelta(days=4)]
            autumn_start = seq[seq < 22].index[0]

            # 冬
            winter = moving_avg.rolling(5).agg(lambda x: max(x) < 10).to_frame()
            try:
                winter = winter[winter.index.month >= 11]
                winter_agg_idx = winter[winter['TEM_Avg'] == 1].index[0]
                winter_move_idx = winter_agg_idx - relativedelta(days=4)
                seq = x[winter_move_idx - relativedelta(days=4):winter_move_idx + relativedelta(days=4)]
                winter_start = seq[seq < 10].index[0]
                autumn_days = (winter_start - autumn_start).days

            except:
                winter = winter[winter.index.month.isin([1, 2])]
                winter_agg_idx = winter[winter['TEM_Avg'] == 1].index[0]
                winter_move_idx = winter_agg_idx - relativedelta(days=4)
                seq = x[winter_move_idx - relativedelta(days=4):winter_move_idx + relativedelta(days=4)]
                winter_start = seq[seq < 10].index[0]

                year_last = pd.to_datetime(datetime.date(autumn_start.year, 12, 31))
                year_first = pd.to_datetime(datetime.date(autumn_start.year, 1, 1))
                autumn_days = (year_last - autumn_start).days + 1 + (winter_start - year_first).days

            # print(spring_start)
            # print(summer_start)
            # print(autumn_start)
            # print(winter_start)
            # print('-------------------')
            return spring_days + autumn_days

        except Exception as e:
            # msg = '该年数据不符合QXT152-2012划分标准'
            return np.nan

    tmp = input_df['TEM_Avg']
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_19 = None
        rank_result[18] = np.nan
        Part_A_19 = np.nan

    else:
        sample_data = input_df['TEM_Avg'].resample('1A', closed='right', label='right').apply(sample_season)
        Part_A_19 = sample_data.mean()

        output_table_19 = sample_data.to_frame().reset_index()
        output_table_19.rename(columns={'index': 'Datetime'}, inplace=True)

        output_table_19['日期'] = output_table_19['Datetime'].dt.strftime('%Y')
        output_table_19.columns = ['Datetime', '历年春秋季总长', '日期']
        output_table_19 = output_table_19[['日期', '历年春秋季总长']]
        output_table_19 = output_table_19.round(1).to_dict(orient='records')

        # 分级
        if Part_A_19 >= 150:
            rank_result[18] = 1

        elif Part_A_19 >= 120 and Part_A_19 < 150:
            rank_result[18] = 2

        elif Part_A_19 < 120:
            rank_result[18] = 3

    #########################################################
    # 气候宜居评价最终结果
    if np.all(rank_result == np.nan):
        rank_result_df = None

    else:
        rank_result_df = pd.DataFrame(rank_result, columns=['评价等级'])
        rank_result_df['选取因子'] = ['年适宜温度日数', '7月平均最低气温', '1月平均最高气温', '平均气温日较差', '夏季平均气温日较差', '冬季平均气温日较差', '年降水量', 
                                  '年降水变差系数', '季节降水均匀度', '年适宜降水日数', '年平均相对湿度', '夏季平均相对湿度', 
                                  '年适宜湿度日数', '年平均风速', '年适宜风日数', '夏季日照时数', '东季日照时数', '大气含氧量', '春秋季总长']
        rank_result_df = rank_result_df[['选取因子', '评价等级']]
        rank_result_df['因子数值'] = [Part_A_1, Part_A_2, Part_A_3, Part_A_4, Part_A_5, Part_A_6, Part_A_7, Part_A_8, Part_A_9, Part_A_10, Part_A_11, Part_A_12, Part_A_13, Part_A_14, Part_A_15, Part_A_16, Part_A_17, Part_A_18, Part_A_19]
        rank_result_df['单位'] = ['d','°C','°C','°C','°C','°C','mm',
                                np.nan,np.nan,'d','%','%',
                                'd','m/s','d','h','h','%','d']
        rank_result_df = rank_result_df.round(1).to_dict(orient='records')

    # 创建保存字典
    result_dict = edict()

    tables = edict()
    tables['历年适宜温度日数'] = output_table_1
    tables['历年7月平均最低气温'] = output_table_2
    tables['历年1月平均最高气温'] = output_table_3
    tables['历年平均气温日较差'] = output_table_4
    tables['历年夏季平均气温日较差'] = output_table_5
    tables['历年冬季平均气温日较差'] = output_table_6
    tables['历年总降水量'] = output_table_7
    tables['历年降水变差系数'] = output_table_8
    tables['历年季节降水均匀度'] = output_table_9
    tables['历年适宜降水日数'] = output_table_10
    tables['历年平均相对湿度'] = output_table_11
    tables['历年夏季平均相对湿度'] = output_table_12
    tables['历年适宜湿度日数'] = output_table_13
    tables['累年各月适宜湿度日数'] = output_table_13_accum
    tables['历年平均风速'] = output_table_14
    tables['历年适宜风日数'] = output_table_15
    tables['累年各月适宜风日数'] = output_table_15_accum
    tables['历年夏季日照时数'] = output_table_16
    tables['历年冬季日照时数'] = output_table_17
    tables['历年大气含氧量'] = output_table_18
    tables['历年春秋季总长'] = output_table_19

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
    result = calc_climate_livable_factors(daily_df)

    # sample_data = post_daily_df[post_daily_df['Year']==2000]['TEM_Avg']
    # moving_avg = sample_data.rolling(5, min_periods=1).mean()

    # # 春夏
    # spring = moving_avg.rolling(5).agg(lambda x: min(x) >= 10).to_frame()
    # spring_agg_idx = spring[spring['TEM_Avg'] == 1].index[0]
    # spring_move_idx = spring_agg_idx-relativedelta(days=4) # 这一天开始滑动平均序列开始大于等于10，连续5天
    # seq = sample_data[spring_move_idx-relativedelta(days=4):spring_move_idx+relativedelta(days=4)] # 这个原始数据序列(9天)对应滑动平均后的都大于等于10度的5天
    # seq_idx = seq[seq>=10].index[0]
