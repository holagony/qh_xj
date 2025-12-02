'''
关键因子-冻土深度
'''
import logging
import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.get_local_data import get_local_data


def compute_frs_month_from_day(df):

    if 'Datetime' not in df.columns:
        month_col = 'Mon' if 'Mon' in df.columns else ('Month' if 'Month' in df.columns else None)
        year_col = 'Year' if 'Year' in df.columns else None
        day_col = 'Day' if 'Day' in df.columns else None

        if month_col and year_col and day_col:
            df['Datetime'] = pd.to_datetime({
                'year': df[year_col].astype(int),
                'month': df[month_col].astype(int),
                'day': df[day_col].astype(int)
            })
        elif 'Datetime' in frs_day.columns:
            df['Datetime'] = pd.to_datetime(frs_day['Datetime'])
        else:
            raise ValueError('缺少 Year/Mon/Day 或 Datetime 字段，无法组装日期')
    else:
        df['Datetime'] = pd.to_datetime(df['Datetime'])

    if 'Year' not in df.columns:
        df['Year'] = df['Datetime'].dt.year
    if 'Mon' not in df.columns:
        df['Mon'] = df['Datetime'].dt.month
    if 'Day' not in df.columns:
        df['Day'] = df['Datetime'].dt.day

    records = []
    if 'Station_Name' in df.columns:
        for station, dfg in df.groupby(['Station_Name', 'Year', 'Mon']):
            max_val = dfg['frs'].astype(float).max()
            max_rows = dfg[dfg['frs'].astype(float) == max_val]
            year_v = int(dfg['Year'].iloc[0])
            mon_v = int(dfg['Mon'].iloc[0])
            if len(max_rows) == 1:
                day_v = int(max_rows['Day'].iloc[0])
                dt = pd.Timestamp(year_v, mon_v, day_v)
                oday = day_v
            else:
                dt = pd.Timestamp(year_v, mon_v, 1)
                oday = str(len(max_rows)) + 'T'

            rec = {
                'Station_Name': dfg['Station_Name'].iloc[0],
                'FRS_Depth_Max_Day': float(max_val),
                'FRS_Depth_Max_ODay_C': oday,
                'Year': year_v,
                'Mon': mon_v,
                'Datetime': dt
            }
            if 'Station_Id_C' in dfg.columns:
                rec['Station_Id_C'] = dfg['Station_Id_C'].iloc[0]
            records.append(rec)
    else:
        for (year_v, mon_v), dfg in df.groupby(['Year', 'Mon']):
            max_val = dfg['frs'].astype(float).max()
            max_rows = dfg[dfg['frs'].astype(float) == max_val]
            if len(max_rows) == 1:
                day_v = int(max_rows['Day'].iloc[0])
                dt = pd.Timestamp(int(year_v), int(mon_v), day_v)
                oday = day_v
            else:
                dt = pd.Timestamp(int(year_v), int(mon_v), 1)
                oday = str(len(max_rows)) + 'T'

            rec = {
                'FRS_Depth_Max_Day': float(max_val),
                'FRS_Depth_Max_ODay_C': oday,
                'Year': int(year_v),
                'Mon': int(mon_v),
                'Datetime': dt
            }
            records.append(rec)

    out = pd.DataFrame(records)
    out.set_index('Datetime', inplace=True)
    return out


