'''
关键因子-极端气温
'''
import logging
import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.get_local_data import get_local_data
# from Report.code.Module02.tem import tem_report


def key_tem_statistics(tem_day, tem_month):
    '''
    温度要素，历年和累年各月统计，
    使用天擎上的年数据和月数据，要素名称为天擎上默认的名称
    年值要素：['Station_Id_C', 'Station_Name', 'Year', 'TEM_Max', 'TEM_Min']
    月值要素：['Station_Id_C', 'Station_Name', 'Year', 'Mon', 'TEM_Max','TEM_Min']
    return: dataframe
    '''
    try:
        if 'Station_Name' in tem_day.columns:
            yearly_records = []
            for station, df in tem_day.groupby('Station_Name'):
                max_dates = df.dropna(subset=['TEM_Max']).groupby(lambda x: x.year)['TEM_Max'].idxmax()
                max_info = df.loc[max_dates[max_dates.notna()], ['TEM_Max']]
                max_info['最高气温出现日期'] = max_info.index.strftime('%m月%d日')
                max_info.index = max_info.index.year

                min_dates = df.dropna(subset=['TEM_Min']).groupby(lambda x: x.year)['TEM_Min'].idxmin()
                min_info = df.loc[min_dates[min_dates.notna()], ['TEM_Min']]
                min_info['最低气温出现日期'] = min_info.index.strftime('%m月%d日')
                min_info.index = min_info.index.year

                yearly_df = pd.concat([max_info, min_info], axis=1)
                yearly_df.insert(loc=0, column='年份', value=yearly_df.index)
                yearly_df.reset_index(drop=True, inplace=True)
                yearly_df.insert(loc=0, column='站名', value=station)
                yearly_df.columns = ['站名', '年份', '极端最高气温(°C)', '极端最高气温出现日期', '极端最低气温(°C)', '极端最低气温出现日期']
                yearly_records.extend(yearly_df.to_dict(orient='records'))

            basic_tem_yearly = yearly_records if len(yearly_records) != 0 else None

        else:
            max_tem_dates = tem_day.dropna(subset=['TEM_Max']).groupby(lambda x: x.year)['TEM_Max'].idxmax()
            max_tem_info = tem_day.loc[max_tem_dates[max_tem_dates.notna()], ['TEM_Max']]
            max_tem_info['最高气温出现日期'] = max_tem_info.index.strftime('%m月%d日')
            max_tem_info.index = max_tem_info.index.year

            min_tem_dates = tem_day.dropna(subset=['TEM_Min']).groupby(lambda x: x.year)['TEM_Min'].idxmin()
            min_tem_info = tem_day.loc[min_tem_dates[min_tem_dates.notna()], ['TEM_Min']]
            min_tem_info['最低气温出现日期'] = min_tem_info.index.strftime('%m月%d日')
            min_tem_info.index = min_tem_info.index.year

            basic_tem_yearly = pd.concat([max_tem_info, min_tem_info], axis=1)
            basic_tem_yearly.insert(loc=0, column='年份', value=basic_tem_yearly.index)
            basic_tem_yearly.reset_index(drop=True, inplace=True)
            basic_tem_yearly.columns = ['年份', '极端最高气温(°C)', '极端最高气温出现日期', '极端最低气温(°C)', '极端最低气温出现日期']
            basic_tem_yearly = basic_tem_yearly.to_dict(orient='records')

    except Exception as e:
        logging.exception(e)
        basic_tem_yearly = None

    finally:
        try:
            if 'Station_Name' in tem_month.columns:
                accum_records = []

                def sample(x):
                    x = str(x)
                    if 'T' in x:
                        x = int(x[:-1])
                    elif 'N' in x:
                        x = int(x[:-1])
                    else:
                        x = 1
                    return x

                for station, dfm in tem_month.groupby('Station_Name'):
                    tem_max = dfm[['TEM_Max', 'TEM_Max_ODay_C', 'Year', 'Mon']]
                    tem_min = dfm[['TEM_Min', 'TEM_Min_ODay_C', 'Year', 'Mon']]

                    max_tem_accum = []
                    min_tem_accum = []

                    for i in range(1, 13):
                        month_i_max = tem_max[tem_max.index.month == i]
                        month_i_max = month_i_max[month_i_max['TEM_Max'] == month_i_max['TEM_Max'].max()]

                        if len(month_i_max) > 1:
                            tem_data = month_i_max.iloc[0, 0]
                            occur_day = str(month_i_max['TEM_Max_ODay_C'].apply(sample).sum()) + 'T'
                            occur_year = str(len(month_i_max)) + 'N'
                            occur_month = month_i_max.iloc[0, 3]
                            array = np.array([tem_data, occur_day, occur_year, occur_month]).reshape(1, -1)
                            max_df = pd.DataFrame(array, columns=['TEM_Max', 'TEM_Max_ODay_C', 'Year', 'Mon'], index=[month_i_max.index[0]])
                        else:
                            max_df = month_i_max[['TEM_Max', 'TEM_Max_ODay_C', 'Year', 'Mon']]

                        max_tem_accum.append(max_df)

                        month_i_min = tem_min[tem_min.index.month == i]
                        month_i_min = month_i_min[month_i_min['TEM_Min'] == month_i_min['TEM_Min'].min()]

                        if len(month_i_min) > 1:
                            tem_data = month_i_min.iloc[0, 0]
                            occur_day = str(month_i_min['TEM_Min_ODay_C'].apply(sample).sum()) + 'T'
                            occur_year = str(len(month_i_min)) + 'N'
                            occur_month = month_i_max.iloc[0, 3]
                            array = np.array([tem_data, occur_day, occur_year, occur_month]).reshape(1, -1)
                            min_df = pd.DataFrame(array, columns=['TEM_Min', 'TEM_Min_ODay_C', 'Year', 'Mon'], index=[month_i_min.index[0]])
                        else:
                            min_df = month_i_min[['TEM_Min', 'TEM_Min_ODay_C', 'Year', 'Mon']]

                        min_tem_accum.append(min_df)

                    max_tem_accum = pd.concat(max_tem_accum, axis=0, ignore_index=True)
                    max_tem_accum['TEM_Max'] = max_tem_accum['TEM_Max'].astype(float)
                    max_row = max_tem_accum[max_tem_accum['TEM_Max'] == max_tem_accum['TEM_Max'].max()].reset_index(drop=True)

                    if len(max_row) == 1:
                        tem_v = max_row.loc[0, 'TEM_Max']
                        date_v = max_row['Mon'].map(str) + '-' + max_row['TEM_Max_ODay_C'].map(str)
                        year_v = max_row.loc[0, 'Year']
                        values_list_max = [tem_v, date_v.values[0], year_v]
                    else:
                        tem_v = max_row.loc[0, 'TEM_Max']
                        date_v = str(len(max_row)) + 'T'
                        year_v = str(max_row['Year'].apply(sample).sum()) + 'N'
                        values_list_max = [tem_v, date_v, year_v]

                    max_tem_accum.drop('Mon', axis=1, inplace=True)
                    max_tem_accum = max_tem_accum.T
                    max_tem_accum.index = ['极端最高气温(°C)', '极端最高气温出现日期', '极端最高气温出现年份']
                    max_tem_accum['全年'] = values_list_max

                    min_tem_accum = pd.concat(min_tem_accum, axis=0, ignore_index=True)
                    min_tem_accum['TEM_Min'] = min_tem_accum['TEM_Min'].astype(float)
                    min_row = min_tem_accum[min_tem_accum['TEM_Min'] == min_tem_accum['TEM_Min'].min()].reset_index(drop=True)

                    if len(min_row) == 1:
                        tem_v = min_row.loc[0, 'TEM_Min']
                        date_v = min_row['Mon'].map(str) + '-' + min_row['TEM_Min_ODay_C'].map(str)
                        year_v = min_row.loc[0, 'Year']
                        values_list_min = [tem_v, date_v.values[0], year_v]
                    else:
                        tem_v = min_row.loc[0, 'TEM_Min']
                        date_v = str(len(min_row)) + 'T'
                        year_v = str(min_row['Year'].apply(sample).sum()) + 'N'
                        values_list_min = [tem_v, date_v, year_v]

                    min_tem_accum.drop('Mon', axis=1, inplace=True)
                    min_tem_accum = min_tem_accum.T
                    min_tem_accum.index = ['极端最低气温(°C)', '极端最低气温出现日期', '极端最低气温出现年份']
                    min_tem_accum['全年'] = values_list_min

                    basic_tem_accum_station = pd.concat([max_tem_accum, min_tem_accum], axis=0)

                    month_list = [str(i) + '月' for i in range(1, 13)]
                    month_list.append('年')
                    basic_tem_accum_station.columns = month_list
                    basic_tem_accum_station.reset_index(inplace=True)
                    basic_tem_accum_station.rename(columns={'index': '要素'}, inplace=True)
                    basic_tem_accum_station.insert(loc=0, column='站名', value=station)

                    accum_records.extend(basic_tem_accum_station.to_dict(orient='records'))

                basic_tem_accum = accum_records if len(accum_records) != 0 else None

            else:
                tem_max = tem_month[['TEM_Max', 'TEM_Max_ODay_C', 'Year', 'Mon']]
                tem_min = tem_month[['TEM_Min', 'TEM_Min_ODay_C', 'Year', 'Mon']]

                max_tem_accum = []
                min_tem_accum = []

                def sample(x):
                    x = str(x)
                    if 'T' in x:
                        x = int(x[:-1])
                    elif 'N' in x:
                        x = int(x[:-1])
                    else:
                        x = 1
                    return x

                for i in range(1, 13):
                    month_i_max = tem_max[tem_max.index.month == i]
                    month_i_max = month_i_max[month_i_max['TEM_Max'] == month_i_max['TEM_Max'].max()]

                    if len(month_i_max) > 1:
                        tem_data = month_i_max.iloc[0, 0]
                        occur_year = str(len(month_i_max)) + 'N'
                        occur_month = month_i_max.iloc[0, 3]
                        array = np.array([tem_data, occur_year, occur_month]).reshape(1, -1)
                        max_df = pd.DataFrame(array, columns=['TEM_Max', 'Year', 'Mon'], index=[month_i_max.index[0]])
                    else:
                        max_df = month_i_max[['TEM_Max', 'Year', 'Mon']]

                    max_tem_accum.append(max_df)

                    month_i_min = tem_min[tem_min.index.month == i]
                    month_i_min = month_i_min[month_i_min['TEM_Min'] == month_i_min['TEM_Min'].min()]

                    if len(month_i_min) > 1:
                        tem_data = month_i_min.iloc[0, 0]
                        occur_year = str(len(month_i_min)) + 'N'
                        occur_month = month_i_max.iloc[0, 3]
                        array = np.array([tem_data, occur_year, occur_month]).reshape(1, -1)
                        min_df = pd.DataFrame(array, columns=['TEM_Min', 'Year', 'Mon'], index=[month_i_min.index[0]])
                    else:
                        min_df = month_i_min[['TEM_Min', 'Year', 'Mon']]

                    min_tem_accum.append(min_df)

                max_tem_accum = pd.concat(max_tem_accum, axis=0, ignore_index=True)
                max_tem_accum['TEM_Max'] = max_tem_accum['TEM_Max'].astype(float)
                max_row = max_tem_accum[max_tem_accum['TEM_Max'] == max_tem_accum['TEM_Max'].max()].reset_index(drop=True)

                if len(max_row) == 1:
                    tem_v = max_row.loc[0, 'TEM_Max']
                    date_v = max_row['Mon'].map(str) + '-' + max_row['TEM_Max_ODay_C'].map(str)
                    year_v = max_row.loc[0, 'Year']
                    values_list_max = [tem_v, date_v.values[0], year_v]
                else:
                    tem_v = max_row.loc[0, 'TEM_Max']
                    date_v = str(len(max_row)) + 'T'
                    year_v = str(max_row['Year'].apply(sample).sum()) + 'N'
                    values_list_max = [tem_v, date_v, year_v]

                max_tem_accum.drop('Mon', axis=1, inplace=True)
                max_tem_accum = max_tem_accum.T
                max_tem_accum.index = ['极端最高气温(°C)', '极端最高气温出现日期', '极端最高气温出现年份']
                max_tem_accum['全年'] = values_list_max

                min_tem_accum = pd.concat(min_tem_accum, axis=0, ignore_index=True)
                min_tem_accum['TEM_Min'] = min_tem_accum['TEM_Min'].astype(float)
                min_row = min_tem_accum[min_tem_accum['TEM_Min'] == min_tem_accum['TEM_Min'].min()].reset_index(drop=True)

                if len(min_row) == 1:
                    tem_v = min_row.loc[0, 'TEM_Min']
                    date_v = min_row['Mon'].map(str) + '-' + min_row['TEM_Min_ODay_C'].map(str)
                    year_v = min_row.loc[0, 'Year']
                    values_list_min = [tem_v, date_v.values[0], year_v]
                else:
                    tem_v = min_row.loc[0, 'TEM_Min']
                    date_v = str(len(min_row)) + 'T'
                    year_v = str(min_row['Year'].apply(sample).sum()) + 'N'
                    values_list_min = [tem_v, date_v, year_v]

                min_tem_accum.drop('Mon', axis=1, inplace=True)
                min_tem_accum = min_tem_accum.T
                min_tem_accum.index = ['极端最低气温(°C)', '极端最低气温出现日期', '极端最低气温出现年份']
                min_tem_accum['全年'] = values_list_min

                basic_tem_accum = pd.concat([max_tem_accum, min_tem_accum], axis=0)
                month_list = [str(i) + '月' for i in range(1, 13)]
                month_list.append('年')
                basic_tem_accum.columns = month_list
                basic_tem_accum.reset_index(inplace=True)
                basic_tem_accum.rename(columns={'index': '要素'}, inplace=True)

                tmp = basic_tem_accum.dropna(axis=1, how='all')
                if len(tmp.columns) <= 1:
                    basic_tem_accum = None
                else:
                    basic_tem_accum = basic_tem_accum.to_dict(orient='records')

        except Exception as e:
            logging.exception(e)
            basic_tem_accum = None

        finally:
            report_path = None
            return basic_tem_yearly, basic_tem_accum, report_path


if __name__ == '__main__':
    daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    monthly_df = pd.read_csv(cfg.FILES.QH_DATA_MONTH, low_memory=False)
    sta_ids = '52866,52713'
    years = '2000,2020'

    daily_elements = 'TEM_Max,TEM_Min,'
    day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements[:-1]).split(',')
    post_daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')
    
    monthly_elements = 'TEM_Max,TEM_Min,TEM_Max_ODay_C,TEM_Min_ODay_C,'
    month_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,' + monthly_elements[:-1]).split(',')
    post_monthly_df = get_local_data(monthly_df, sta_ids, month_eles, years, 'Month')
    
    tem_day = post_daily_df.copy()
    tem_month = post_monthly_df.copy()
    basic_tem_yearly, basic_tem_accum, report_path = key_tem_statistics(post_daily_df, post_monthly_df)
