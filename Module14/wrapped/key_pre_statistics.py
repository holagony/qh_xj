'''
关键因子-日降水量
'''
import logging
import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.get_local_data import get_local_data


def compute_pre_month_from_day(pre_day):
    df = pre_day.dropna(subset=['PRE_Time_2020']).copy()
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
        elif 'Datetime' in pre_day.columns:
            df['Datetime'] = pd.to_datetime(pre_day['Datetime'])
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
            max_val = dfg['PRE_Time_2020'].astype(float).max()
            max_rows = dfg[dfg['PRE_Time_2020'].astype(float) == max_val]
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
                'PRE_Max_Day': float(max_val),
                'PRE_Max_ODay_C': oday,
                'Year': year_v,
                'Mon': mon_v,
                'Datetime': dt
            }
            if 'Station_Id_C' in dfg.columns:
                rec['Station_Id_C'] = dfg['Station_Id_C'].iloc[0]
            records.append(rec)
    else:
        for (year_v, mon_v), dfg in df.groupby(['Year', 'Mon']):
            max_val = dfg['PRE_Time_2020'].astype(float).max()
            max_rows = dfg[dfg['PRE_Time_2020'].astype(float) == max_val]
            if len(max_rows) == 1:
                day_v = int(max_rows['Day'].iloc[0])
                dt = pd.Timestamp(int(year_v), int(mon_v), day_v)
                oday = day_v
            else:
                dt = pd.Timestamp(int(year_v), int(mon_v), 1)
                oday = str(len(max_rows)) + 'T'

            rec = {
                'PRE_Max_Day': float(max_val),
                'PRE_Max_ODay_C': oday,
                'Year': int(year_v),
                'Mon': int(mon_v),
                'Datetime': dt
            }
            records.append(rec)

    out = pd.DataFrame(records)
    out.set_index('Datetime', inplace=True)
    return out


