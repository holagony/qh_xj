import simplejson
import itertools
import numpy as np
import pandas as pd
from Utils.data_processing import daily_data_processing
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict


def calc_heat_island_garden_city(df_day, main_st_ids, sub_st_ids):
    '''
    园林城市-城市热岛效应程度(℃)
    城市热岛效应是城市出现市区气温比周围郊区高的现象。
    采用城市市区6-8月日最高气温的平均值和对应时期区域腹地(郊区、农村)日最高气温平均值的差值表示。
    使用日数据 TEM_Max
    '''
    group = df_day.groupby(['Station_Id_C', 'Station_Name'])['TEM_Max']
    group = list(group)

    # 多站数据处理
    stations = []
    for i in range(len(group)):
        station_info = group[i][0]
        data_info = group[i][1]
        stations.append(str(station_info[1]))  # 中文站名

        dates = pd.date_range(start=str(data_info.index.year[0]), end=str(data_info.index.year[-1] + 1), freq='D')[:-1]
        data_info = data_info.reindex(dates, fill_value=np.nan)
        data_info = data_info.interpolate(method='linear')

        if i == 0:
            tem_max_daily = data_info.to_frame()
        else:
            tem_max_daily = pd.concat([tem_max_daily, data_info], axis=1)

    tem_max_daily.columns = stations
    tem_max_daily = tem_max_daily[tem_max_daily.index.month.isin([6, 7, 8])]  # 只保留6/7/8月
    tem_max_yearly = tem_max_daily.resample('1A', closed='right', label='right').mean().round(1)  # 年平均

    # 城市热岛效应程度计算 (排列组合)
    main_st = [df_day[df_day['Station_Id_C'] == main_id]['Station_Name'][0] for main_id in main_st_ids]
    sub_st = [df_day[df_day['Station_Id_C'] == sub_id]['Station_Name'][0] for sub_id in sub_st_ids]
    combine = list(itertools.product(main_st, sub_st))

    result_table = pd.DataFrame(index=tem_max_yearly.index)
    for j in range(len(combine)):
        a = combine[j][0]
        b = combine[j][1]
        result_table[a + '/' + b] = tem_max_yearly[a] - tem_max_yearly[b]

    result_table.index = result_table.index.year
    result_table.loc['平均'] = result_table.mean(axis=0).round(1)

    rate = (result_table.isnull().sum()) / result_table.shape[0]

    if np.all(rate == 1):
        result_table = None
    else:
        result_table.reset_index(inplace=True)
        result_table.rename(columns={'index': '日期'}, inplace=True)
        result_table = result_table.round(1)

    return result_table


if __name__ == '__main__':
    pass
