import os
import itertools
import numpy as np
import pandas as pd
from Module11.wrapped.wind_dataloader import get_data_postgresql, wind_tower_processing
from Utils.ordered_easydict import OrderedEasyDict as edict

def ws_trend_test(ws_df, h):
    '''
    针对单个高度的，风速变化趋势检测，如果大于6m/s，判断为异常
    输出1，表示风速异常样本
    '''
    ws_df['趋势突变_flag'] = np.nan
    col_name = str(h) + 'm_hour_ws'
    rolling_list = list(ws_df[col_name].rolling(3, min_periods=1))

    for section in rolling_list[2:]:
        if np.abs(section[1] - section[0]) >= 6 and np.abs(section[1] - section[2]) >= 6:
            ws_df.loc[section.index[1], '趋势突变_flag'] = 1

    ws_df['趋势突变_flag'].fillna(0, inplace=True)

    return ws_df


def ws_difference_test(h_combine, temp_dict):
    '''
    不同高度层的风速差值检测
    如果差值大于阈值(异常)，对应上下两层风速的输出flag都为1
    和consider_diff参数相关

    目前已设定的组合：
    高度100m/70m 风速0-3之间合理
    高度100m/50m 风速0-5之间合理
    高度100m/30m 风速0-7之间合理
    高度50m/30m 风速0-2之间合理
    高度50m/10m 风速0-4之间合理
    高度70m/50m 风速0-2之间合理
    高度70m/30m 风速0-4之间合理
    高度70m/10m 风速0-6之间合理
    高度30m/10m 风速0-2之间合理
    
    h_combine: 该测风塔实际高度的排列组合结果列表
    temp_dict: 前面统计好的每层风速的dict
    '''
    ws_diff_info = {'100m/70m': 3, '100m/50m': 5, '100m/30m': 7, '70m/50m': 2, '70m/30m': 4, '70m/10m': 6, '50m/30m': 2, '50m/10m': 4, '30m/10m': 2}

    for combine in h_combine:
        h0 = combine[0]
        h1 = combine[1]

        if int(h0) > int(h1):
            name = h0 + 'm/' + h1 + 'm'
        else:
            name = h1 + 'm/' + h0 + 'm'

        if name in ws_diff_info.keys():
            threshold_value = ws_diff_info[name]
            hh = name.split('/')
            hh0 = hh[0][:-1]  # hh0>hh1
            hh1 = hh[1][:-1]

            df_h0 = temp_dict[hh0]
            df_h1 = temp_dict[hh1]
            wind_A = df_h0[hh0 + 'm_hour_ws'].values  # hh0高度对应的风速
            wind_B = df_h1[hh1 + 'm_hour_ws'].values

            diff = wind_A - wind_B
            diff_flag = np.where((diff < threshold_value) & (diff > 0) | (np.isnan(diff)), 0, 1)  # 计算判断flag值，diff是nan的时候，赋值0

            df_h0[name + '_flag'] = diff_flag
            df_h1[name + '_flag'] = diff_flag

            temp_dict[hh0] = df_h0
            temp_dict[hh1] = df_h1

    return temp_dict


def wd_difference_test(h_combine, temp_dict):
    '''
    不同高度层的风向差值检测
    如果差值大于阈值(异常)，对应上下两层风速的输出flag都为1
    和consider_diff参数相关
    
    目前已设定的组合：
    高度50m/30m 风速0-22.5度之间合理
    
    h_combine: 该测风塔实际高度的排列组合结果列表
    temp_dict: 前面统计好的每层风速的dict
    '''
    wd_diff_info = {'50m/30m': 22.5}

    for combine in h_combine:
        h0 = combine[0]
        h1 = combine[1]

        if int(h0) > int(h1):
            name = h0 + 'm/' + h1 + 'm'
        else:
            name = h1 + 'm/' + h0 + 'm'

        if name in wd_diff_info.keys():
            threshold_value = wd_diff_info[name]
            hh = name.split('/')
            hh0 = hh[0][:-1]  # hh0>hh1
            hh1 = hh[1][:-1]

            df_h0 = temp_dict[hh0]
            df_h1 = temp_dict[hh1]
            wind_A = df_h0[hh0 + 'm_hour_wd'].values  # hh0高度对应的风向
            wind_B = df_h1[hh1 + 'm_hour_wd'].values

            diff = np.abs(wind_A - wind_B)
            diff_flag = np.where((diff < threshold_value) | (np.isnan(diff)), 0, 1)  # 计算判断flag值，diff是nan的时候，赋值0

            df_h0[name + '_flag'] = diff_flag
            df_h1[name + '_flag'] = diff_flag

            temp_dict[hh0] = df_h0
            temp_dict[hh1] = df_h1

    return temp_dict


