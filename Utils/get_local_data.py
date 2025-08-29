import pandas as pd
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_processing import hourly_data_processing, daily_data_processing, monthly_data_processing, yearly_data_processing


def get_local_data(df_in, sta_ids, eles, years, freq):
    '''
    读取本地站点数据+数据处理
    df_in 年/月/日/小时df
    sta_ids 站号列表
    '''
    selected_years = years
    years = years.split(',')
    sta_list = [int(ids) for ids in sta_ids.split(',')]
    df_in = df_in.loc[df_in['Station_Id_C'].isin(sta_list), eles]
    df_in['Datetime'] = pd.to_datetime(df_in['Datetime'])
    df_in.set_index('Datetime', inplace=True)
    df_in = df_in[(df_in.index.year >= int(years[0])) & (df_in.index.year <= int(years[1]))]

    if freq == 'Year':
        df_out = yearly_data_processing(df_in, selected_years)
    elif freq == 'Month':
        df_out = monthly_data_processing(df_in, selected_years)
    elif freq == 'Day':
        df_out = daily_data_processing(df_in, selected_years)
    elif freq == 'Hour':
        df_out = hourly_data_processing(df_in, selected_years)
        if 'RHU' in df_out.columns:
            df_out['RHU'] = df_out['RHU'] / 100

    return df_out