import logging
import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.data_processing import yearly_data_processing, monthly_data_processing
from Report.code.Module02.gst import gst_report


def basic_gst_statistics(gst_day, gst_month, data_dir):
    '''
    地面温度要素，历年和累年各月统计，
    使用天擎上的年数据和月数据，要素名称为天擎上默认的名称
    年值要素：['Station_Id_C', 'Station_Name', 'Year', 'GST_Avg', 'EGST_Max_Avg_Mon',
              'GST_Min_Avg', 'GST_Max', 'V12311_067', 'GST_Min', 'V12121_067']
    月值要素：['Station_Id_C', 'Station_Name', 'Year', 'Mon', 'GST_Avg', 'EGST_Max_Avg_Mon', 
              'GST_Min_Avg', 'GST_Max', 'EGST_Max_ODay_C', 'GST_Min', 'GST_Min_Ten_ODay_C']
    return: dataframe
    '''
    try:
        # 计算年度统计数据
        yearly_avg_gst = gst_day['GST_Avg'].resample('1A').mean().round(1)
        yearly_avg_gst.index = yearly_avg_gst.index.year

        monthly_max_gst = gst_day['GST_Max'].resample('1A').mean().round(1)
        monthly_max_gst.index = monthly_max_gst.index.year

        monthly_min_gst = gst_day['GST_Min'].resample('1A').mean().round(1)
        monthly_min_gst.index = monthly_min_gst.index.year

        # 计算极端温度及其出现日期
        extreme_max_dates = gst_day.dropna(subset=['GST_Max']).groupby(lambda x: x.year)['GST_Max'].idxmax()
        extreme_max_info = gst_day.loc[extreme_max_dates[extreme_max_dates.notna()], ['GST_Max']]
        extreme_max_info['极端最高地面温度出现日期'] = extreme_max_info.index.strftime('%m月%d日')
        extreme_max_info.index = extreme_max_info.index.year

        extreme_min_dates = gst_day.dropna(subset=['GST_Min']).groupby(lambda x: x.year)['GST_Min'].idxmin()
        extreme_min_info = gst_day.loc[extreme_min_dates[extreme_min_dates.notna()], ['GST_Min']]
        extreme_min_info['极端最低地面温度出现日期'] = extreme_min_info.index.strftime('%m月%d日')
        extreme_min_info.index = extreme_min_info.index.year

        basic_gst_yearly = pd.concat([yearly_avg_gst,monthly_max_gst,monthly_min_gst,extreme_max_info,extreme_min_info],axis=1)
        basic_gst_yearly.insert(loc=0, column='年份', value=basic_gst_yearly.index)
        basic_gst_yearly.columns = ['年份', '平均地面温度(℃)', '平均最高地面温度(℃)', '平均最低地面温度(℃)', '极端最高地面温度(℃)', '极端最高地面温度出现日期', '极端最低地面温度(℃)', '极端最低地面温度出现日期']
        basic_gst_yearly.reset_index(drop=True, inplace=True)

        tmp = basic_gst_yearly.dropna(axis=1, how='all')
        if len(tmp.columns) == 1:  # 如果只有年份一列，说明全部没有数据
            basic_gst_yearly = None
        else:
            basic_gst_yearly = basic_gst_yearly.round(1).to_dict(orient='records')

    except Exception as e:
        logging.exception(e)
        basic_gst_yearly = None

    finally:
        try:
            # B.累年各月统计
            gst_mean = gst_month[['GST_Avg', 'EGST_Max_Avg_Mon', 'GST_Min_Avg']]
            gst_max = gst_month[['GST_Max', 'EGST_Max_ODay_C', 'Year', 'Mon']]
            gst_min = gst_month[['GST_Min', 'GST_Min_Ten_ODay_C', 'Year', 'Mon']]

            mean_gst_accum = []
            max_gst_accum = []
            min_gst_accum = []

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
                month_i_mean = gst_mean[gst_mean.index.month == i].mean().round(1).to_frame()
                mean_gst_accum.append(month_i_mean)

                # max
                month_i_max = gst_max[gst_max.index.month == i]
                month_i_max = month_i_max[month_i_max['GST_Max'] == month_i_max['GST_Max'].max()]

                # 针对多个时间点数值相同的情况
                if len(month_i_max) > 1:
                    gst_data = month_i_max.iloc[0, 0]  # columns: ['GST_Max','EGST_Max_ODay_C','Year','Mon']
                    occur_day = str(month_i_max['EGST_Max_ODay_C'].apply(sample).sum()) + 'T'
                    occur_year = str(len(month_i_max)) + 'N'
                    occur_month = month_i_max.iloc[0, 3]

                    array = np.array([gst_data, occur_day, occur_year, occur_month]).reshape(1, -1)
                    max_df = pd.DataFrame(array, columns=month_i_max.columns, index=[month_i_max.index[0]])

                else:
                    max_df = month_i_max

                max_gst_accum.append(max_df)

                # min
                month_i_min = gst_min[gst_min.index.month == i]
                month_i_min = month_i_min[month_i_min['GST_Min'] == month_i_min['GST_Min'].min()]

                # 针对多个时间点数值相同的情况
                if len(month_i_min) > 1:
                    gst_data = month_i_min.iloc[0, 0]  # columns: ['GST_Min','GST_Min_Ten_ODay_C','Year','Mon']
                    occur_day = str(month_i_min['GST_Min_Ten_ODay_C'].apply(sample).sum()) + 'T'
                    occur_year = str(len(month_i_min)) + 'N'
                    occur_month = month_i_min.iloc[0, 3]

                    array = np.array([gst_data, occur_day, occur_year, occur_month]).reshape(1, -1)
                    min_df = pd.DataFrame(array, columns=month_i_min.columns, index=[month_i_min.index[0]])

                else:
                    min_df = month_i_min

                min_gst_accum.append(min_df)

            ####################################################
            # 结果合成为DateFrame
            # mean
            mean_gst_accum = pd.concat(mean_gst_accum, axis=1, ignore_index=True)
            mean_gst_accum.index = ['平均地面温度(℃)', '平均最高地面温度(℃)', '平均最低地面温度(℃)']
            mean_gst_accum['全年'] = mean_gst_accum.iloc[:, :].mean(axis=1).round(1)

            # max
            max_gst_accum = pd.concat(max_gst_accum, axis=0, ignore_index=True)
            max_gst_accum['GST_Max'] = max_gst_accum['GST_Max'].astype(float)
            max_row = max_gst_accum[max_gst_accum['GST_Max'] == max_gst_accum['GST_Max'].max()].reset_index(drop=True)

            if len(max_row) == 1:
                gst = max_row.loc[0, 'GST_Max']
                date = max_row['Mon'].map(str) + '-' + max_row['EGST_Max_ODay_C'].map(str)
                year = max_row.loc[0, 'Year']
                values_list = [gst, date.values[0], year]

            elif len(max_row) > 1:
                gst = max_row.loc[0, 'GST_Max']
                date = str(len(max_row)) + 'T'
                year = str(max_row['Year'].apply(sample).sum()) + 'N'
                values_list = [gst, date, year]

            max_gst_accum.drop('Mon', axis=1, inplace=True)  # 删除月份列
            max_gst_accum = max_gst_accum.T
            max_gst_accum.index = ['极端最高地面温度(℃)', '极端最高地面温度出现日期', '极端最高地面温度出现年份']
            max_gst_accum['全年'] = values_list

            # min
            min_gst_accum = pd.concat(min_gst_accum, axis=0, ignore_index=True)
            min_gst_accum['GST_Min'] = min_gst_accum['GST_Min'].astype(float)
            min_row = min_gst_accum[min_gst_accum['GST_Min'] == min_gst_accum['GST_Min'].min()].reset_index(drop=True)

            if len(min_row) == 1:
                gst = min_row.loc[0, 'GST_Min']
                date = min_row['Mon'].map(str) + '-' + min_row['GST_Min_Ten_ODay_C'].map(str)
                year = min_row.loc[0, 'Year']
                values_list = [gst, date.values[0], year]

            elif len(min_row) > 1:
                gst = min_row.loc[0, 'GST_Min']
                date = str(len(min_row)) + 'T'
                year = str(min_row['Year'].apply(sample).sum()) + 'N'
                values_list = [gst, date, year]

            min_gst_accum.drop('Mon', axis=1, inplace=True)  # 删除月份列
            min_gst_accum = min_gst_accum.T
            min_gst_accum.index = ['极端最低地面温度(℃)', '极端最低地面温度出现日期', '极端最低地面温度出现年份']
            min_gst_accum['全年'] = values_list

            # 计算结果concat在一起
            basic_gst_accum = pd.concat([mean_gst_accum, max_gst_accum, min_gst_accum], axis=0)

            # 增加月份
            month_list = [str(i) + '月' for i in range(1, 13)]
            month_list.append('年')
            basic_gst_accum.columns = month_list
            basic_gst_accum.reset_index(inplace=True)
            basic_gst_accum.rename(columns={'index': '要素'}, inplace=True)

            tmp = basic_gst_accum.dropna(axis=1, how='all')
            if len(tmp.columns) == 1:
                basic_gst_accum = None
            else:
                basic_gst_accum = basic_gst_accum.to_dict(orient='records')

        except Exception as e:
            logging.exception(e)
            basic_gst_accum = None

        finally:
            try:
                report_path = gst_report(basic_gst_yearly, basic_gst_accum, gst_month, data_dir)
            except:
                report_path = None

            return basic_gst_yearly, basic_gst_accum, report_path


if __name__ == '__main__':
    yearly_df = pd.read_csv(cfg.FILES.QH_DATA_YEAR)
    monthly_df = pd.read_csv(cfg.FILES.QH_DATA_MONTH)
    post_yearly_df = yearly_data_processing(yearly_df, '2000', '2020')
    post_monthly_df = monthly_data_processing(monthly_df, '2000', '2020')
    post_yearly_df = post_yearly_df[post_yearly_df['Station_Id_C']=='52866']
    post_monthly_df = post_monthly_df[post_monthly_df['Station_Id_C']=='52866']
    data_dir = r'C:/Users/MJY/Desktop'
    basic_gst_yearly, basic_gst_accum, report_path = basic_gst_statistics(post_yearly_df, post_monthly_df,data_dir)
