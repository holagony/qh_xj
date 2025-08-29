import logging
import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.get_local_data import get_local_data
from Report.code.Module02.snow import snow_report


def basic_snow_statistics(snow_day, snow_month, data_dir):
    '''
    积雪深度要素，历年和累年各月统计，
    使用天擎上的年数据和月数据，要素名称为天擎上默认的名称
    年值要素：['Station_Id_C', 'Station_Name', 'Year', 'Snow_Depth_Max', 'V13334_067']
    月值要素：['Station_Id_C', 'Station_Name', 'Year', 'Mon', 'Snow_Depth_Max', 'V13334_060_C']
    return: dataframe
    '''
    try:
        # A.历年统计 天擎年值序列直接输出
        avg_snow_info = snow_day['Snow_Depth'].resample('1A').max().round(1).to_frame()
        avg_snow_info.index = avg_snow_info.index.year
        
        snow_dates = snow_day.dropna(subset=['Snow_Depth']).groupby(lambda x: x.year)['Snow_Depth'].idxmax()
        snow_max_day = snow_day.loc[snow_dates[snow_dates.notna()], ['Snow_Depth']]
        snow_max_day['最大雪深出现日期'] = snow_max_day.index.strftime('%m月%d日')
        snow_max_day.index = snow_max_day.index.year
        snow_max_day = snow_max_day['最大雪深出现日期'].to_frame()
        
        basic_snow_yearly = pd.concat([avg_snow_info,snow_max_day],axis=1)
        basic_snow_yearly.insert(loc=0, column='年份', value=basic_snow_yearly.index)
        basic_snow_yearly.reset_index(drop=True, inplace=True)
        basic_snow_yearly.columns = ['年份', '最大雪深(cm)', '最大雪深出现日期']

        tmp = basic_snow_yearly.dropna(axis=1, how='all')
        if len(tmp.columns) == 1:  # 如果只有年份一列，说明全部没有数据
            basic_snow_yearly = None
        else:
            basic_snow_yearly = basic_snow_yearly.round(1).to_dict(orient='records')

    except Exception as e:
        logging.exception(e)
        basic_snow_yearly = None

    finally:
        try:
            # B.累年各月统计
            snow = snow_month['Snow_Depth_Max'].to_frame()
            snow_max = snow_month[['Snow_Depth_Max', 'V13334_060_C', 'Year', 'Mon']]

            mean_snow_accum = []
            max_snow_accum = []

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
                month_i_mean = snow[snow.index.month == i].mean().round(1).to_frame()
                mean_snow_accum.append(month_i_mean)

                # min
                month_i_max = snow_max[snow_max.index.month == i]
                month_i_max = month_i_max[month_i_max['Snow_Depth_Max'] == month_i_max['Snow_Depth_Max'].max()]

                # 针对多个时间点数值相同的情况
                if len(month_i_max) > 1:
                    snow_data = month_i_max.iloc[0, 0]  # columns: ['Snow_Depth_Max','V13334_060_C','Year','Mon']
                    occur_day = str(month_i_max['V13334_060_C'].apply(sample).sum()) + 'T'
                    occur_year = str(len(month_i_max)) + 'N'
                    occur_month = month_i_max.iloc[0, 3]

                    array = np.array([snow_data, occur_day, occur_year, occur_month]).reshape(1, -1)
                    max_df = pd.DataFrame(array, columns=month_i_max.columns, index=[month_i_max.index[0]])

                else:
                    max_df = month_i_max

                max_snow_accum.append(max_df)

            ####################################################
            # 结果合成为DateFrame
            # mean
            mean_snow_accum = pd.concat(mean_snow_accum, axis=1, ignore_index=True)
            mean_snow_accum.index = ['平均最大雪深(cm)']
            mean_snow_accum['全年'] = mean_snow_accum.iloc[:, :].mean(axis=1).round(1)

            # max
            max_snow_accum = pd.concat(max_snow_accum, axis=0, ignore_index=True)

            if len(max_snow_accum) == 0:  # 没有数据的情况
                index = ['最大雪深(cm)', '最大雪深出现日期', '最大雪深出现年份']
                columns = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, '全年']
                max_snow_accum = pd.DataFrame(columns=columns, index=index)

            else:
                max_snow_accum['Snow_Depth_Max'] = max_snow_accum['Snow_Depth_Max'].astype(float)
                max_row = max_snow_accum[max_snow_accum['Snow_Depth_Max'] == max_snow_accum['Snow_Depth_Max'].max()].reset_index(drop=True)

                if len(max_row) == 1:
                    snow = max_row.loc[0, 'Snow_Depth_Max']
                    date = max_row['Mon'].map(str) + '-' + max_row['V13334_060_C'].map(str)
                    year = max_row.loc[0, 'Year']
                    values_list = [snow, date.values[0], year]

                elif len(max_row) > 1:
                    rh = max_row.loc[0, 'Snow_Depth_Max']
                    date = str(len(max_row)) + 'T'
                    year = str(max_row['Year'].apply(sample).sum()) + 'N'
                    values_list = [rh, date, year]

                max_snow_accum.drop('Mon', axis=1, inplace=True)  # 删除月份列
                max_snow_accum = max_snow_accum.T
                max_snow_accum.index = ['最大雪深(cm)', '最大雪深出现日期', '最大雪深出现年份']
                max_snow_accum['全年'] = values_list

            # 计算结果concat在一起
            basic_snow_accum = pd.concat([mean_snow_accum, max_snow_accum], axis=0)

            # 增加月份
            month_list = [str(i) + '月' for i in range(1, 13)]
            month_list.append('年')
            basic_snow_accum.columns = month_list
            basic_snow_accum.reset_index(inplace=True)
            basic_snow_accum.rename(columns={'index': '要素'}, inplace=True)

            tmp = basic_snow_accum.dropna(axis=1, how='all')
            if len(tmp.columns) == 1:
                basic_snow_accum = None
            else:
                basic_snow_accum = basic_snow_accum.copy()
                basic_snow_accum.iloc[:, 6:10] = np.nan
                basic_snow_accum = basic_snow_accum.to_dict(orient='records')

        except Exception as e:
            logging.exception(e)
            basic_snow_accum = None

        finally:
            try:
                report_path = snow_report(basic_snow_yearly, basic_snow_accum, snow_month, data_dir)
            except:
                report_path = None

            return basic_snow_yearly, basic_snow_accum, report_path


if __name__ == '__main__':
    daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    monthly_df = pd.read_csv(cfg.FILES.QH_DATA_MONTH, low_memory=False)
    sta_ids = '52866'
    years = '1980,2020'

    day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day').split(',')
    post_daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')
    post_daily_df.loc[3650:, 'Snow_Depth'] = 20
    
    monthly_elements = 'Snow_Depth_Max,V13334_060_C,'
    month_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,' + monthly_elements[:-1]).split(',')
    post_monthly_df = get_local_data(monthly_df, sta_ids, month_eles, years, 'Month')
    
    data_dir = r'C:/Users/mjynj/Desktop'

    basic_snow_yearly, basic_snow_accum, report_path = basic_snow_statistics(post_daily_df, post_monthly_df,data_dir)
