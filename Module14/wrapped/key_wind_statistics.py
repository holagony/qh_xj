'''
关键因子-风速
'''
import logging
import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.get_local_data import get_local_data
# from Report.code.Module02.wind import wind_report


def key_wind_statistics(wind_day, wind_month):
    '''
    温度要素，历年和累年各月统计，
    使用天擎上的年数据和月数据，要素名称为天擎上默认的名称
    年值要素：['Station_Id_C', 'Station_Name', 'Year', 'WIN_S_Max', 'WIN_S_Inst_Max']
    月值要素：['Station_Id_C', 'Station_Name', 'Year', 'WIN_S_Max', 'WIN_S_Inst_Max']
    return: dataframe
    '''
    try:
        if 'Station_Name' in wind_day.columns:
            yearly_records = []
            for station, df in wind_day.groupby('Station_Name'):
                max_dates = df.dropna(subset=['WIN_S_Max']).groupby(lambda x: x.year)['WIN_S_Max'].idxmax()
                max_info = df.loc[max_dates[max_dates.notna()], ['WIN_S_Max']]
                max_info['最大风速出现日期'] = max_info.index.strftime('%m月%d日')
                max_info.index = max_info.index.year

                inst_dates = df.dropna(subset=['WIN_S_Inst_Max']).groupby(lambda x: x.year)['WIN_S_Inst_Max'].idxmax()
                inst_info = df.loc[inst_dates[inst_dates.notna()], ['WIN_S_Inst_Max']]
                inst_info['极大风速出现日期'] = inst_info.index.strftime('%m月%d日')
                inst_info.index = inst_info.index.year

                yearly_df = pd.concat([max_info, inst_info], axis=1)
                yearly_df.insert(loc=0, column='年份', value=yearly_df.index)
                yearly_df.reset_index(drop=True, inplace=True)
                yearly_df.insert(loc=0, column='站名', value=station)
                yearly_df.columns = ['站名', '年份', '最大风速(m/s)', '最大风速出现日期', '极大风速(m/s)', '极大风速出现日期']
                yearly_records.extend(yearly_df.to_dict(orient='records'))

            basic_wind_yearly = yearly_records if len(yearly_records) != 0 else None

        else:
            max_wind_dates = wind_day.dropna(subset=['WIN_S_Max']).groupby(lambda x: x.year)['WIN_S_Max'].idxmax()
            max_wind_info = wind_day.loc[max_wind_dates[max_wind_dates.notna()], ['WIN_S_Max']]
            max_wind_info['最大风速出现日期'] = max_wind_info.index.strftime('%m月%d日')
            max_wind_info.index = max_wind_info.index.year

            inst_wind_dates = wind_day.dropna(subset=['WIN_S_Inst_Max']).groupby(lambda x: x.year)['WIN_S_Inst_Max'].idxmax()
            inst_wind_info = wind_day.loc[inst_wind_dates[inst_wind_dates.notna()], ['WIN_S_Inst_Max']]
            inst_wind_info['极大风速出现日期'] = inst_wind_info.index.strftime('%m月%d日')
            inst_wind_info.index = inst_wind_info.index.year

            basic_wind_yearly = pd.concat([max_wind_info, inst_wind_info], axis=1)
            basic_wind_yearly.insert(loc=0, column='年份', value=basic_wind_yearly.index)
            basic_wind_yearly.reset_index(drop=True, inplace=True)
            basic_wind_yearly.columns = ['年份', '最大风速(m/s)', '最大风速出现日期', '极大风速(m/s)', '极大风速出现日期']
            basic_wind_yearly = basic_wind_yearly.to_dict(orient='records')

    except Exception as e:
        logging.exception(e)
        basic_wind_yearly = None

    finally:
        try:
            if 'Station_Name' in wind_month.columns:
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

                for station, dfm in wind_month.groupby('Station_Name'):
                    WIN_S_Max = dfm[['WIN_S_Max', 'WIN_S_Max_ODay_C', 'Year', 'Mon']]
                    WIN_S_Inst_Max = dfm[['WIN_S_Inst_Max', 'WIN_S_INST_Max_ODay_C', 'Year', 'Mon']]

                    max_wind_accum = []
                    inst_wind_accum = []

                    for i in range(1, 13):
                        month_i_max = WIN_S_Max[WIN_S_Max.index.month == i]
                        month_i_max = month_i_max[month_i_max['WIN_S_Max'] == month_i_max['WIN_S_Max'].max()]

                        if len(month_i_max) > 1:
                            wind_data = month_i_max.iloc[0, 0]
                            occur_day = str(month_i_max['WIN_S_Max_ODay_C'].apply(sample).sum()) + 'T'
                            occur_year = str(len(month_i_max)) + 'N'
                            occur_month = month_i_max.iloc[0, 3]
                            array = np.array([wind_data, occur_day, occur_year, occur_month]).reshape(1, -1)
                            max_df = pd.DataFrame(array, columns=['WIN_S_Max', 'WIN_S_Max_ODay_C', 'Year', 'Mon'], index=[month_i_max.index[0]])
                        else:
                            max_df = month_i_max[['WIN_S_Max', 'WIN_S_Max_ODay_C', 'Year', 'Mon']]

                        max_wind_accum.append(max_df)

                        month_i_max = WIN_S_Inst_Max[WIN_S_Inst_Max.index.month == i]
                        month_i_max = month_i_max[month_i_max['WIN_S_Inst_Max'] == month_i_max['WIN_S_Inst_Max'].max()]

                        if len(month_i_max) > 1:
                            wind_data = month_i_max.iloc[0, 0]
                            occur_day = str(month_i_max['WIN_S_INST_Max_ODay_C'].apply(sample).sum()) + 'T'
                            occur_year = str(len(month_i_max)) + 'N'
                            occur_month = month_i_max.iloc[0, 3]
                            array = np.array([wind_data, occur_day, occur_year, occur_month]).reshape(1, -1)
                            inst_df = pd.DataFrame(array, columns=['WIN_S_Inst_Max', 'WIN_S_INST_Max_ODay_C', 'Year', 'Mon'], index=[month_i_max.index[0]])
                        else:
                            inst_df = month_i_max[['WIN_S_Inst_Max', 'WIN_S_INST_Max_ODay_C', 'Year', 'Mon']]

                        inst_wind_accum.append(inst_df)

                    max_wind_accum = pd.concat(max_wind_accum, axis=0, ignore_index=True)
                    max_wind_accum['WIN_S_Max'] = max_wind_accum['WIN_S_Max'].astype(float)
                    max_row = max_wind_accum[max_wind_accum['WIN_S_Max'] == max_wind_accum['WIN_S_Max'].max()].reset_index(drop=True)

                    if len(max_row) == 1:
                        wind_v = max_row.loc[0, 'WIN_S_Max']
                        date_v = max_row['Mon'].map(str) + '-' + max_row['WIN_S_Max_ODay_C'].map(str)
                        year_v = max_row.loc[0, 'Year']
                        values_list_max = [wind_v, date_v.values[0], year_v]
                    else:
                        wind_v = max_row.loc[0, 'WIN_S_Max']
                        date_v = str(len(max_row)) + 'T'
                        year_v = str(max_row['Year'].apply(sample).sum()) + 'N'
                        values_list_max = [wind_v, date_v, year_v]

                    max_wind_accum.drop('Mon', axis=1, inplace=True)
                    max_wind_accum = max_wind_accum.T
                    max_wind_accum.index = ['最大风速(m/s)', '最大风速出现日期', '最大风速出现年份']
                    max_wind_accum['全年'] = values_list_max

                    inst_wind_accum = pd.concat(inst_wind_accum, axis=0, ignore_index=True)
                    inst_wind_accum['WIN_S_Inst_Max'] = inst_wind_accum['WIN_S_Inst_Max'].astype(float)
                    inst_row = inst_wind_accum[inst_wind_accum['WIN_S_Inst_Max'] == inst_wind_accum['WIN_S_Inst_Max'].max()].reset_index(drop=True)

                    if len(inst_row) == 1:
                        wind_v = inst_row.loc[0, 'WIN_S_Inst_Max']
                        date_v = inst_row['Mon'].map(str) + '-' + inst_row['WIN_S_INST_Max_ODay_C'].map(str)
                        year_v = inst_row.loc[0, 'Year']
                        values_list_max = [wind_v, date_v.values[0], year_v]
                    else:
                        wind_v = inst_row.loc[0, 'WIN_S_Inst_Max']
                        date_v = str(len(inst_row)) + 'T'
                        year_v = str(inst_row['Year'].apply(sample).sum()) + 'N'
                        values_list_max = [wind_v, date_v, year_v]

                    inst_wind_accum.drop('Mon', axis=1, inplace=True)
                    inst_wind_accum = inst_wind_accum.T
                    inst_wind_accum.index = ['极大风速(m/s)', '极大风速出现日期', '极大风速出现年份']
                    inst_wind_accum['全年'] = values_list_max

                    basic_wind_accum_station = pd.concat([max_wind_accum, inst_wind_accum], axis=0)

                    month_list = [str(i) + '月' for i in range(1, 13)]
                    month_list.append('年')
                    basic_wind_accum_station.columns = month_list
                    basic_wind_accum_station.reset_index(inplace=True)
                    basic_wind_accum_station.rename(columns={'index': '要素'}, inplace=True)
                    basic_wind_accum_station.insert(loc=0, column='站名', value=station)

                    accum_records.extend(basic_wind_accum_station.to_dict(orient='records'))

                basic_wind_accum = accum_records if len(accum_records) != 0 else None

            else:
                WIN_S_Max = wind_month[['WIN_S_Max', 'WIN_S_Max_ODay_C', 'Year', 'Mon']]
                WIN_S_Inst_Max = wind_month[['WIN_S_Inst_Max', 'WIN_S_INST_Max_ODay_C', 'Year', 'Mon']]

                max_wind_accum = []
                inst_wind_accum = []

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
                    month_i_max = WIN_S_Max[WIN_S_Max.index.month == i]
                    month_i_max = month_i_max[month_i_max['WIN_S_Max'] == month_i_max['WIN_S_Max'].max()]

                    if len(month_i_max) > 1:
                        wind_data = month_i_max.iloc[0, 0]
                        occur_year = str(len(month_i_max)) + 'N'
                        occur_month = month_i_max.iloc[0, 3]
                        array = np.array([wind_data, occur_year, occur_month]).reshape(1, -1)
                        max_df = pd.DataFrame(array, columns=['WIN_S_Max', 'Year', 'Mon'], index=[month_i_max.index[0]])
                    else:
                        max_df = month_i_max[['WIN_S_Max', 'Year', 'Mon']]

                    max_wind_accum.append(max_df)

                    month_i_max = WIN_S_Inst_Max[WIN_S_Inst_Max.index.month == i]
                    month_i_max = month_i_max[month_i_max['WIN_S_Inst_Max'] == month_i_max['WIN_S_Inst_Max'].max()]

                    if len(month_i_max) > 1:
                        wind_data = month_i_max.iloc[0, 0]
                        occur_year = str(len(month_i_max)) + 'N'
                        occur_month = month_i_max.iloc[0, 3]
                        array = np.array([wind_data, occur_year, occur_month]).reshape(1, -1)
                        inst_df = pd.DataFrame(array, columns=['WIN_S_Inst_Max', 'Year', 'Mon'], index=[month_i_max.index[0]])
                    else:
                        inst_df = month_i_max[['WIN_S_Inst_Max', 'Year', 'Mon']]

                    inst_wind_accum.append(inst_df)

                max_wind_accum = pd.concat(max_wind_accum, axis=0, ignore_index=True)
                max_wind_accum['WIN_S_Max'] = max_wind_accum['WIN_S_Max'].astype(float)
                max_row = max_wind_accum[max_wind_accum['WIN_S_Max'] == max_wind_accum['WIN_S_Max'].max()].reset_index(drop=True)

                if len(max_row) == 1:
                    wind_v = max_row.loc[0, 'WIN_S_Max']
                    date_v = max_row['Mon'].map(str) + '-' + max_row['WIN_S_Max_ODay_C'].map(str)
                    year_v = max_row.loc[0, 'Year']
                    values_list_max = [wind_v, date_v.values[0], year_v]
                else:
                    wind_v = max_row.loc[0, 'WIN_S_Max']
                    date_v = str(len(max_row)) + 'T'
                    year_v = str(max_row['Year'].apply(sample).sum()) + 'N'
                    values_list_max = [wind_v, date_v, year_v]

                max_wind_accum.drop('Mon', axis=1, inplace=True)
                max_wind_accum = max_wind_accum.T
                max_wind_accum.index = ['最大风速(m/s)', '最大风速出现日期', '最大风速出现年份']
                max_wind_accum['全年'] = values_list_max

                inst_wind_accum = pd.concat(inst_wind_accum, axis=0, ignore_index=True)
                inst_wind_accum['WIN_S_Inst_Max'] = inst_wind_accum['WIN_S_Inst_Max'].astype(float)
                inst_row = inst_wind_accum[inst_wind_accum['WIN_S_Inst_Max'] == inst_wind_accum['WIN_S_Inst_Max'].max()].reset_index(drop=True)

                if len(inst_row) == 1:
                    wind_v = inst_row.loc[0, 'WIN_S_Inst_Max']
                    date_v = inst_row['Mon'].map(str) + '-' + inst_row['WIN_S_INST_Max_ODay_C'].map(str)
                    year_v = inst_row.loc[0, 'Year']
                    values_list_max = [wind_v, date_v.values[0], year_v]
                else:
                    wind_v = inst_row.loc[0, 'WIN_S_Inst_Max']
                    date_v = str(len(inst_row)) + 'T'
                    year_v = str(inst_row['Year'].apply(sample).sum()) + 'N'
                    values_list_max = [wind_v, date_v, year_v]

                inst_wind_accum.drop('Mon', axis=1, inplace=True)
                inst_wind_accum = inst_wind_accum.T
                inst_wind_accum.index = ['极大风速(m/s)', '极大风速出现日期', '极大风速出现年份']
                inst_wind_accum['全年'] = values_list_max

                basic_wind_accum = pd.concat([max_wind_accum, inst_wind_accum], axis=0)
                month_list = [str(i) + '月' for i in range(1, 13)]
                month_list.append('年')
                basic_wind_accum.columns = month_list
                basic_wind_accum.reset_index(inplace=True)
                basic_wind_accum.rename(columns={'index': '要素'}, inplace=True)

                tmp = basic_wind_accum.dropna(axis=1, how='all')
                if len(tmp.columns) <= 1:
                    basic_wind_accum = None
                else:
                    basic_wind_accum = basic_wind_accum.to_dict(orient='records')

        except Exception as e:
            logging.exception(e)
            basic_wind_accum = None

        finally:
            report_path = None
            return basic_wind_yearly, basic_wind_accum, report_path


if __name__ == '__main__':
    daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    monthly_df = pd.read_csv(cfg.FILES.QH_DATA_MONTH, low_memory=False)
    sta_ids = '52866,52713'
    years = '2000,2020'

    daily_elements = 'WIN_S_Max,WIN_S_Inst_Max,'
    day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements[:-1]).split(',')
    post_daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')
    
    monthly_elements = 'WIN_S_Max,WIN_S_Inst_Max,WIN_S_Max_ODay_C,WIN_S_INST_Max_ODay_C,'
    month_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,' + monthly_elements[:-1]).split(',')
    post_monthly_df = get_local_data(monthly_df, sta_ids, month_eles, years, 'Month')
    
    wind_day = post_daily_df.copy()
    wind_month = post_monthly_df.copy()
    basic_wind_yearly, basic_wind_accum, report_path = key_wind_statistics(post_daily_df, post_monthly_df)
