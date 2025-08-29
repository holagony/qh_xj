import simplejson
import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_processing import daily_data_processing


def calc_climate_disadvantage_factors(input_df):
    '''
    计算气候不利因子，并分级得到评估结果，使用日数据
    要素: TEM_Max,TEM_Min,PRE_Time_2020,WIN_S_Max,WIN_S_2mi_Avg,FlSa,SaSt,Haze,Hail,Thund,Tord,Squa
    '''
    # 建立最后评价结果的array
    rank_result = np.zeros(9)

    #############################################
    # 1.年高温日数 >=35
    def sample_tem5(x):
        x = np.array(x)
        values = np.where(x >= 35, 1, 0)
        return np.sum(values)

    tmp = input_df['TEM_Max']
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_1 = None
        output_table_2 = None
        rank_result[0] = np.nan

    else:
        # 历年结果output
        sample_data = input_df['TEM_Max'].resample('1A', closed='right', label='right').apply(sample_tem5).reset_index()
        sample_data.rename(columns={'index': 'Datetime'}, inplace=True)

        sample_data['日期'] = sample_data['Datetime'].dt.year
        sample_data.columns = ['Datetime', '历年高温日数', '日期']
        Part_B_1 = sample_data['历年高温日数'].mean()
        output_table_1 = sample_data[['日期', '历年高温日数']]
        output_table_1 = output_table_1.round(1).to_dict(orient='records')

        # 累年各月结果output
        sample_data = input_df['TEM_Max'].resample('1M', closed='right', label='right').apply(sample_tem5)
        hot_day_accum = []

        for i in range(1, 13):
            month_i_mean = sample_data[sample_data.index.month == i].mean()
            hot_day_accum.append(month_i_mean)

        hot_day_accum = pd.DataFrame(hot_day_accum)
        hot_day_accum.columns = ['累年各月平均高温日数']
        hot_day_accum['日期'] = [str(i) + '月' for i in range(1, 13)]
        output_table_2 = hot_day_accum[['日期', '累年各月平均高温日数']]
        output_table_2 = output_table_2.round(1).to_dict(orient='records')

        # 分级
        if Part_B_1 <= 3:
            rank_result[0] = 1

        elif Part_B_1 > 3 and Part_B_1 <= 15:
            rank_result[0] = 2

        elif Part_B_1 > 15:
            rank_result[0] = 3

    #############################################
    # 2.年寒冷日数 <=-10
    def sample_tem6(x):
        x = np.array(x)
        values = np.where(x <= -10, 1, 0)
        return np.sum(values)

    tmp = input_df['TEM_Min']
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_3 = None
        output_table_4 = None
        rank_result[1] = np.nan

    else:
        # 历年结果output
        sample_data = input_df['TEM_Min'].resample('1A', closed='right', label='right').apply(sample_tem6).reset_index()
        sample_data.rename(columns={'index': 'Datetime'}, inplace=True)

        sample_data['日期'] = sample_data['Datetime'].dt.year
        sample_data.columns = ['Datetime', '历年寒冷日数', '日期']
        Part_B_2 = sample_data['历年寒冷日数'].mean()
        output_table_3 = sample_data[['日期', '历年寒冷日数']]
        output_table_3 = output_table_3.round(1).to_dict(orient='records')

        # 累年各月结果output
        sample_data = input_df['TEM_Min'].resample('1M', closed='right', label='right').apply(sample_tem6)
        cold_day_accum = []

        for i in range(1, 13):
            month_i_mean = sample_data[sample_data.index.month == i].mean()
            cold_day_accum.append(month_i_mean)

        cold_day_accum = pd.DataFrame(cold_day_accum)
        cold_day_accum.columns = ['累年各月平均寒冷日数']
        cold_day_accum['日期'] = [str(i) + '月' for i in range(1, 13)]
        output_table_4 = cold_day_accum[['日期', '累年各月平均寒冷日数']]
        output_table_4 = output_table_4.round(1).to_dict(orient='records')

        # 分级
        if Part_B_2 <= 5:
            rank_result[1] = 1

        elif Part_B_2 > 5 and Part_B_1 <= 60:
            rank_result[1] = 2

        elif Part_B_2 > 60:
            rank_result[1] = 3

    #############################################
    # 3.年大雨日数 >=25
    def sample_pre3(x):
        x = np.array(x)
        values = np.where(x >= 25, 1, 0)
        return np.sum(values)

    tmp = input_df['PRE_Time_2020']
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_5 = None
        output_table_6 = None
        rank_result[2] = np.nan

    else:
        # 历年结果output
        sample_data = input_df['PRE_Time_2020'].resample('1A', closed='right', label='right').apply(sample_pre3).reset_index()
        sample_data.rename(columns={'index': 'Datetime'}, inplace=True)

        sample_data['日期'] = sample_data['Datetime'].dt.year
        sample_data.columns = ['Datetime', '历年大雨日数', '日期']
        Part_B_3 = sample_data['历年大雨日数'].mean()
        output_table_5 = sample_data[['日期', '历年大雨日数']]
        output_table_5 = output_table_5.round(1).to_dict(orient='records')

        # 累年各月结果output
        sample_data = input_df['PRE_Time_2020'].resample('1M', closed='right', label='right').apply(sample_pre3)
        rain_day_accum = []

        for i in range(1, 13):
            month_i_mean = sample_data[sample_data.index.month == i].mean()
            rain_day_accum.append(month_i_mean)

        rain_day_accum = pd.DataFrame(rain_day_accum)
        rain_day_accum.columns = ['累年各月平均大雨日数']
        rain_day_accum['日期'] = [str(i) + '月' for i in range(1, 13)]
        output_table_6 = rain_day_accum[['日期', '累年各月平均大雨日数']]
        output_table_6 = output_table_6.round(1).to_dict(orient='records')

        # 分级
        if Part_B_3 <= 3:
            rank_result[2] = 1

        elif Part_B_3 > 3 and Part_B_3 <= 15:
            rank_result[2] = 2

        elif Part_B_3 > 15:
            rank_result[2] = 3

    #############################################
    # 4.年无雨日数 <0.1
    def sample_pre4(x):
        x = np.array(x)
        values = np.where(x < 0.1, 1, 0)
        return np.sum(values)

    tmp = input_df['PRE_Time_2020']
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_7 = None
        output_table_8 = None
        rank_result[3] = np.nan

    else:
        # 历年结果output
        sample_data = input_df['PRE_Time_2020'].resample('1A', closed='right', label='right').apply(sample_pre4).reset_index()
        sample_data.rename(columns={'index': 'Datetime'}, inplace=True)

        sample_data['日期'] = sample_data['Datetime'].dt.year
        sample_data.columns = ['Datetime', '历年无雨日数', '日期']
        Part_B_4 = sample_data['历年无雨日数'].mean()
        output_table_7 = sample_data[['日期', '历年无雨日数']]
        output_table_7 = output_table_7.round(1).to_dict(orient='records')

        # 累年各月结果output
        sample_data = input_df['PRE_Time_2020'].resample('1M', closed='right', label='right').apply(sample_pre4)
        no_rain_accum = []

        for i in range(1, 13):
            month_i_mean = sample_data[sample_data.index.month == i].mean()
            no_rain_accum.append(month_i_mean)

        no_rain_accum = pd.DataFrame(no_rain_accum)
        no_rain_accum.columns = ['累年各月平均无雨日数']
        no_rain_accum['日期'] = [str(i) + '月' for i in range(1, 13)]
        output_table_8 = no_rain_accum[['日期', '累年各月平均无雨日数']]
        output_table_8 = output_table_8.round(1).to_dict(orient='records')

        # 分级
        if Part_B_4 <= 210:
            rank_result[3] = 1

        elif Part_B_4 > 210 and Part_B_3 <= 270:
            rank_result[3] = 2

        elif Part_B_4 > 270:
            rank_result[3] = 3

    #############################################
    # 5.年强风日数 >=10.8
    def sample_win2(x):
        x = np.array(x)
        values = np.where(x >= 10.8, 1, 0)
        return np.sum(values)

    tmp = input_df['WIN_S_Max']
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_9 = None
        output_table_10 = None
        rank_result[4] = np.nan

    else:
        # 历年结果output
        sample_data = input_df['WIN_S_Max'].resample('1A', closed='right', label='right').apply(sample_win2).reset_index()
        sample_data.rename(columns={'index': 'Datetime'}, inplace=True)

        sample_data['日期'] = sample_data['Datetime'].dt.year
        sample_data.columns = ['Datetime', '历年强风日数', '日期']
        Part_B_5 = sample_data['历年强风日数'].mean()
        output_table_9 = sample_data[['日期', '历年强风日数']]
        output_table_9 = output_table_9.round(1).to_dict(orient='records')

        # 累年各月结果output
        sample_data = input_df['WIN_S_Max'].resample('1M', closed='right', label='right').apply(sample_win2)
        big_win_accum = []

        for i in range(1, 13):
            month_i_mean = sample_data[sample_data.index.month == i].mean()
            big_win_accum.append(month_i_mean)

        big_win_accum = pd.DataFrame(big_win_accum)
        big_win_accum.columns = ['累年各月平均强风日数']
        big_win_accum['日期'] = [str(i) + '月' for i in range(1, 13)]
        output_table_10 = big_win_accum[['日期', '累年各月平均强风日数']]
        output_table_10 = output_table_10.round(1).to_dict(orient='records')

        # 分级
        if Part_B_5 <= 3:
            rank_result[4] = 1

        elif Part_B_5 > 3 and Part_B_3 <= 15:
            rank_result[4] = 2

        elif Part_B_5 > 15:
            rank_result[4] = 3

    #############################################
    # 6.年静风日数 <=0.2
    def sample_win3(x):
        x = np.array(x)
        values = np.where(x <= 0.2, 1, 0)
        return np.sum(values)

    tmp = input_df['WIN_S_2mi_Avg']
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_11 = None
        output_table_12 = None
        rank_result[5] = np.nan

    else:
        # 历年结果output
        sample_data = input_df['WIN_S_2mi_Avg'].resample('1A', closed='right', label='right').apply(sample_win3).reset_index()
        sample_data.rename(columns={'index': 'Datetime'}, inplace=True)

        sample_data['日期'] = sample_data['Datetime'].dt.year
        sample_data.columns = ['Datetime', '历年静风日数', '日期']
        Part_B_6 = sample_data['历年静风日数'].mean()
        output_table_11 = sample_data[['日期', '历年静风日数']]
        output_table_11 = output_table_11.round(1).to_dict(orient='records')

        # 累年各月结果output
        sample_data = input_df['WIN_S_2mi_Avg'].resample('1M', closed='right', label='right').apply(sample_win3)
        no_win_accum = []

        for i in range(1, 13):
            month_i_mean = sample_data[sample_data.index.month == i].mean()
            no_win_accum.append(month_i_mean)

        no_win_accum = pd.DataFrame(no_win_accum)
        no_win_accum.columns = ['累年各月平均静风日数']
        no_win_accum['日期'] = [str(i) + '月' for i in range(1, 13)]
        output_table_12 = no_win_accum[['日期', '累年各月平均静风日数']]
        output_table_12 = output_table_12.round(1).to_dict(orient='records')

        # 分级
        if Part_B_6 <= 3:
            rank_result[5] = 1

        elif Part_B_6 > 3 and Part_B_3 <= 15:
            rank_result[5] = 2

        elif Part_B_6 > 15:
            rank_result[5] = 3

    #############################################
    # 7.年沙尘日数 扬沙及以上等级 Part_B_7
    tmp = input_df[['FlSa', 'SaSt']]
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_13 = None
        output_table_14 = None
        rank_result[6] = np.nan

    else:
        # 历年结果output
        array = input_df[['FlSa', 'SaSt']].values
        input_df['dust'] = np.nansum(array, axis=1)
        sample_data = input_df['dust'].resample('1A', closed='right', label='right').sum().reset_index()
        sample_data.rename(columns={'index': 'Datetime'}, inplace=True)

        sample_data['日期'] = sample_data['Datetime'].dt.year
        sample_data.columns = ['Datetime', '历年沙尘日数', '日期']
        Part_B_7 = sample_data['历年沙尘日数'].mean()
        output_table_13 = sample_data[['日期', '历年沙尘日数']]
        output_table_13 = output_table_13.round(1).to_dict(orient='records')

        # 累年各月结果output
        sample_data = input_df['dust'].resample('1M', closed='right', label='right').sum()
        dust_accum = []

        for i in range(1, 13):
            month_i_mean = sample_data[sample_data.index.month == i].mean()
            dust_accum.append(month_i_mean)

        dust_accum = pd.DataFrame(dust_accum)
        dust_accum.columns = ['累年各月平均沙尘日数']
        dust_accum['日期'] = [str(i) + '月' for i in range(1, 13)]
        output_table_14 = dust_accum[['日期', '累年各月平均沙尘日数']]
        output_table_14 = output_table_14.round(1).to_dict(orient='records')

        # 分级
        if Part_B_7 <= 2:
            rank_result[6] = 1

        elif Part_B_7 > 2 and Part_B_3 <= 5:
            rank_result[6] = 2

        elif Part_B_7 > 5:
            rank_result[6] = 3

    #############################################
    # 8.年霾日数
    tmp = input_df['Haze']
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_15 = None
        output_table_16 = None
        rank_result[7] = np.nan

    else:
        # 历年结果output
        sample_data = input_df['Haze'].resample('1A', closed='right', label='right').sum().reset_index()
        sample_data.rename(columns={'index': 'Datetime'}, inplace=True)

        sample_data['日期'] = sample_data['Datetime'].dt.year
        sample_data.columns = ['Datetime', '历年霾日数', '日期']
        Part_B_8 = sample_data['历年霾日数'].mean()
        output_table_15 = sample_data[['日期', '历年霾日数']]
        output_table_15 = output_table_15.round(1).to_dict(orient='records')

        # 累年各月结果output
        sample_data = input_df['Haze'].resample('1M', closed='right', label='right').sum()
        haze_accum = []

        for i in range(1, 13):
            month_i_mean = sample_data[sample_data.index.month == i].mean()
            haze_accum.append(month_i_mean)

        haze_accum = pd.DataFrame(haze_accum)
        haze_accum.columns = ['累年各月平均霾日数']
        haze_accum['日期'] = [str(i) + '月' for i in range(1, 13)]
        output_table_16 = haze_accum[['日期', '累年各月平均霾日数']]
        output_table_16 = output_table_16.round(1).to_dict(orient='records')

        # 分级
        if Part_B_8 <= 3:
            rank_result[7] = 1

        elif Part_B_8 > 3 and Part_B_3 <= 15:
            rank_result[7] = 2

        elif Part_B_8 > 15:
            rank_result[7] = 3

    #############################################
    # 9 年强对流日数 冰雹/雷暴/龙卷/飑线合计
    tmp = input_df[['Hail', 'Thund', 'Tord', 'Squa']]
    rate = (tmp.isnull().sum()) / tmp.shape[0]
    if np.any(rate == 1):
        output_table_17 = None
        output_table_18 = None
        rank_result[8] = np.nan

    else:
        # 历年结果output
        array = input_df[['Hail', 'Thund', 'Tord', 'Squa']].values
        input_df['convection'] = np.nansum(array, axis=1)
        sample_data = input_df['convection'].resample('1A', closed='right', label='right').sum().reset_index()
        sample_data.rename(columns={'index': 'Datetime'}, inplace=True)

        sample_data['日期'] = sample_data['Datetime'].dt.year
        sample_data.columns = ['Datetime', '历年强对流日数', '日期']
        Part_B_9 = sample_data['历年强对流日数'].mean()
        output_table_17 = sample_data[['日期', '历年强对流日数']]
        output_table_17 = output_table_17.round(1).to_dict(orient='records')

        # 累年各月结果output
        sample_data = input_df['convection'].resample('1M', closed='right', label='right').sum()
        convection_accum = []

        for i in range(1, 13):
            month_i_mean = sample_data[sample_data.index.month == i].mean()
            convection_accum.append(month_i_mean)

        convection_accum = pd.DataFrame(convection_accum)
        convection_accum.columns = ['累年各月平均强对流日数']
        convection_accum['日期'] = [str(i) + '月' for i in range(1, 13)]
        output_table_18 = convection_accum[['日期', '累年各月平均强对流日数']]
        output_table_18 = output_table_18.round(1).to_dict(orient='records')

        # 分级
        if Part_B_9 <= 15:
            rank_result[8] = 1

        elif Part_B_9 > 15 and Part_B_3 <= 30:
            rank_result[8] = 2

        elif Part_B_9 > 30:
            rank_result[8] = 3

    #########################################################
    # 合成结果
    if np.all(rank_result == np.nan):
        rank_result_df = None

    else:
        rank_result_df = pd.DataFrame(rank_result, columns=['评价等级'])
        rank_result_df['选取因子'] = ['年高温日数', '年寒冷日数', '年大雨日数', '年无雨日数', '年强风日数', '年静风日数', '年沙尘日数', '年霾日数', '年强对流日数']
        rank_result_df = rank_result_df[['选取因子', '评价等级']]
        rank_result_df['因子数值'] = [Part_B_1, Part_B_2, Part_B_3, Part_B_4, Part_B_5, Part_B_6, Part_B_7, Part_B_8, Part_B_9]
        rank_result_df['单位'] = ['d'] * 9
        rank_result_df = rank_result_df.round(1).to_dict(orient='records')

    # 创建结果字典
    result_dict = edict()

    tables = edict()
    tables['历年高温日数'] = output_table_1
    tables['累年各月平均高温日数'] = output_table_2
    tables['历年寒冷日数'] = output_table_3
    tables['累年各月平均寒冷日数'] = output_table_4
    tables['历年大雨日数'] = output_table_5
    tables['累年各月平均大雨日数'] = output_table_6
    tables['历年无雨日数'] = output_table_7
    tables['累年各月平均无雨日数'] = output_table_8
    tables['历年强风日数'] = output_table_9
    tables['累年各月平均强风日数'] = output_table_10
    tables['历年静风日数'] = output_table_11
    tables['累年各月平均静风日数'] = output_table_12
    tables['历年沙尘日数'] = output_table_13
    tables['累年各月平均沙尘日数'] = output_table_14
    tables['历年霾日数'] = output_table_15
    tables['累年各月平均霾日数'] = output_table_16
    tables['历年强对流日数'] = output_table_17
    tables['累年各月平均强对流日数'] = output_table_18

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
    result = calc_climate_disadvantage_factors(daily_df)