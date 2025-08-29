import logging
import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.get_local_data import get_local_data
from Report.code.Module02.tem import tem_report


def basic_tem_statistics(tem_day, tem_month, data_dir):
    '''
    温度要素，历年和累年各月统计，
    使用天擎上的年数据和月数据，要素名称为天擎上默认的名称
    年值要素：['Station_Id_C', 'Station_Name', 'Year', 'TEM_Avg', 'TEM_Max_Avg',
              'TEM_Min_Avg', 'TEM_Max', 'V12011_067', 'TEM_Min', 'V12012_067']
    月值要素：['Station_Id_C', 'Station_Name', 'Year', 'Mon', 'TEM_Avg', 'TEM_Max','TEM_Min', 
              'TEM_Max_Avg', 'TEM_Min_Avg', 'TEM_Max_ODay_C', 'TEM_Min_ODay_C']
    return: dataframe
    '''
    try:
        max_tem_dates = tem_day.dropna(subset=['TEM_Max']).groupby(lambda x: x.year)['TEM_Max'].idxmax()
        max_tem_info = tem_day.loc[max_tem_dates[max_tem_dates.notna()], ['TEM_Max']]
        max_tem_info['最高气温出现日期'] = max_tem_info.index.strftime('%m月%d日')
        max_tem_info.index = max_tem_info.index.year
        
        min_tem_dates = tem_day.dropna(subset=['TEM_Min']).groupby(lambda x: x.year)['TEM_Min'].idxmin()
        min_tem_info = tem_day.loc[min_tem_dates[min_tem_dates.notna()], ['TEM_Min']]
        min_tem_info['最低气温出现日期'] = min_tem_info.index.strftime('%m月%d日')
        min_tem_info.index = min_tem_info.index.year
        
        avg_tem_info = tem_day['TEM_Avg'].resample('1A').mean().round(1).to_frame()
        avg_tem_info.index = avg_tem_info.index.year
        
        basic_tem_yearly = pd.concat([avg_tem_info,max_tem_info,min_tem_info], axis=1)
        basic_tem_yearly.insert(loc=0, column='年份', value=basic_tem_yearly.index)
        basic_tem_yearly.reset_index(drop=True, inplace=True)
        basic_tem_yearly.columns = ['年份', '平均气温(°C)', '最高气温(°C)', '最高气温出现日期', '最低气温(°C)', '最低气温出现日期']
        basic_tem_yearly = basic_tem_yearly.to_dict(orient='records')

    except Exception as e:
        logging.exception(e)
        basic_tem_yearly = None

    finally:
        try:
            # B.累年各月统计
            tem = tem_month[['TEM_Avg', 'TEM_Max_Avg', 'TEM_Min_Avg']]
            tem_max = tem_month[['TEM_Max', 'TEM_Max_ODay_C', 'Year', 'Mon']]
            tem_min = tem_month[['TEM_Min', 'TEM_Min_ODay_C', 'Year', 'Mon']]

            mean_tem_accum = []
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
                # mean
                month_i_mean = tem[tem.index.month == i].mean().round(1).to_frame()
                mean_tem_accum.append(month_i_mean)

                # max
                month_i_max = tem_max[tem_max.index.month == i]
                month_i_max = month_i_max[month_i_max['TEM_Max'] == month_i_max['TEM_Max'].max()]

                # 针对多个时间点数值相同的情况
                if len(month_i_max) > 1:
                    tem_data = month_i_max.iloc[0, 0]  # columns: ['TEM_Max', 'TEM_Max_ODay_C', 'Year', 'Mon']
                    occur_day = str(month_i_max['TEM_Max_ODay_C'].apply(sample).sum()) + 'T'
                    occur_year = str(len(month_i_max)) + 'N'
                    occur_month = month_i_max.iloc[0, 3]

                    array = np.array([tem_data, occur_day, occur_year, occur_month]).reshape(1, -1)
                    max_df = pd.DataFrame(array, columns=month_i_max.columns, index=[month_i_max.index[0]])

                else:
                    max_df = month_i_max

                max_tem_accum.append(max_df)

                # min
                month_i_min = tem_min[tem_min.index.month == i]
                month_i_min = month_i_min[month_i_min['TEM_Min'] == month_i_min['TEM_Min'].min()]

                # 针对多个时间点数值相同的情况
                if len(month_i_min) > 1:
                    tem_data = month_i_min.iloc[0, 0]
                    occur_day = str(month_i_min['TEM_Min_ODay_C'].apply(sample).sum()) + 'T'
                    occur_year = str(len(month_i_min)) + 'N'
                    occur_month = month_i_max.iloc[0, 3]

                    array = np.array([tem_data, occur_day, occur_year, occur_month]).reshape(1, -1)
                    min_df = pd.DataFrame(array, columns=month_i_min.columns, index=[month_i_min.index[0]])

                else:
                    min_df = month_i_min

                min_tem_accum.append(min_df)

            # 结果合成为DateFrame
            # mean
            mean_tem_accum = pd.concat(mean_tem_accum, axis=1, ignore_index=True)
            mean_tem_accum.index = ['平均气温(°C)', '平均最高气温(°C)', '平均最低气温(°C)']
            mean_tem_accum['全年'] = mean_tem_accum.iloc[:, :].mean(axis=1).round(1)

            # max
            max_tem_accum = pd.concat(max_tem_accum, axis=0, ignore_index=True)
            max_tem_accum['TEM_Max'] = max_tem_accum['TEM_Max'].astype(float)
            max_row = max_tem_accum[max_tem_accum['TEM_Max'] == max_tem_accum['TEM_Max'].max()].reset_index(drop=True)

            if len(max_row) == 1:
                tem = max_row.loc[0, 'TEM_Max']
                date = max_row['Mon'].map(str) + '-' + max_row['TEM_Max_ODay_C'].map(str)
                year = max_row.loc[0, 'Year']  # 气压最大值对应的年份
                values_list = [tem, date.values[0], year]

            elif len(max_row) > 1:
                tem = max_row.loc[0, 'TEM_Max']
                date = str(len(max_row)) + 'T'
                year = str(max_row['Year'].apply(sample).sum()) + 'N'
                values_list = [tem, date, year]

            max_tem_accum.drop('Mon', axis=1, inplace=True)  # 删除月份列
            max_tem_accum = max_tem_accum.T
            max_tem_accum.index = ['极端最高气温(°C)', '极端最高气温出现日期', '极端最高气温出现年份']
            max_tem_accum['全年'] = values_list

            # min
            min_tem_accum = pd.concat(min_tem_accum, axis=0, ignore_index=True)
            min_tem_accum['TEM_Min'] = min_tem_accum['TEM_Min'].astype(float)
            min_row = min_tem_accum[min_tem_accum['TEM_Min'] == min_tem_accum['TEM_Min'].min()].reset_index(drop=True)

            if len(min_row) == 1:
                tem = min_row.loc[0, 'TEM_Min']
                date = min_row['Mon'].map(str) + '-' + min_row['TEM_Min_ODay_C'].map(str)
                year = min_row.loc[0, 'Year']  # 气压最大值对应的年份
                values_list = [tem, date.values[0], year]

            elif len(min_row) > 1:
                tem = min_row.loc[0, 'TEM_Min']
                date = str(len(min_row)) + 'T'
                year = str(min_row['Year'].apply(sample).sum()) + 'N'
                values_list = [tem, date, year]

            min_tem_accum.drop('Mon', axis=1, inplace=True)  # 删除月份列
            min_tem_accum = min_tem_accum.T
            min_tem_accum.index = ['极端最低气温(°C)', '极端最低气温出现日期', '极端最低气温出现年份']
            min_tem_accum['全年'] = values_list

            # 计算结果concat在一起
            basic_tem_accum = pd.concat([mean_tem_accum, max_tem_accum, min_tem_accum], axis=0)

            # 增加月份
            month_list = [str(i) + '月' for i in range(1, 13)]
            month_list.append('年')
            basic_tem_accum.columns = month_list
            basic_tem_accum.reset_index(inplace=True)
            basic_tem_accum.rename(columns={'index': '要素'}, inplace=True)

            tmp = basic_tem_accum.dropna(axis=1, how='all')
            if len(tmp.columns) == 1:  # 如果只有年份一列，说明全部没有数据
                basic_tem_accum = None
            else:
                basic_tem_accum = basic_tem_accum.to_dict(orient='records')

        except Exception as e:
            logging.exception(e)
            basic_tem_accum = None

        finally:
            try:
                report_path = tem_report(basic_tem_yearly, basic_tem_accum, tem_month, data_dir)
            except:
                report_path = None
                
            return basic_tem_yearly, basic_tem_accum, report_path


if __name__ == '__main__':
    daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    monthly_df = pd.read_csv(cfg.FILES.QH_DATA_MONTH, low_memory=False)
    sta_ids = '52866'
    years = '2000,2020'

    daily_elements = 'TEM_Avg,TEM_Max,TEM_Min,'
    day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements[:-1]).split(',')
    post_daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')
    
    monthly_elements = 'TEM_Avg,TEM_Max,TEM_Min,TEM_Max_Avg,TEM_Min_Avg,TEM_Max_ODay_C,TEM_Min_ODay_C,'
    month_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,' + monthly_elements[:-1]).split(',')
    post_monthly_df = get_local_data(monthly_df, sta_ids, month_eles, years, 'Month')
    
    data_dir = r'C:/Users/mjynj/Desktop'
    basic_tem_yearly, basic_tem_accum, report_path = basic_tem_statistics(post_daily_df, post_monthly_df, data_dir)