def key_frs_statistics(frs_day):
    try:
        if ('FRS_1st_Bot' in frs_day.columns) or ('FRS_2nd_Bot' in frs_day.columns):
            frs_day['frs'] = frs_day[[c for c in ['FRS_1st_Bot', 'FRS_2nd_Bot'] if c in frs_day.columns]].max(axis=1).fillna(0)
        else:
            raise ValueError('缺少 FRS_1st_Bot/FRS_2nd_Bot 字段，无法计算冻土深度')
        frs_day['frs'] = frs_day['frs'].astype(float).round(1)
        if 'Station_Name' in frs_day.columns:
            yearly_records = []
            for station, df in frs_day.groupby('Station_Name'):
                max_dates = df.dropna(subset=['frs']).groupby(lambda x: x.year)['frs'].idxmax()
                max_info = df.loc[max_dates[max_dates.notna()], ['frs']]
                max_info['最大日冻土深度出现日期'] = max_info.index.strftime('%m月%d日')
                max_info.index = max_info.index.year

                yearly_df = pd.concat([max_info], axis=1)
                yearly_df.insert(loc=0, column='年份', value=yearly_df.index)
                yearly_df.reset_index(drop=True, inplace=True)
                yearly_df.insert(loc=0, column='站名', value=station)
                yearly_df.columns = ['站名', '年份', '最大日冻土深度(cm)', '最大日冻土深度出现日期']
                yearly_records.extend(yearly_df.to_dict(orient='records'))

            basic_frs_yearly = yearly_records if len(yearly_records) != 0 else None

        else:
            max_dates = frs_day.dropna(subset=['frs']).groupby(lambda x: x.year)['frs'].idxmax()
            max_info = frs_day.loc[max_dates[max_dates.notna()], ['frs']]
            max_info['最大日冻土深度出现日期'] = max_info.index.strftime('%m月%d日')
            max_info.index = max_info.index.year

            basic_frs_yearly = pd.concat([max_info], axis=1)
            basic_frs_yearly.insert(loc=0, column='年份', value=basic_frs_yearly.index)
            basic_frs_yearly.reset_index(drop=True, inplace=True)
            basic_frs_yearly.columns = ['年份', '最大日冻土深度(cm)', '最大日冻土深度出现日期']
            basic_frs_yearly = basic_frs_yearly.to_dict(orient='records')

    except Exception as e:
        logging.exception(e)
        basic_frs_yearly = None

    finally:
        try:
            
            frs_month = compute_frs_month_from_day(frs_day)
            if 'Station_Name' in frs_month.columns:
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

                for station, dfm in frs_month.groupby('Station_Name'):
                    max_frs = dfm[['FRS_Depth_Max_Day', 'FRS_Depth_Max_ODay_C', 'Year', 'Mon']]

                    max_frs_accum = []

                    for i in range(1, 13):
                        month_i_max = max_frs[max_frs.index.month == i]
                        month_i_max = month_i_max[month_i_max['FRS_Depth_Max_Day'] == month_i_max['FRS_Depth_Max_Day'].max()]

                        if len(month_i_max) > 1:
                            frs_data = month_i_max.iloc[0, 0]
                            occur_day = str(month_i_max['FRS_Depth_Max_ODay_C'].apply(sample).sum()) + 'T'
                            occur_year = str(len(month_i_max)) + 'N'
                            occur_month = month_i_max.iloc[0, 3]
                            array = np.array([frs_data, occur_day, occur_year, occur_month]).reshape(1, -1)
                            max_df = pd.DataFrame(array, columns=['FRS_Depth_Max_Day', 'FRS_Depth_Max_ODay_C', 'Year', 'Mon'], index=[month_i_max.index[0]])
                        else:
                            max_df = month_i_max[['FRS_Depth_Max_Day', 'FRS_Depth_Max_ODay_C', 'Year', 'Mon']]

                        max_frs_accum.append(max_df)

                    max_frs_accum = pd.concat(max_frs_accum, axis=0, ignore_index=True)
                    max_frs_accum['FRS_Depth_Max_Day'] = max_frs_accum['FRS_Depth_Max_Day'].astype(float)
                    max_row = max_frs_accum[max_frs_accum['FRS_Depth_Max_Day'] == max_frs_accum['FRS_Depth_Max_Day'].max()].reset_index(drop=True)

                    if len(max_row) == 1:
                        frs_v = max_row.loc[0, 'FRS_Depth_Max_Day']
                        date_v = max_row['Mon'].map(str) + '-' + max_row['FRS_Depth_Max_ODay_C'].map(str)
                        year_v = max_row.loc[0, 'Year']
                        values_list_max = [frs_v, date_v.values[0], year_v]
                    else:
                        frs_v = max_row.loc[0, 'FRS_Depth_Max_Day']
                        date_v = str(len(max_row)) + 'T'
                        year_v = str(max_row['Year'].apply(sample).sum()) + 'N'
                        values_list_max = [frs_v, date_v, year_v]

                    max_frs_accum.drop('Mon', axis=1, inplace=True)
                    max_frs_accum = max_frs_accum.T
                    max_frs_accum.index = ['最大日冻土深度(cm)', '最大日冻土深度出现日期', '最大日冻土深度出现年份']
                    max_frs_accum['全年'] = values_list_max

                    basic_frs_accum_station = max_frs_accum
                    month_list = [str(i) + '月' for i in range(1, 13)]
                    month_list.append('年')
                    basic_frs_accum_station.columns = month_list
                    basic_frs_accum_station.reset_index(inplace=True)
                    basic_frs_accum_station.rename(columns={'index': '要素'}, inplace=True)
                    basic_frs_accum_station.insert(loc=0, column='站名', value=station)

                    accum_records.extend(basic_frs_accum_station.to_dict(orient='records'))

                basic_frs_accum = accum_records if len(accum_records) != 0 else None

            else:
                max_frs = frs_month[['FRS_Depth_Max_Day', 'FRS_Depth_Max_ODay_C', 'Year', 'Mon']]

                max_frs_accum = []

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
                    month_i_max = max_frs[max_frs.index.month == i]
                    month_i_max = month_i_max[month_i_max['FRS_Depth_Max_Day'] == month_i_max['FRS_Depth_Max_Day'].max()]

                    if len(month_i_max) > 1:
                        frs_data = month_i_max.iloc[0, 0]
                        occur_year = str(len(month_i_max)) + 'N'
                        occur_month = month_i_max.iloc[0, 3]
                        array = np.array([frs_data, occur_year, occur_month]).reshape(1, -1)
                        max_df = pd.DataFrame(array, columns=['FRS_Depth_Max_Day', 'Year', 'Mon'], index=[month_i_max.index[0]])
                    else:
                        max_df = month_i_max[['FRS_Depth_Max_Day', 'Year', 'Mon']]

                    max_frs_accum.append(max_df)

                max_frs_accum = pd.concat(max_frs_accum, axis=0, ignore_index=True)
                max_frs_accum['FRS_Depth_Max_Day'] = max_frs_accum['FRS_Depth_Max_Day'].astype(float)
                max_row = max_frs_accum[max_frs_accum['FRS_Depth_Max_Day'] == max_frs_accum['FRS_Depth_Max_Day'].max()].reset_index(drop=True)

                if len(max_row) == 1:
                    frs_v = max_row.loc[0, 'FRS_Depth_Max_Day']
                    date_v = max_row['Mon'].map(str) + '-' + max_row['FRS_Depth_Max_ODay_C'].map(str)
                    year_v = max_row.loc[0, 'Year']
                    values_list_max = [frs_v, date_v.values[0], year_v]
                else:
                    frs_v = max_row.loc[0, 'FRS_Depth_Max_Day']
                    date_v = str(len(max_row)) + 'T'
                    year_v = str(max_row['Year'].apply(sample).sum()) + 'N'
                    values_list_max = [frs_v, date_v, year_v]

                max_frs_accum.drop('Mon', axis=1, inplace=True)
                max_frs_accum = max_frs_accum.T
                max_frs_accum.index = ['最大日冻土深度(cm)', '最大日冻土深度出现日期', '最大日冻土深度出现年份']
                max_frs_accum['全年'] = values_list_max

                basic_frs_accum = max_frs_accum
                month_list = [str(i) + '月' for i in range(1, 13)]
                month_list.append('年')
                basic_frs_accum.columns = month_list
                basic_frs_accum.reset_index(inplace=True)
                basic_frs_accum.rename(columns={'index': '要素'}, inplace=True)

                tmp = basic_frs_accum.dropna(axis=1, how='all')
                if len(tmp.columns) <= 1:
                    basic_frs_accum = None
                else:
                    basic_frs_accum = basic_frs_accum.to_dict(orient='records')

        except Exception as e:
            logging.exception(e)
            basic_frs_accum = None

        finally:
            report_path = None
            return basic_frs_yearly, basic_frs_accum, report_path


if __name__ == '__main__':
    daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    monthly_df = pd.read_csv(cfg.FILES.QH_DATA_MONTH, low_memory=False)
    sta_ids = '52866,52713'
    years = '2000,2020'

    day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,FRS_1st_Bot,FRS_2nd_Bot').split(',')
    post_daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')

    frs_day = post_daily_df.copy()
    basic_frs_yearly, basic_frs_accum, report_path = key_frs_statistics(frs_day)
