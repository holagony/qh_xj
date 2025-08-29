import glob
import numpy as np
import pandas as pd
import calendar
from datetime import timedelta
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.get_local_data import get_local_data


def radiation_data_check(df):
    '''
    小时总辐射数据的缺测时间统计和完整率统计，单站
    '''
    df.rename(columns={'V14311': '总辐射辐照度'}, inplace=True)
    dates = df[df.loc[:, '总辐射辐照度'].isna()].index.to_frame().reset_index(drop=True)

    if len(dates) != 0:
        # 缺测时间统计
        deltas = dates.diff()[1:]
        gaps = deltas[deltas > timedelta(hours=1)]
        gaps_idx = gaps.dropna().index

        if len(gaps_idx) == 0:
            start = dates.iloc[0, 0]
            end = dates.iloc[-1, 0]
            num_hours = len(dates)
            time = [start, end, num_hours]
            time = np.array(time).reshape(1, -1)
            time_periods = pd.DataFrame(time, columns=['缺测起始时间', '缺测终止时间', '缺测时间总计'])

        else:
            periods_list = []
            for i in range(0, len(gaps_idx) + 1):

                if i == 0:
                    temp = dates[0:gaps_idx[i]].reset_index(drop=True)

                elif (i > 0) and (i < len(gaps_idx)):
                    temp = dates[gaps_idx[i - 1]:gaps_idx[i]].reset_index(drop=True)

                elif i == len(gaps_idx):
                    temp = dates[gaps_idx[i - 1]:].reset_index(drop=True)

                start = temp.iloc[0, 0]
                end = temp.iloc[-1, 0]
                num_hours = len(temp)
                time = [start, end, num_hours]
                periods_list.append(time)
                time_periods = pd.DataFrame(periods_list, columns=['缺测起始时间', '缺测终止时间', '缺测时间总计'])

        time_periods['缺测起始时间'] = time_periods['缺测起始时间'].dt.strftime('%Y-%m-%d %H:%M:%S')
        time_periods['缺测终止时间'] = time_periods['缺测终止时间'].dt.strftime('%Y-%m-%d %H:%M:%S')

        # 完整率统计
        total_num = df.shape[0]  # 应测数据
        actual_num = df[~df.loc[:, '总辐射辐照度'].isna()].shape[0]  # 实测数据
        leak_num = total_num - actual_num  # 缺测数据
        complete_rate = round((actual_num / total_num) * 100, 1)
        records = pd.DataFrame([total_num, actual_num, leak_num, complete_rate]).T
        records.columns = ['应测数据', '实测数据', '缺测数据', '数据完整率']

    else:
        time_periods = pd.DataFrame()
        records = pd.DataFrame()

    # 保存
    check_result = edict()
    check_result['数据缺测时间检验'] = time_periods.to_dict(orient='records')
    check_result['有效数据完整率'] = records.to_dict(orient='records')

    return check_result


