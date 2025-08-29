import json
import simplejson
import itertools
import numpy as np
import pandas as pd
from Utils.data_processing import daily_data_processing
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.name_utils import equalsIgnoreCase


def get_heat_island_levels(df):
    '''
    热岛强度等级判断
    '''
    bins = [-np.inf, 0.5, 1.5, 2.5, 3.5, np.inf]
    labels = ['无', '弱', '中等', '强', '极强']

    for i in range(len(df.columns)):
        level = pd.cut(df.iloc[:, i], bins=bins, labels=labels)

        if i == 0:
            df_levels = level
        else:
            df_levels = pd.concat([df_levels, level], axis=1)

    return df_levels


def calc_heat_island(df_day, main_st_ids, sub_st_ids, time_resolution, data_types):
    '''
    计算热岛强度 使用日数据
    时间分辨率time_resolution: 'year', 'season', 'month', 'day'
    要素类型data_types: 'Avg', 'Max', 'Min'
    对应要素: TEM_Avg, TEM_Max, TEM_Min
    '''
    main_st = [df_day[df_day['Station_Id_C'] == main_id]['Station_Name'][0] for main_id in main_st_ids]
    sub_st = [df_day[df_day['Station_Id_C'] == sub_id]['Station_Name'][0] for sub_id in sub_st_ids]
    combine = list(itertools.product(main_st, sub_st))  # 主副站排列组合

    elements = ['TEM_' + type_ for type_ in data_types]
    all_result = edict()  # 先创建保存结果的字典
    all_result.Avg = edict()
    all_result.Max = edict()
    all_result.Min = edict()
    all_result.Avg.year = edict()
    all_result.Avg.season = edict()
    all_result.Avg.month = edict()
    all_result.Avg.day = edict()
    all_result.Max.year = edict()
    all_result.Max.season = edict()
    all_result.Max.month = edict()
    all_result.Max.day = edict()
    all_result.Min.year = edict()
    all_result.Min.season = edict()
    all_result.Min.month = edict()
    all_result.Min.day = edict()

    for i in range(len(elements)):
        group = df_day.groupby(['Station_Id_C', 'Station_Name'])[elements[i]]
        group = list(group)

        # 多站数据处理
        stations = []
        for j in range(len(group)):
            station_info = group[j][0]
            data_info = group[j][1]
            stations.append(str(station_info[1]))  # 中文站名
            dates = pd.date_range(start=str(data_info.index.year[0]), end=str(data_info.index.year[-1] + 1), freq='D')[:-1]
            data_info = data_info.reindex(dates, fill_value=np.nan)
            data_info = data_info.interpolate(method='linear')

            if j == 0:
                all_data = data_info.to_frame()
            else:
                all_data = pd.concat([all_data, data_info], axis=1)

        all_data.columns = stations  # 处理后的多站数据的最终形式 (单一的平均/最大/最小气温要素)
        all_data['城市站均值'] = all_data[main_st].mean(axis=1).round(1)
        all_data['郊区站均值'] = all_data[sub_st].mean(axis=1).round(1)

        # 在这个element下的日热岛计算结果，后续的结果在这个日结果的基础上resample
        heat_day = pd.DataFrame(index=all_data.index)
        for k in range(len(combine)):
            a = combine[k][0]
            b = combine[k][1]
            heat_day[a + '/' + b] = (all_data[a] - all_data[b]).round(1)

        heat_day['城市站均值/郊区站均值'] = (all_data['城市站均值'] - all_data['郊区站均值']).round(1)

        # 开始根据输入的time_resolution, 提取年/季/月/日结果
        for time_res in time_resolution:
            if time_res == 'year':
                # 1.气温历年变化结果
                data_year = all_data.resample('1A', closed='right', label='right').mean().round(1)  # 年平均
                data_year.index = data_year.index.year

                # 2.热岛强度历年变化结果
                heat_year = heat_day.resample('1A', closed='right', label='right').mean().round(1)
                heat_year.index = heat_year.index.year

                # 两个表进一步处理
                data_year.loc['平均'] = data_year.mean(axis=0).round(1)
                data_year.loc['最大'] = data_year.max(axis=0).round(1)
                data_year.loc['最小'] = data_year.min(axis=0).round(1)
                data_year.reset_index(inplace=True)
                data_year.rename(columns={'index': '日期'}, inplace=True)

                heat_year.loc['平均'] = heat_year.mean(axis=0).round(1)
                heat_year.loc['最大'] = heat_year.max(axis=0).round(1)
                heat_year.loc['最小'] = heat_year.min(axis=0).round(1)
                heat_year_levels = get_heat_island_levels(heat_year)

                heat_year.reset_index(inplace=True)
                heat_year.rename(columns={'index': '日期'}, inplace=True)

                heat_year_levels.columns = [col + '-热岛强度等级' for col in heat_year_levels.columns]
                heat_year_levels.reset_index(inplace=True)
                heat_year_levels.rename(columns={'index': '日期'}, inplace=True)

                # 年结果装入字典
                if elements[i] == 'TEM_Avg':
                    all_result.Avg.year['温度逐年变化'] = data_year.to_dict(orient='records')
                    all_result.Avg.year['热岛强度逐年变化'] = heat_year.to_dict(orient='records')
                    all_result.Avg.year['热岛强度等级逐年变化'] = heat_year_levels.to_dict(orient='records')

                elif elements[i] == 'TEM_Max':
                    all_result.Max.year['温度逐年变化'] = data_year.to_dict(orient='records')
                    all_result.Max.year['热岛强度逐年变化'] = heat_year.to_dict(orient='records')
                    all_result.Max.year['热岛强度等级逐年变化'] = heat_year_levels.to_dict(orient='records')

                elif elements[i] == 'TEM_Min':
                    all_result.Min.year['温度逐年变化'] = data_year.to_dict(orient='records')
                    all_result.Min.year['热岛强度逐年变化'] = heat_year.to_dict(orient='records')
                    all_result.Min.year['热岛强度等级逐年变化'] = heat_year_levels.to_dict(orient='records')

            elif time_res == 'season':

                rows = ['平均-春季', '平均-夏季', '平均-秋季', '平均-冬季', '最大-春季', '最大-夏季', '最大-秋季', '最大-冬季', '最小-春季', '最小-夏季', '最小-秋季', '最小-冬季']

                # 1.气温历年逐季变化结果
                data_season = all_data.resample('1Q', closed='right', label='right').mean().round(1)  # 季平均

                # 2.气温累年各季变化结果 (平均/最高/最低)
                avg_season_accum = []
                max_season_accum = []
                min_season_accum = []

                for num in [3, 6, 9, 12]:
                    season_i_mean = data_season[data_season.index.month == num].mean().round(1)
                    season_i_max = data_season[data_season.index.month == num].max()
                    season_i_min = data_season[data_season.index.month == num].min()

                    avg_season_accum.append(season_i_mean)
                    max_season_accum.append(season_i_max)
                    min_season_accum.append(season_i_min)

                avg_season_accum = pd.DataFrame(avg_season_accum)
                max_season_accum = pd.DataFrame(max_season_accum)
                min_season_accum = pd.DataFrame(min_season_accum)
                data_season_accum = pd.concat([avg_season_accum, max_season_accum, min_season_accum], axis=0).reset_index(drop=True)

                # 3.热岛强度历年逐季变化结果
                heat_season = heat_day.resample('1Q', closed='right', label='right').mean().round(1)

                # 4.热岛强度累年各季变化结果 (平均/最高/最低)
                avg_heat_accum = []
                max_heat_accum = []
                min_heat_accum = []

                for num in [3, 6, 9, 12]:
                    heat_i_mean = heat_season[heat_season.index.month == num].mean().round(1)
                    heat_i_max = heat_season[heat_season.index.month == num].max()
                    heat_i_min = heat_season[heat_season.index.month == num].min()

                    avg_heat_accum.append(heat_i_mean)
                    max_heat_accum.append(heat_i_max)
                    min_heat_accum.append(heat_i_min)

                avg_heat_accum = pd.DataFrame(avg_heat_accum)
                max_heat_accum = pd.DataFrame(max_heat_accum)
                min_heat_accum = pd.DataFrame(min_heat_accum)
                heat_season_accum = pd.concat([avg_heat_accum, max_heat_accum, min_heat_accum], axis=0).reset_index(drop=True)

                # 四个表进一步处理
                data_season.index = data_season.index.strftime('%Y-%m')
                data_season.loc['平均'] = data_season.mean(axis=0).round(1)
                data_season.loc['最大'] = data_season.max(axis=0).round(1)
                data_season.loc['最小'] = data_season.min(axis=0).round(1)
                data_season.reset_index(inplace=True)
                data_season.rename(columns={'index': '日期'}, inplace=True)

                data_season_accum.index = rows
                data_season_accum.reset_index(inplace=True)

                heat_season.index = heat_season.index.strftime('%Y-%m')
                heat_season.loc['平均'] = heat_season.mean(axis=0).round(1)
                heat_season.loc['最大'] = heat_season.max(axis=0).round(1)
                heat_season.loc['最小'] = heat_season.min(axis=0).round(1)

                heat_season_levels = get_heat_island_levels(heat_season)
                heat_season_levels.columns = [col + '-热岛强度等级' for col in heat_season_levels.columns]
                heat_season_levels.reset_index(inplace=True)
                heat_season_levels.rename(columns={'index': '日期'}, inplace=True)

                heat_season.reset_index(inplace=True)
                heat_season.rename(columns={'index': '日期'}, inplace=True)

                heat_season_accum.index = [str(i) + '月' for i in range(1, 13)]
                heat_season_accum.loc['平均'] = heat_season_accum.mean(axis=0).round(1)
                heat_season_accum.loc['最大'] = heat_season_accum.max(axis=0).round(1)
                heat_season_accum.loc['最小'] = heat_season_accum.min(axis=0).round(1)
                heat_season_accum_levels = get_heat_island_levels(heat_season_accum)
                heat_season_accum_levels.columns = [col + '-热岛强度等级' for col in heat_season_accum_levels.columns]
                heat_season_accum_levels.reset_index(inplace=True)
                heat_season_accum_levels.rename(columns={'index': '日期'}, inplace=True)

                heat_season_accum.reset_index(inplace=True)
                heat_season_accum.rename(columns={'index': '日期'}, inplace=True)

                # 季结果装入字典
                if elements[i] == 'TEM_Avg':
                    all_result.Avg.season['温度逐季变化'] = data_season.to_dict(orient='records')
                    all_result.Avg.season['温度累年各季变化'] = data_season_accum.to_dict(orient='records')
                    all_result.Avg.season['热岛强度逐季变化'] = heat_season.to_dict(orient='records')
                    all_result.Avg.season['热岛强度等级逐季变化'] = heat_season_levels.to_dict(orient='records')
                    all_result.Avg.season['热岛强度累年各季变化'] = heat_season_accum.to_dict(orient='records')
                    all_result.Avg.season['热岛强度等级累年各季变化'] = heat_season_accum_levels.to_dict(orient='records')

                elif elements[i] == 'TEM_Max':
                    all_result.Max.season['温度逐季变化'] = data_season.to_dict(orient='records')
                    all_result.Max.season['温度累年各季变化'] = data_season_accum.to_dict(orient='records')
                    all_result.Max.season['热岛强度逐季变化'] = heat_season.to_dict(orient='records')
                    all_result.Max.season['热岛强度等级逐季变化'] = heat_season_levels.to_dict(orient='records')
                    all_result.Max.season['热岛强度累年各季变化'] = heat_season_accum.to_dict(orient='records')
                    all_result.Max.season['热岛强度等级累年各季变化'] = heat_season_accum_levels.to_dict(orient='records')

                elif elements[i] == 'TEM_Min':
                    all_result.Min.season['温度逐季变化'] = data_season.to_dict(orient='records')
                    all_result.Min.season['温度累年各季变化'] = data_season_accum.to_dict(orient='records')
                    all_result.Min.season['热岛强度逐季变化'] = heat_season.to_dict(orient='records')
                    all_result.Min.season['热岛强度等级逐季变化'] = heat_season_levels.to_dict(orient='records')
                    all_result.Min.season['热岛强度累年各季变化'] = heat_season_accum.to_dict(orient='records')
                    all_result.Min.season['热岛强度等级累年各季变化'] = heat_season_accum_levels.to_dict(orient='records')

            elif time_res == 'month':
                # 1.气温历年逐月变化结果
                data_month = all_data.resample('1M', closed='right', label='right').mean().round(1)

                # 2.气温累年各月变化结果
                avg_month_accum = []
                for num in range(1, 13):
                    month_i_mean = data_month[data_month.index.month == num].mean().round(1)
                    avg_month_accum.append(month_i_mean)

                data_month_accum = pd.DataFrame(avg_month_accum)

                # 3.热岛强度历年逐月变化结果
                heat_month = heat_day.resample('1M', closed='right', label='right').mean().round(1)

                # 4.热岛强度累年各月变化结果
                avg_heat_accum = []
                for num in range(1, 13):
                    heat_i_mean = heat_month[heat_month.index.month == num].mean().round(1)
                    avg_heat_accum.append(heat_i_mean)

                heat_month_accum = pd.DataFrame(avg_heat_accum)

                # 四个表进一步处理
                data_month.index = data_month.index.strftime('%Y-%m')
                data_month.loc['平均'] = data_month.mean(axis=0).round(1)
                data_month.loc['最大'] = data_month.max(axis=0).round(1)
                data_month.loc['最小'] = data_month.min(axis=0).round(1)
                data_month.reset_index(inplace=True)
                data_month.rename(columns={'index': '日期'}, inplace=True)

                data_month_accum.index = [str(i) + '月' for i in range(1, 13)]
                data_month_accum.loc['平均'] = data_month_accum.mean(axis=0).round(1)
                data_month_accum.loc['最大'] = data_month_accum.max(axis=0).round(1)
                data_month_accum.loc['最小'] = data_month_accum.min(axis=0).round(1)
                data_month_accum.reset_index(inplace=True)

                heat_month.index = heat_month.index.strftime('%Y-%m')
                heat_month.loc['平均'] = heat_month.mean(axis=0).round(1)
                heat_month.loc['最大'] = heat_month.max(axis=0).round(1)
                heat_month.loc['最小'] = heat_month.min(axis=0).round(1)

                heat_month_levels = get_heat_island_levels(heat_month)
                heat_month_levels.columns = [col + '-热岛强度等级' for col in heat_month_levels.columns]
                heat_month_levels.reset_index(inplace=True)
                heat_month_levels.rename(columns={'index': '日期'}, inplace=True)
                heat_month.reset_index(inplace=True)
                heat_month.rename(columns={'index': '日期'}, inplace=True)

                heat_month_accum.index = [str(i) + '月' for i in range(1, 13)]
                heat_month_accum.loc['平均'] = heat_month_accum.mean(axis=0).round(1)
                heat_month_accum.loc['最大'] = heat_month_accum.max(axis=0).round(1)
                heat_month_accum.loc['最小'] = heat_month_accum.min(axis=0).round(1)
                heat_month_accum_levels = get_heat_island_levels(heat_month_accum)
                heat_month_accum_levels.columns = [col + '-热岛强度等级' for col in heat_month_accum_levels.columns]
                heat_month_accum_levels.reset_index(inplace=True)
                heat_month_accum_levels.rename(columns={'index': '日期'}, inplace=True)

                heat_month_accum.reset_index(inplace=True)
                heat_month_accum.rename(columns={'index': '日期'}, inplace=True)

                # 月结果装入字典
                if elements[i] == 'TEM_Avg':
                    all_result.Avg.month['温度逐月变化'] = data_month.to_dict(orient='records')
                    all_result.Avg.month['温度累年各月变化'] = data_month_accum.to_dict(orient='records')
                    all_result.Avg.month['热岛强度逐月变化'] = heat_month.to_dict(orient='records')
                    all_result.Avg.month['热岛强度等级逐月变化'] = heat_month_levels.to_dict(orient='records')
                    all_result.Avg.month['热岛强度累年各月变化'] = heat_month_accum.to_dict(orient='records')
                    all_result.Avg.month['热岛强度等级累年各月变化'] = heat_month_accum_levels.to_dict(orient='records')

                elif elements[i] == 'TEM_Max':
                    all_result.Max.month['温度逐月变化'] = data_month.to_dict(orient='records')
                    all_result.Max.month['温度累年各月变化'] = data_month_accum.to_dict(orient='records')
                    all_result.Max.month['热岛强度逐月变化'] = heat_month.to_dict(orient='records')
                    all_result.Max.month['热岛强度等级逐月变化'] = heat_month_levels.to_dict(orient='records')
                    all_result.Max.month['热岛强度累年各月变化'] = heat_month_accum.to_dict(orient='records')
                    all_result.Max.month['热岛强度等级累年各月变化'] = heat_month_accum_levels.to_dict(orient='records')

                elif elements[i] == 'TEM_Min':
                    all_result.Min.month['温度逐月变化'] = data_month.to_dict(orient='records')
                    all_result.Min.month['温度累年各月变化'] = data_month_accum.to_dict(orient='records')
                    all_result.Min.month['热岛强度逐月变化'] = heat_month.to_dict(orient='records')
                    all_result.Min.month['热岛强度等级逐月变化'] = heat_month_levels.to_dict(orient='records')
                    all_result.Min.month['热岛强度累年各月变化'] = heat_month_accum.to_dict(orient='records')
                    all_result.Min.month['热岛强度等级累年各月变化'] = heat_month_accum_levels.to_dict(orient='records')

            elif time_res == 'day':
                # 1.气温逐日变化结果
                data_day = all_data

                # 2.热岛强度逐日变化结果
                heat_day_levels = get_heat_island_levels(heat_day)
                heat_day_levels.columns = [col + '-热岛强度等级' for col in heat_day_levels.columns]

                # 三个表进一步处理
                data_day.index = data_day.index.strftime('%Y-%m-%d')
                data_day.reset_index(inplace=True)
                data_day.rename(columns={'index': '日期'}, inplace=True)

                heat_day.index = heat_day.index.strftime('%Y-%m-%d')
                heat_day.reset_index(inplace=True)
                heat_day.rename(columns={'index': '日期'}, inplace=True)

                heat_day_levels.index = heat_day_levels.index.strftime('%Y-%m-%d')
                heat_day_levels.reset_index(inplace=True)
                heat_day_levels.rename(columns={'index': '日期'}, inplace=True)

                # 日结果装入字典
                if elements[i] == 'TEM_Avg':
                    all_result.Avg.day['温度逐日变化'] = data_day.to_dict(orient='records')
                    all_result.Avg.day['热岛强度逐日变化'] = heat_day.to_dict(orient='records')
                    all_result.Avg.day['热岛强度等级逐日变化'] = heat_day_levels.to_dict(orient='records')

                elif elements[i] == 'TEM_Max':
                    all_result.Max.day['温度逐日变化'] = data_day.to_dict(orient='records')
                    all_result.Max.day['热岛强度逐日变化'] = heat_day.to_dict(orient='records')
                    all_result.Max.day['热岛强度等级逐日变化'] = heat_day_levels.to_dict(orient='records')

                elif elements[i] == 'TEM_Min':
                    all_result.Min.day['温度逐日变化'] = data_day.to_dict(orient='records')
                    all_result.Min.day['热岛强度逐日变化'] = heat_day.to_dict(orient='records')
                    all_result.Min.day['热岛强度等级逐日变化'] = heat_day_levels.to_dict(orient='records')

    return all_result