def wind_stats2(data_dict, time_range, consider_diff):
    '''
    测风塔数据(风速和风向)的完整率统计，默认不统计unknow层的风速(不管有没有)
    data_dict: 对应处理过后的测风塔数据
    heights: 对应传入的高度列表 ['unknown1', '10m', '30m', '60m', 'unknown2']
    consider_diff: 考虑是否统计不同高度层数据的差值，用来计算数据异常率，默认为0不考虑差值
    '''
    # 高度提取
    # heights = list(filter(lambda x: x[:-1] != 'unknown', heights))
    # heights = [h[:-1] for h in heights]
    # h_combine = list(itertools.combinations(heights, 2))  # 不同高度两两组合，用于计算不同层风速差值
    
    # 时间处理
    times = time_range.split(',')
    start_date = times[0] + '000000'
    end_date = times[1] + '235959'
    date_time = pd.date_range(start=start_date, end=end_date, freq='H')
    
    # 循环计算
    check_result = edict()
    for sta, sub_dict in data_dict.items():
        check_result[sta] = edict()
        
        for ele, df in sub_dict.items():
            df = df.reindex(date_time, fill_value=np.nan)
            heights = [col.split('_')[0][:-1] for col in df.columns]
            h_combine = list(itertools.combinations(heights, 2))  # 不同高度两两组合，用于计算不同层风速差值
        
            if ele == 'ws_10':
                temp_dict = {}  # 存放不同高度统计表的dict

                for h in heights:
                    col_name = h + 'm_hour_ws'
                    ws = df[col_name].to_frame()

                    # 添加应有、缺测、无效样本flag
                    ws['应有样本'] = 1  # 恒定都是1
                    ws['实有样本'] = ws.apply(lambda x: 0 if np.isnan(x[col_name]) else 1, axis=1)  # 0表示这个样本没有
                    ws['缺测样本'] = ws.apply(lambda x: 1 if np.isnan(x[col_name]) else 0, axis=1)  # 1表示缺测样本
                    ws['无效范围_flag'] = ws.apply(lambda x: 1 if (x[col_name] < 0) or (x[col_name] >= 40) and (x['缺测样本flag'] == 0) else 0, axis=1)  # 1表示范围无效样本

                    # 添加趋势突变flag
                    ws = ws_trend_test(ws, h)

                    # 添加到临时的dict
                    temp_dict[h] = ws

                # 添加不同高度层异常差值flag，temp_dict更新
                temp_dict = ws_difference_test(h_combine, temp_dict)

                # 计算有效率
                ws_dict = edict()

                for key, temp_df in temp_dict.items():
                    if consider_diff == 0:
                        temp_df['异常样本'] = temp_df[['无效范围_flag', '趋势突变_flag']].max(axis=1)
                    else:
                        temp_df['异常样本'] = temp_df[temp_df.filter(like='_flag').columns].max(axis=1)

                    stats_s = temp_df.resample('1M', closed='right', label='right')[['应有样本', '实有样本', '缺测样本', '异常样本']].sum()
                    stats_s.columns = ['应有样本数', '实有样本数', '缺测样本数', '异常样本数']
                    stats_s['样本缺测率'] = ((stats_s['缺测样本数'] / stats_s['应有样本数']) * 100).round(2)
                    stats_s['样本异常率'] = ((stats_s['异常样本数'] / stats_s['应有样本数']) * 100).round(2)
                    stats_s['有效完整率'] = 100 - stats_s['样本缺测率'] - stats_s['样本异常率']
                    stats_s = stats_s[['应有样本数', '实有样本数', '缺测样本数', '异常样本数', '有效完整率', '样本缺测率', '样本异常率']]
                    stats_s.columns = ['应有样本数', '实有样本数', '缺测样本数', '异常样本数', '有效完整率%', '样本缺测率%', '样本异常率%']
                    stats_s.insert(loc=0, column='时间', value=stats_s.index.strftime('%Y-%m'))
                    stats_s.reset_index(drop=True, inplace=True)
                    ws_dict[key + 'm' + '观测高度'] = stats_s.to_dict(orient='records')

                # 保存
                check_result[sta]['风速'] = ws_dict

            elif ele == 'wd_10':
                temp_dict = {}  # 存放不同高度统计表的dict

                for h in heights:
                    col_name = h + 'm_hour_wd'
                    wd = df[col_name].to_frame()

                    # 添加应有、缺测、无效样本flag
                    wd['应有样本'] = 1  # 恒定都是1
                    wd['实有样本'] = wd.apply(lambda x: 0 if np.isnan(x[col_name]) else 1, axis=1)  # 0表示这个样本没有
                    wd['缺测样本'] = wd.apply(lambda x: 1 if np.isnan(x[col_name]) else 0, axis=1)  # 1表示缺测样本
                    wd['无效范围_flag'] = wd.apply(lambda x: 1 if (x[col_name] < 0) or (x[col_name] >= 360) and (x[col_name] != np.nan) else 0, axis=1)  # 1表示范围无效样本

                    # 添加到临时的dict
                    temp_dict[h] = wd

                # 添加不同高度层异常差值flag，temp_dict更新
                temp_dict = wd_difference_test(h_combine, temp_dict)

                # 计算有效率
                wd_dict = edict()
                for key, temp_df in temp_dict.items():
                    if consider_diff == 0:
                        temp_df['异常样本'] = temp_df[['无效范围_flag']].max(axis=1)
                    else:
                        temp_df['异常样本'] = temp_df[temp_df.filter(like='_flag').columns].max(axis=1)

                    stats_d = temp_df.resample('1M', closed='right', label='right')[['应有样本', '实有样本', '缺测样本', '异常样本']].sum()
                    stats_d.columns = ['应有样本数', '实有样本数', '缺测样本数', '异常样本数']
                    stats_d['样本缺测率'] = ((stats_d['缺测样本数'] / stats_d['应有样本数']) * 100).round(2)
                    stats_d['样本异常率'] = ((stats_d['异常样本数'] / stats_d['应有样本数']) * 100).round(2)
                    stats_d['有效完整率'] = 100 - stats_d['样本缺测率'] - stats_d['样本异常率']
                    stats_d = stats_d[['应有样本数', '实有样本数', '缺测样本数', '异常样本数', '有效完整率', '样本缺测率', '样本异常率']]
                    stats_d.columns = ['应有样本数', '实有样本数', '缺测样本数', '异常样本数', '有效完整率%', '样本缺测率%', '样本异常率%']
                    stats_d.insert(loc=0, column='时间', value=stats_d.index.strftime('%Y-%m'))
                    stats_d.reset_index(drop=True, inplace=True)
                    wd_dict[key + 'm' + '观测高度'] = stats_d.to_dict(orient='records')

                # 保存
                check_result[sta]['风向'] = wd_dict

    return check_result


if __name__ == '__main__':
    df = get_data_postgresql(sta_id='QH001', time_range='20230801,20240630')
    after_process = wind_tower_processing(df)
    check_result2 = wind_stats2(after_process, time_range='20220801,20240630', consider_diff=0)