def radiation_partition(df, lon, lat):
    '''
    晴空指数法
    将总辐射数据划分为直接辐射和散射辐射
    '''
    lon = float(lon)
    lat = float(lat)
    
    # 创建EQ时差表
    table = pd.DataFrame()
    table['平年'] = list(range(1, 32)) + [np.nan]
    table['闰年'] = [np.nan] + list(range(1, 32))
    table[1] = [-2, -3, -3, -4, -4, -5, -5, -5, -6, -6, -7, -7, -7, -8, -8, -9, -9, -9, -10, -10, -10, -11, -11, -11, -11, -12, -12, -12, -12, -13, -13, np.nan]
    table[2] = [-13, -13, -13, -13, -14, -14, -14, -14, -14, -14, -14, -14, -14, -14, -14, -14, -14, -14, -14, -14, -14, -14, -14, -14, -14, -13, -13, -13, -13, np.nan, np.nan, np.nan]
    table[3] = [-13, -13, -13, -12, -12, -12, -12, -12, -11, -11, -11, -11, -10, -10, -10, -10, -9, -9, -9, -8, -8, -8, -8, -7, -7, -7, -6, -6, -6, -5, -5, -5]
    table[4] = [-5, -4, -4, -4, -3, -3, -3, -3, -2, -2, -2, -1, -1, -1, -1, -0, -0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, np.nan]
    table[5] = [3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 3, 3, 3, 3, 3, 3, 3, 3]
    table[6] = [3, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 0, 0, -0, -0, -1, -1, -1, -1, -1, -2, -2, -2, -2, -2, -3, -3, -3, -3, np.nan]
    table[7] = [-3, -4, -4, -4, -4, -4, -4, -5, -5, -5, -5, -5, -5, -6, -6, -6, -6, -6, -6, -6, -6, -6, -6, -7, -7, -7, -7, -7, -7, -7, -7, -7]
    table[8] = [-7, -7, -7, -6, -6, -6, -6, -6, -6, -6, -6, -6, -6, -5, -5, -5, -5, -5, -4, -4, -4, -4, -3, -3, -3, -3, -2, -2, -2, -1, -1, -1]
    table[9] = [-1, -0, -0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 8, 8, 8, 9, 9, 10, 10, 10, np.nan]
    table[10] = [10, 10, 11, 11, 11, 12, 12, 12, 13, 13, 13, 13, 14, 14, 14, 14, 15, 15, 15, 15, 15, 15, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16]
    table[11] = [16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 15, 15, 15, 15, 15, 14, 14, 14, 14, 13, 13, 13, 12, 12, 12, 11, 11, np.nan]
    table[12] = [11, 11, 10, 10, 10, 9, 9, 8, 8, 8, 7, 7, 6, 6, 5, 5, 5, 4, 4, 3, 3, 2, 2, 1, 1, 0, -0, -1, -1, -1, -2, -2]

    n = df.index.day_of_year.values  # 积日
    EDNI = 1366.1 * (1 + 0.033 * np.cos(np.radians(360 * n / 365)))
    phi = np.radians(lat)  # 转换为弧度
    delta = np.radians(23.45 * np.sin(np.radians(360 * (284 + n) / 365)))  # 转换为弧度
    c_t = df.index.hour.values
    l_g = lon
    l_c = (l_g - 120) / 15  # 经度修正，单位：小时

    def query_eq(x):
        '''
        EQ表查表确定分钟值，转换为小时
        '''
        if calendar.isleap(x['Year']):
            row = table.loc[table['闰年'] == x['Day'], table.columns == x['Mon']]

        else:
            row = table.loc[table['平年'] == x['Day'], table.columns == x['Mon']]

        return row.values[0][0] / 60

    e_q = df.apply(query_eq, axis=1).values
    t_t = c_t + l_c + e_q
    omega = np.radians((t_t - 12) * 15)  # 时角，转换为弧度
    EHI = EDNI * (np.cos(phi) * np.cos(delta) * np.cos(omega) + np.sin(phi) * np.sin(delta))
    EHI = np.maximum(EHI, 0)  # 确保EHI不为负值（夜间或太阳在地平线以下时）

    # 将EHI转换为与总辐射相同的单位 (MJ/m²)
    # EHI原单位为W/m²，转换为MJ/m²: W/m² * 3600 / 1e6 = MJ/m²
    EHI_MJ = EHI * 3600 / 1e6

    # 晴空系数计算，确保单位一致 (都是MJ/m²)
    # 使用更小的最小值避免除零，同时不影响正常计算
    kt = df.iloc[:, -1] / np.maximum(EHI_MJ, 1e-6)  # 避免除以0或极小值
    kt = np.abs(kt)
    kt = np.minimum(kt, 1.0)  # 晴空系数不应超过1.0

    def calc_f_kt(x):
        if pd.isna(x) or x < 0:
            return np.nan
        elif 0 <= x < 0.35:
            return 1.0 - 0.249 * x
        elif 0.35 <= x <= 0.75:
            return 1.557 - 1.84 * x
        elif x > 0.75:
            return 0.177
        else:
            return np.nan

    f_kt = kt.apply(calc_f_kt)  # 散射辐射比例
    
    # 只在有效太阳辐射时间计算分离
    # 降低阈值：0.001 MJ/m² (约1 W/m²)，确保更多有效数据点
    # valid_mask = (EHI_MJ > 0.001) & (~pd.isna(f_kt)) & (df.iloc[:, -1] > 0)
    
    # df['散射辐射'] = np.where(valid_mask, 
    #                         (df.iloc[:, -1] * f_kt).round(4), 
    #                         0)
    # df['直接辐射'] = np.where(valid_mask,
    #                         (df['总辐射'] - df['散射辐射']).round(4),
    #                         0)
    df['散射辐射'] = (df.iloc[:, -1] * f_kt).round(1)
    df['直接辐射'] = (df['总辐射'] - df['散射辐射']).round(1)

    return df


