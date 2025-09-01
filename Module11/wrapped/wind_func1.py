import os
import numpy as np
import pandas as pd
from datetime import timedelta
from Module11.wrapped.wind_dataloader import get_data_postgresql, wind_tower_processing
from Utils.ordered_easydict import OrderedEasyDict as edict

def data_missing_time_stats(df, time_range):
    '''
    测风塔数据缺失时间段统计，
    使用小时df，只能有1列，代表一个要素/高度
    '''
    times = time_range.split(',')
    start_date = times[0] + '000000'
    end_date = times[1] + '235959'
    date_time = pd.date_range(start=start_date, end=end_date, freq='H')
    df = df.reindex(date_time, fill_value=np.nan)
    dates = df[df.iloc[:, 0].isna()].index.to_frame().reset_index(drop=True)

    if len(dates) != 0:
        deltas = dates.diff()[1:]
        gaps = deltas[deltas > timedelta(hours=1)]
        gaps_idx = gaps.dropna().index

        if len(gaps_idx) == 0:
            start = dates.iloc[0, 0]
            end = dates.iloc[-1, 0]
            num_hours = len(dates)
            time = [start, end, num_hours]
            time = np.array(time).reshape(1, -1)
            time_periods = pd.DataFrame(time, columns=['缺测起始时间', '缺测终止时间', '缺测时间总计(小时)'])
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
                time_periods = pd.DataFrame(periods_list, columns=['缺测起始时间', '缺测终止时间', '缺测时间总计(小时)'])

        time_periods['缺测起始时间'] = time_periods['缺测起始时间'].dt.strftime('%Y-%m-%d %H:%M:%S')
        time_periods['缺测终止时间'] = time_periods['缺测终止时间'].dt.strftime('%Y-%m-%d %H:%M:%S')
    else:
        time_periods = pd.DataFrame()

    return time_periods


def wind_stats1(data_dict, time_range):
    '''
    对每个站各高度的风速/风向统计缺失时间段
    对每个站各个气象要素统计缺失时间段
    如果有，输出相应的时间段表格；如果没有，输出提示字符串
    '''
    ele_ch = dict()
    ele_ch['ws_10'] = '风速'
    ele_ch['wd_10'] = '风向'
    ele_ch['ws_max'] = '最大风速'
    ele_ch['ws_max_inst'] = '极大风速'

    check_result = edict()
    for sta, sub_dict in data_dict.items():
        check_result[sta] = edict()
        
        for ele, df in sub_dict.items():
            ch = ele_ch[ele]
            check_result[sta][ch] = edict()
            cols = df.columns

            for col in cols:
                data = df[col].to_frame()
                name = col.split('_')[0] + '观测高度'
                time_periods = data_missing_time_stats(data, time_range)
                check_result[sta][ch][name] = time_periods.round(2).to_dict(orient='records')

    return check_result


if __name__ == '__main__':
    df = get_data_postgresql(sta_id='XJ_dabancheng', time_range='20220701,20230731')
    after_process = wind_tower_processing(df)
    check_result1 = wind_stats1(after_process, time_range='20220701,20230731')
