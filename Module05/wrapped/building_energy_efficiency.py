import simplejson
import calendar
import datetime
import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_processing import daily_data_processing


def daynum_to_date(daynum, year=2022):
    '''
    天数转换为[月-日]的形式，默认选择365天为一年
    '''
    month = 1
    day = daynum

    while month < 13:
        month_days = calendar.monthrange(year, month)[1]
        if day <= month_days:
            return datetime.date(year, month, day).strftime('%m-%d')

        day -= month_days
        month += 1


def calc_building_energy_efficiency(df_daily):
    '''
    建筑节能参数计算
    '''
    num_years = len(df_daily.index.year.unique())
    dates = pd.date_range(start=str(df_daily.index.year[0]), end=str(df_daily.index.year[-1] + 1), freq='D')[:-1]
    df_daily = df_daily.reindex(dates, fill_value=np.nan)
    df_daily = df_daily[['Station_Id_C', 'Year', 'Mon', 'Day', 'TEM_Avg']]
    df_daily.loc[:, 'TEM_Avg'] = df_daily.loc[:, 'TEM_Avg'].interpolate(method='linear', axis=0)  # 缺失值插值填充
    df_daily.loc[:, 'TEM_Avg'] = df_daily.loc[:, 'TEM_Avg'].fillna(method='bfill')  # 填充后一条数据的值，但是后一条也不一定有值

    ######################################################
    # 1.采暖度日数 HDD18
    sample_data = df_daily['TEM_Avg']
    sample_data = sample_data[~((sample_data.index.month == 2) & (sample_data.index.day == 29))]  # 去掉2.29号
    data = sample_data.values.reshape(num_years, -1)

    t_hdd = np.where(18 - data > 0, 1, 0)  # (21,365)
    HDD18 = np.mean(np.sum(t_hdd, axis=1))

    # 历年结果表
    sample_data = sample_data.to_frame()
    sample_data['hdd'] = t_hdd.reshape(-1, 1)

    hdd_year = sample_data['hdd'].resample('1A', closed='right', label='right').sum().reset_index()
    hdd_year['date'] = hdd_year['index'].dt.year
    hdd_year.columns = ['index', '历年采暖日数', 'date']
    output_table_1 = hdd_year[['date', '历年采暖日数']]

    # 累年各月结果表
    hdd_month = sample_data['hdd'].resample('1M', closed='right', label='right').sum()
    hdd_accum = []

    for i in range(1, 13):
        month_i_mean = hdd_month[hdd_month.index.month == i].mean()
        hdd_accum.append(month_i_mean)

    hdd_accum = pd.DataFrame(hdd_accum)
    hdd_accum.columns = ['累年各月平均采暖日数']
    hdd_accum['date'] = [str(i) + '月' for i in range(1, 13)]
    output_table_2 = hdd_accum[['date', '累年各月平均采暖日数']]

    ######################################################
    # 2.空调度日数 CDD26
    sample_data = df_daily['TEM_Avg']
    sample_data = sample_data[~((sample_data.index.month == 2) & (sample_data.index.day == 29))]  # 去掉2.29号
    data = sample_data.values.reshape(num_years, -1)

    t_cdd = np.where(data - 26 > 0, 1, 0)
    CDD26 = np.mean(np.sum(t_cdd, axis=1))

    # 历年结果表
    sample_data = sample_data.to_frame()
    sample_data['cdd'] = t_cdd.reshape(-1, 1)

    cdd_year = sample_data['cdd'].resample('1A', closed='right', label='right').sum().reset_index()
    cdd_year['date'] = cdd_year['index'].dt.year
    cdd_year.columns = ['index', '历年空调日数', 'date']
    output_table_3 = cdd_year[['date', '历年空调日数']]

    # 累年各月结果表
    cdd_month = sample_data['cdd'].resample('1M', closed='right', label='right').sum()
    cdd_accum = []

    for i in range(1, 13):
        month_i_mean = cdd_month[cdd_month.index.month == i].mean()
        cdd_accum.append(month_i_mean)

    cdd_accum = pd.DataFrame(cdd_accum)
    cdd_accum.columns = ['累年各月平均空调日数']
    cdd_accum['date'] = [str(i) + '月' for i in range(1, 13)]
    output_table_4 = cdd_accum[['date', '累年各月平均空调日数']]

    ######################################################
    # 3.采暖期 所使用的日资料，每年都按365天计算
    sample_data = df_daily['TEM_Avg']
    sample_data = sample_data[~((sample_data.index.month == 2) & (sample_data.index.day == 29))]  # 去掉2.29号
    assert len(sample_data) % 365 == 0, '数据长度不对，不能整除'

    data = sample_data.values.reshape(num_years, -1)
    t_dny = np.mean(data, axis=0)
    t_dny = pd.DataFrame(t_dny, index=range(1, 366), columns=['tem'])
    t_dny = pd.concat([t_dny, t_dny[:4]])  # 把前4天的数据拼到末尾，用于计算滑动平均
    t_dny = t_dny.rolling(5).mean().dropna()
    t_dny.index = range(1, 366)
    t_dny_re = pd.concat([t_dny[182:], t_dny[0:182]]).reset_index()

    N_hps_idx = t_dny_re[t_dny_re['tem'] <= 5].index[0]
    N_hps = t_dny_re.iloc[N_hps_idx, 0]

    N_hpe_idx = t_dny_re[t_dny_re['tem'] <= 5].index[-1] + 4
    N_hpe = t_dny_re.iloc[N_hpe_idx, 0]

    if (N_hps >= 183 and N_hps <= 365) and (N_hpe >= 1 and N_hpe < 183):
        Z = 365 - N_hps + N_hpe + 1

    elif (N_hps >= 1 and N_hpe > N_hps and N_hpe < 183) or (N_hps >= 138 and N_hpe > N_hps and N_hpe <= 365):
        Z = N_hpe - N_hps + 1

    Z_start = daynum_to_date(N_hps)
    Z_end = daynum_to_date(N_hpe)

    ######################################################
    # 4.采暖期室外平均温度
    sample_data = df_daily['TEM_Avg']
    sample_data = sample_data[~((sample_data.index.month == 2) & (sample_data.index.day == 29))]  # 去掉2.29号
    data = sample_data.values.reshape(num_years, -1).T  # n列，每一列为一年的日平均气温

    data = pd.DataFrame(data)
    data = pd.concat([data, data.iloc[0:4, :]], axis=0)  # 把前4天的数据拼到末尾，用于计算滑动平均
    data_moving_avg = data.rolling(5, axis=0).mean().dropna()
    data_moving_avg.index = range(1, 366)
    data_moving_avg_re = pd.concat([data_moving_avg[182:], data_moving_avg[0:182]]).reset_index()

    tmp_lst = []
    for i in range(num_years):
        start = data_moving_avg_re[data_moving_avg_re.loc[:, i] <= 5].index[0]
        end = data_moving_avg_re[data_moving_avg_re.loc[:, i] <= 5].index[-1]

        if end <= 360:
            end += 4

        N_hps = data_moving_avg_re.iloc[start, 0]
        N_hpe = data_moving_avg_re.iloc[end, 0]

        if (N_hps >= 183 and N_hps <= 365) and (N_hpe >= 1 and N_hpe < 183):
            Z = 365 - N_hps + N_hpe + 1

        elif (N_hps >= 1 and N_hpe > N_hps and N_hpe < 183) or (N_hps >= 138 and N_hpe > N_hps and N_hpe <= 365):
            Z = N_hpe - N_hps + 1

        seq = data_moving_avg_re.loc[start:end, i]
        t_hp = seq.sum() / Z
        tmp_lst.append(t_hp)

    result = np.sum(np.array(tmp_lst))

    ######################################################
    # 合并结果
    result_dict = edict()
    result_dict.HDD18 = round(float(HDD18), 1)
    result_dict.CDD26 = round(float(CDD26), 1)
    result_dict.Z = int(Z)
    result_dict.Z_start = Z_start
    result_dict.Z_end = Z_end
    result_dict.mean_tem = round(float(result), 1)
    result_dict.table1 = output_table_1.round(1).to_dict(orient='records')
    result_dict.table2 = output_table_2.round(1).to_dict(orient='records')
    result_dict.table3 = output_table_3.round(1).to_dict(orient='records')
    result_dict.table4 = output_table_4.round(1).to_dict(orient='records')
    result_dict.note = ['HDD18-采暖度日数', 'CDD26-空调度日数', 'Z-采暖期天数', 'Z_start-采暖期开始日期', 'Z_end-采暖期结束日期', 'mean_tem-采暖期室外平均温度', 'table1-历年采暖日数表', 'table2-累年各月平均采暖日数表', 'table3-历年空调日数表', 'table4-累年各月平均空调日数表']

    return result_dict


if __name__ == '__main__':
    df_day = pd.read_csv(r'D:\Project\3_项目\2_气候评估和气候可行性论证\qhkxxlz\Files\old_data\Module05_data\day.csv')
    df_day = daily_data_processing(df_day)
    # daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    # post_daily_df = daily_data_processing(daily_df)
    # post_daily_df = post_daily_df[post_daily_df['Station_Id_C']=='52853']
    # post_daily_df = post_daily_df[post_daily_df.index.year>=1994]
    # df_day = post_daily_df[post_daily_df.index.year<=2023]
    # # df_day['RHU_Avg'] = df_day['RHU_Avg'] / 100
    # df_day.dropna(inplace=True)
    result = calc_building_energy_efficiency(df_day)