def key_pre_statistics(pre_day, data_dir):
    try:
        if 'Station_Name' in pre_day.columns:
            yearly_records = []
            for station, df in pre_day.groupby('Station_Name'):
                max_dates = df.dropna(subset=['PRE_Time_2020']).groupby(lambda x: x.year)['PRE_Time_2020'].idxmax()
                max_info = df.loc[max_dates[max_dates.notna()], ['PRE_Time_2020']]
                max_info['最大日降水量出现日期'] = max_info.index.strftime('%m月%d日')
                max_info.index = max_info.index.year

                yearly_df = pd.concat([max_info], axis=1)
                yearly_df.insert(loc=0, column='年份', value=yearly_df.index)
                yearly_df.reset_index(drop=True, inplace=True)
                yearly_df.insert(loc=0, column='站名', value=station)
                yearly_df.columns = ['站名', '年份', '最大日降水量(mm)', '最大日降水量出现日期']
                yearly_records.extend(yearly_df.to_dict(orient='records'))

            basic_pre_yearly = yearly_records if len(yearly_records) != 0 else None

        else:
            max_dates = pre_day.dropna(subset=['PRE_Time_2020']).groupby(lambda x: x.year)['PRE_Time_2020'].idxmax()
            max_info = pre_day.loc[max_dates[max_dates.notna()], ['PRE_Time_2020']]
            max_info['最大日降水量出现日期'] = max_info.index.strftime('%m月%d日')
            max_info.index = max_info.index.year

            basic_pre_yearly = pd.concat([max_info], axis=1)
            basic_pre_yearly.insert(loc=0, column='年份', value=basic_pre_yearly.index)
            basic_pre_yearly.reset_index(drop=True, inplace=True)
            basic_pre_yearly.columns = ['年份', '最大日降水量(mm)', '最大日降水量出现日期']
            basic_pre_yearly = basic_pre_yearly.to_dict(orient='records')

    except Exception as e:
        logging.exception(e)
        basic_pre_yearly = None

    finally:
        try:
            
            pre_month = compute_pre_month_from_day(pre_day)
            if 'Station_Name' in pre_month.columns:
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

                for station, dfm in pre_month.groupby('Station_Name'):
                    max_pre = dfm[['PRE_Max_Day', 'PRE_Max_ODay_C', 'Year', 'Mon']]

                    max_pre_accum = []

                    for i in range(1, 13):
                        month_i_max = max_pre[max_pre.index.month == i]
                        month_i_max = month_i_max[month_i_max['PRE_Max_Day'] == month_i_max['PRE_Max_Day'].max()]

                        if len(month_i_max) > 1:
                            pre_data = month_i_max.iloc[0, 0]
                            occur_day = str(month_i_max['PRE_Max_ODay_C'].apply(sample).sum()) + 'T'
                            occur_year = str(len(month_i_max)) + 'N'
                            occur_month = month_i_max.iloc[0, 3]
                            array = np.array([pre_data, occur_day, occur_year, occur_month]).reshape(1, -1)
                            max_df = pd.DataFrame(array, columns=['PRE_Max_Day', 'PRE_Max_ODay_C', 'Year', 'Mon'], index=[month_i_max.index[0]])
                        else:
                            max_df = month_i_max[['PRE_Max_Day', 'PRE_Max_ODay_C', 'Year', 'Mon']]

                        max_pre_accum.append(max_df)

                    max_pre_accum = pd.concat(max_pre_accum, axis=0, ignore_index=True)
                    max_pre_accum['PRE_Max_Day'] = max_pre_accum['PRE_Max_Day'].astype(float)
                    max_row = max_pre_accum[max_pre_accum['PRE_Max_Day'] == max_pre_accum['PRE_Max_Day'].max()].reset_index(drop=True)

                    if len(max_row) == 1:
                        pre_v = max_row.loc[0, 'PRE_Max_Day']
                        date_v = max_row['Mon'].map(str) + '-' + max_row['PRE_Max_ODay_C'].map(str)
                        year_v = max_row.loc[0, 'Year']
                        values_list_max = [pre_v, date_v.values[0], year_v]
                    else:
                        pre_v = max_row.loc[0, 'PRE_Max_Day']
                        date_v = str(len(max_row)) + 'T'
                        year_v = str(max_row['Year'].apply(sample).sum()) + 'N'
                        values_list_max = [pre_v, date_v, year_v]

                    max_pre_accum.drop('Mon', axis=1, inplace=True)
                    max_pre_accum = max_pre_accum.T
                    max_pre_accum.index = ['最大日降水量(mm)', '最大日降水量出现日期', '最大日降水量出现年份']
                    max_pre_accum['全年'] = values_list_max

                    basic_pre_accum_station = max_pre_accum
                    month_list = [str(i) + '月' for i in range(1, 13)]
                    month_list.append('年')
                    basic_pre_accum_station.columns = month_list
                    basic_pre_accum_station.reset_index(inplace=True)
                    basic_pre_accum_station.rename(columns={'index': '要素'}, inplace=True)
                    basic_pre_accum_station.insert(loc=0, column='站名', value=station)

                    accum_records.extend(basic_pre_accum_station.to_dict(orient='records'))

                basic_pre_accum = accum_records if len(accum_records) != 0 else None

            else:
                max_pre = pre_month[['PRE_Max_Day', 'PRE_Max_ODay_C', 'Year', 'Mon']]

                max_pre_accum = []

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
                    month_i_max = max_pre[max_pre.index.month == i]
                    month_i_max = month_i_max[month_i_max['PRE_Max_Day'] == month_i_max['PRE_Max_Day'].max()]

                    if len(month_i_max) > 1:
                        pre_data = month_i_max.iloc[0, 0]
                        occur_year = str(len(month_i_max)) + 'N'
                        occur_month = month_i_max.iloc[0, 3]
                        array = np.array([pre_data, occur_year, occur_month]).reshape(1, -1)
                        max_df = pd.DataFrame(array, columns=['PRE_Max_Day', 'Year', 'Mon'], index=[month_i_max.index[0]])
                    else:
                        max_df = month_i_max[['PRE_Max_Day', 'Year', 'Mon']]

                    max_pre_accum.append(max_df)

                max_pre_accum = pd.concat(max_pre_accum, axis=0, ignore_index=True)
                max_pre_accum['PRE_Max_Day'] = max_pre_accum['PRE_Max_Day'].astype(float)
                max_row = max_pre_accum[max_pre_accum['PRE_Max_Day'] == max_pre_accum['PRE_Max_Day'].max()].reset_index(drop=True)

                if len(max_row) == 1:
                    pre_v = max_row.loc[0, 'PRE_Max_Day']
                    date_v = max_row['Mon'].map(str) + '-' + max_row['PRE_Max_ODay_C'].map(str)
                    year_v = max_row.loc[0, 'Year']
                    values_list_max = [pre_v, date_v.values[0], year_v]
                else:
                    pre_v = max_row.loc[0, 'PRE_Max_Day']
                    date_v = str(len(max_row)) + 'T'
                    year_v = str(max_row['Year'].apply(sample).sum()) + 'N'
                    values_list_max = [pre_v, date_v, year_v]

                max_pre_accum.drop('Mon', axis=1, inplace=True)
                max_pre_accum = max_pre_accum.T
                max_pre_accum.index = ['最大日降水量(mm)', '最大日降水量出现日期', '最大日降水量出现年份']
                max_pre_accum['全年'] = values_list_max

                basic_pre_accum = max_pre_accum
                month_list = [str(i) + '月' for i in range(1, 13)]
                month_list.append('年')
                basic_pre_accum.columns = month_list
                basic_pre_accum.reset_index(inplace=True)
                basic_pre_accum.rename(columns={'index': '要素'}, inplace=True)

                tmp = basic_pre_accum.dropna(axis=1, how='all')
                if len(tmp.columns) <= 1:
                    basic_pre_accum = None
                else:
                    basic_pre_accum = basic_pre_accum.to_dict(orient='records')

        except Exception as e:
            logging.exception(e)
            basic_pre_accum = None

        finally:
            report_path = None
            return basic_pre_yearly, basic_pre_accum, report_path


if __name__ == '__main__':
    daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    monthly_df = pd.read_csv(cfg.FILES.QH_DATA_MONTH, low_memory=False)
    sta_ids = '52866,52713'
    years = '2000,2020'

    day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + 'PRE_Time_2020').split(',')
    post_daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')

    pre_day = post_daily_df.copy()
    basic_pre_yearly, basic_pre_accum, report_path = key_pre_statistics(pre_day)