def radiation_data_stats(df, flag=None):
    '''
    辐射统计，单站
    逐月变化 sun/mean
    累年各小时变化 sum/mean
    '''
    stats_result = edict()

    # 提取数据信息
    exposure = df[df.filter(like='辐射').columns]  # MJ.m-2

    # 历年
    sum_yearly = exposure.resample('1A').sum().round(1)
    sum_yearly.insert(loc=0, column='时间', value=sum_yearly.index.strftime('%Y'))
    sum_yearly.reset_index(drop=True, inplace=True)
    stats_result['年变化'] = sum_yearly.to_dict(orient='records')

    # 历月
    exposure_sum = exposure.resample('1M').sum().round(1)  # 月累积
    exposure_sum.insert(loc=0, column='时间', value=exposure_sum.index.strftime('%Y-%m'))
    exposure_sum.reset_index(drop=True, inplace=True)
    stats_result['月变化'] = exposure_sum.to_dict(orient='records')

    # 累年各月
    num_year = len(exposure.index.year.unique())
    exposure_monthly = []
    for i in range(1, 13):
        # 计算多年来各月的平均总辐射量
        monthly_sums = exposure[exposure.index.month == i].sum()
        tmp = (monthly_sums/num_year).round(1)  # 各月总量的多年平均
        exposure_monthly.append(tmp)

    exposure_monthly = pd.DataFrame(exposure_monthly)
    exposure_monthly.insert(loc=0, column='时间', value=[str(i+1) + '月' for i in exposure_monthly.index])
    exposure_monthly.reset_index(drop=True, inplace=True)
    stats_result['累年各月变化'] = exposure_monthly.to_dict(orient='records')

    if flag == 'radi':
        # 日变化
        exposure_hourly_mean = []
        for i in range(0, 24):
            exposure_i_mean = exposure[exposure.index.hour == i].sum()
            exposure_i_mean = (exposure_i_mean/num_year).round(1)
            exposure_hourly_mean.append(exposure_i_mean)

        exposure_hourly_mean = pd.DataFrame(exposure_hourly_mean)
        exposure_hourly_mean.insert(loc=0, column='时间', value=[str(i) + '时' for i in exposure_hourly_mean.index])
        exposure_hourly_mean.reset_index(drop=True, inplace=True)
        stats_result['累年日变化'] = exposure_hourly_mean.to_dict(orient='records')

    return stats_result


def radiation_stats(daily_df, radi_df, sta_ids, param_a, param_b, divide_flag):
    '''
    辐射数据统计全流程
    stations 站号(可多个)，'52866,56029,52863,52754,52818,52874,56043,52713,56065'
    years 年份，str '2000,2020'
    '''
    # 数据检验
    # start_year = int(years.split(',')[0])
    # end_year = int(years.split(',')[1])
    # dates = pd.date_range(start=str(start_year), end=str(end_year + 1), freq='H')[:-1]
    # df_sta = df_sta.reindex(dates, fill_value=np.nan)
    # check_result = radiation_data_check(df_sta)
    # result_dict['检验结果'] = check_result

    result_dict = edict()
    daily_df = daily_df[~daily_df.index.duplicated()]  # 数据去除重复
    daily_df['总辐射'] = param_a*daily_df['SSH'] + param_b # 单位：辐照量 MJ/m
    # daily_df.dropna(inplace=True)

    if divide_flag == 1:
        lon = daily_df['Lon'][0]
        lat = daily_df['Lat'][0]
        daily_df = radiation_partition(daily_df, lon, lat)

    sta_result = radiation_data_stats(daily_df)
    result_dict['日照时换算结果'] = sta_result

    # 辐射站
    if radi_df is not None:
        # radi_df转化为辐照量
        # x W/m^2--> x*3600/100000 MJ/m
        radi_df_cp = radi_df.copy()
        radi_df_cp['总辐射'] = radi_df_cp['总辐射'] * 3600 / 1e6
        # radi_df.dropna(inplace=True)

        if divide_flag == 1:
            lon = radi_df_cp['Lon'][0]
            lat = radi_df_cp['Lat'][0]
            radi_df_cp = radiation_partition(radi_df_cp, lon, lat)

        radi_result = radiation_data_stats(radi_df_cp, flag='radi')
        result_dict['辐射站监测结果'] = radi_result

    return result_dict


if __name__ == '__main__':

    def radi_data_processing(df):
        '''
        辐射数据处理
        '''
        if 'Unnamed: 0' in df.columns:
            df.drop(['Unnamed: 0'], axis=1, inplace=True)

        # df['Datetime'] = pd.to_datetime(df['year'] + '-' + df['month'] + '-' + df['day'] + '-' + df['hour'], format='%Y-%m-%d-%H')
        try:
            df['Datetime'] = pd.to_datetime(df['Datetime'])
            df.set_index('Datetime', inplace=True)
        except:
            pass

        df['Station_Id_C'] = df['Station_Id_C'].astype(str)
        df['Year'] = df['Year'].map(int)
        df['Mon'] = df['Mon'].map(int)
        df['Day'] = df['Day'].map(int)
        df['Hour'] = df['Hour'].map(int)
        df['V14311'] = df['V14311'].apply(lambda x: np.nan if x > 999 else x)
        df.rename(columns={'V14311': '总辐射'}, inplace=True)

        return df

    sta_ids = '52866'
    years = '2016,2020'
    param_a = 1.525
    param_b = 10.526
    divide_flag = 1
    daily_elements = 'SSH'
    hourly_elements = 'V14311'
    day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements).split(',')
    daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')
    
    radi_df = pd.read_csv(cfg.FILES.QH_DATA_RADI)
    radi_df = radi_data_processing(radi_df)
    radi_df = radi_df[radi_df['Station_Id_C']==sta_ids]
    sp_years = years.split(',')
    radi_df = radi_df[(radi_df.index.year >= int(sp_years[0])) & (radi_df.index.year <= int(sp_years[1]))]
    result = radiation_stats(daily_df, radi_df, sta_ids, param_a, param_b, divide_flag)
