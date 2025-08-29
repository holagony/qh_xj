import os
import glob
import json
import simplejson
import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_processing import hourly_data_processing, wind_direction_to_symbol
from Utils.get_local_data import get_local_data

def calc_airport_wind_ds(df_hourly,numeric_interval):
    '''
    机场参数，统计不同风速区间的风向
    使用小时风速数据
    '''
    hour_df = df_hourly.copy()
    hour_df['WIN_D_Avg_10mi'] = hour_df['WIN_D_Avg_10mi'].astype(str).apply(wind_direction_to_symbol)
    hour_df = hour_df[['WIN_D_Avg_10mi','WIN_S_Avg_10mi']]
    hour_df = hour_df.dropna(how='any')
    
    table = []
    table_index = []
    for interval in numeric_interval:
        if interval[0] == 'null':
            interval[0] = -np.inf
            idx = '0-' + str(interval[1])
            
        elif interval[1] == 'null':
            interval[1] = np.inf
            idx = '>= ' + str(interval[0])
        
        else:
            idx = str(interval[0])+'-'+str(interval[1])
        
        try:
            selected_data = hour_df[(hour_df['WIN_S_Avg_10mi']>interval[0]) & (hour_df['WIN_S_Avg_10mi']<=interval[1])]
            tmp = selected_data.value_counts('WIN_D_Avg_10mi',sort=False)
            table.append(tmp)
            table_index.append(idx)
        
        except Exception as e:
            pass

    table = pd.concat(table,axis=1).T
    table.index = table_index
    table.fillna(0,inplace=True)
    table['总计'] = table.sum(axis=1)
    table.reset_index(inplace=True)
    table.rename(columns={'index':'风速(m/s)'}, inplace=True)
    table = table.round(1)
    
    return table


def calc_airport_wind_loading(df_hourly):
    '''
    机场参数，计算满足最大允许侧风值的侧风数，和相应的风保障率
    使用小时风速数据
    计算不用数据前处理
    '''
    #df_hourly.set_index('Datetime', inplace=True)
    #df_hourly.index = pd.DatetimeIndex(df_hourly.index)
    df_hourly.reset_index(drop=True,inplace=True)
    
    wind_d = list(range(999001,999018))
    df_hourly = df_hourly[~df_hourly.isin(wind_d)]
    df_hourly = df_hourly[['WIN_D_Avg_10mi','WIN_S_Avg_10mi']]
    df_hourly = df_hourly.dropna(how='any')

    def sample(x):
        alpha = x.iloc[0,0]
        selected_data = df_hourly[~(df_hourly['WIN_D_Avg_10mi']-alpha).isin([0,180,360])]
        
        result = []
        for v_c in [5, 6.5, 10]:
            v_theta = np.abs(v_c/np.sin(np.deg2rad(selected_data['WIN_D_Avg_10mi']-alpha)))
            diff = selected_data['WIN_S_Avg_10mi'] - v_theta
            t = len(diff[diff<0])
            phi = round((t/len(diff))*100, 2)
            result.append(t)
            result.append(phi)
        
        result = pd.DataFrame(result)
    
        return result
        
    df = pd.DataFrame(range(1,361),columns=['跑道方向'])
    table = df.groupby('跑道方向').apply(sample).unstack().reset_index()
    table.columns=['跑道方向(度)','侧风数(满足最大允许侧风值5m/s)','风保障率(满足最大允许侧风值5m/s)',
                   '侧风数(满足最大允许侧风值6.5m/s)','风保障率(满足最大允许侧风值6.5m/s)',
                   '侧风数(满足最大允许侧风值10m/s)','风保障率(满足最大允许侧风值10m/s)']

    return table


if __name__ == '__main__':
    hourly_elements = 'WIN_D_Avg_10mi,WIN_S_Avg_10mi'
    sta_ids = '52866'
    years = '2010,2020'
    hour_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,' + hourly_elements).split(',')
    hourly_df = pd.read_csv(cfg.FILES.QH_DATA_HOUR)
    hourly_df = get_local_data(hourly_df, sta_ids, hour_eles, years, 'Hour')
    numeric_interval = [['null',0.5],[0.5,3],[3,5],[5,6.5],[6.5,10],[10,13],[13,17],[17,'null']] 
    table1 = calc_airport_wind_ds(hourly_df,numeric_interval)
    table2 = calc_airport_wind_loading(hourly_df)