if __name__ == '__main__':
    
    df_day = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    df_day.loc[df_day['Station_Id_C'] == '52842', 'TEM_Avg'] = np.nan
    main_st_ids = ['52955', '52713']
    sub_st_ids = ['52842', '52874', '56029', '56043']
    main_st_ids_str = '52955, 52713'
    sub_st_ids_str = '52842, 52874, 56029, 56043'
    time_resolution = ['year', 'season', 'month', 'day']
    data_types = ['Avg']
    daily_elements = ''
    for type_ in data_types:
        if equalsIgnoreCase(type_, 'Avg'):
            daily_elements += 'TEM_Avg,'
        elif equalsIgnoreCase(type_, 'Max'):
            daily_elements += 'TEM_Max,'
        elif equalsIgnoreCase(type_, 'Min'):
            daily_elements += 'TEM_Min,'
            
    day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements[:-1]).split(',')

    sta_ids = main_st_ids_str + ',' + sub_st_ids_str
    sta_ids_int = [int(ids) for ids in sta_ids.split(',')]
    daily_df = df_day.loc[df_day['Station_Id_C'].isin(sta_ids_int), day_eles]

    df_day = daily_data_processing(daily_df)

    all_result = calc_heat_island(df_day, main_st_ids, sub_st_ids, time_resolution, data_types)
