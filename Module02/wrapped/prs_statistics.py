import logging
import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.get_local_data import get_local_data
from Report.code.Module02.prs import prs_report


def basic_prs_statistics(prs_day, prs_month, data_dir):
    '''
    气压要素，历年和累年各月统计，
    使用天擎上的年数据和月数据，要素名称为天擎上默认的名称
    年值要素：['Station_Id_C', 'Station_Name', 'Year', 'PRS_Avg', 'PRS_Max', 'PRS_Max_Odate', 'PRS_Min', 'PRS_Min_Odate']
    月值要素：['Station_Id_C', 'Station_Name', 'Year', 'Mon', 'PRS_Max', 'PRS_Min', 'PRS_Max_ODay_C', 'PRS_Min_ODay_C']
    日值要素：['PRS_Avg', 'PRS_Max', 'PRS_Min']
    return: dataframe
    '''
    try:
        # 处理最高气压
        max_prs_dates = prs_day.dropna(subset=['PRS_Max']).groupby(lambda x: x.year)['PRS_Max'].idxmax()
        max_prs_info = prs_day.loc[max_prs_dates[max_prs_dates.notna()], ['PRS_Max']]
        max_prs_info['最高气压出现日期'] = max_prs_info.index.strftime('%m月%d日')
        max_prs_info.index = max_prs_info.index.year

        # 处理最低气压
        min_prs_dates = prs_day.dropna(subset=['PRS_Min']).groupby(lambda x: x.year)['PRS_Min'].idxmin()
        min_prs_info = prs_day.loc[min_prs_dates[min_prs_dates.notna()], ['PRS_Min']]
        min_prs_info['最低气压出现日期'] = min_prs_info.index.strftime('%m月%d日')
        min_prs_info.index = min_prs_info.index.year

        # 处理平均气压
        avg_prs_info = prs_day['PRS_Avg'].resample('1A').mean().round(1).to_frame()
        avg_prs_info.index = avg_prs_info.index.year

        basic_prs_yearly = pd.concat([avg_prs_info,max_prs_info,min_prs_info], axis=1)
        basic_prs_yearly.insert(loc=0, column='年份', value=basic_prs_yearly.index)
        basic_prs_yearly.reset_index(drop=True, inplace=True)
        basic_prs_yearly.columns = ['年份', '平均气压(hPa)', '最高气压(hPa)', '最高气压出现日期', '最低气压(hPa)', '最低气压出现日期']
        basic_prs_yearly = basic_prs_yearly.to_dict(orient='records')

    except Exception as e:
        logging.exception(e)
        basic_prs_yearly = None
        # raise Exception('选取的气压要素整时间段缺失，无法计算气压历年统计')

    finally:
        try:
            # B.累年各月统计
            # prs = prs_day[['PRS_Avg', 'PRS_Max', 'PRS_Min']] # 气压日值
            # prs = prs.resample('1M', closed='right', label='right').mean() # 气压月平均
            prs = prs_month[['PRS_Avg', 'PRS_Max', 'PRS_Min']]
            prs_max = prs_month[['PRS_Max', 'PRS_Max_ODay_C', 'Year', 'Mon']]
            prs_min = prs_month[['PRS_Min', 'PRS_Min_ODay_C', 'Year', 'Mon']]

            mean_prs_accum = []
            max_prs_accum = []
            min_prs_accum = []

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
                month_i_mean = prs[prs.index.month == i].mean().round(1).to_frame()
                mean_prs_accum.append(month_i_mean)

                # max
                month_i_max = prs_max[prs_max.index.month == i]
                # 找到PRS_Max最大所对应的行
                month_i_max = month_i_max[month_i_max['PRS_Max'] == month_i_max['PRS_Max'].max()]

                # 针对多个时间点数值相同的情况
                if len(month_i_max) > 1:
                    # columns: ['PRS_Max', 'PRS_Max_ODay_C', 'Year', 'Mon']
                    prs_data = month_i_max.iloc[0, 0]
                    occur_day = (str(month_i_max['PRS_Max_ODay_C'].apply(sample).sum()) + 'T')
                    occur_year = str(len(month_i_max)) + 'N'
                    occur_month = month_i_max.iloc[0, 3]

                    array = np.array([prs_data, occur_day, occur_year, occur_month]).reshape(1, -1)
                    max_df = pd.DataFrame(array, columns=month_i_max.columns, index=[month_i_max.index[0]])

                else:
                    max_df = month_i_max

                max_prs_accum.append(max_df)

                # min
                month_i_min = prs_min[prs_min.index.month == i]
                # 找到PRS_Min最小所对应的行
                month_i_min = month_i_min[month_i_min['PRS_Min'] == month_i_min['PRS_Min'].min()]

                # 针对多个时间点数值相同的情况
                if len(month_i_min) > 1:
                    prs_data = month_i_min.iloc[0, 0]
                    occur_day = (str(month_i_min['PRS_Min_ODay_C'].apply(sample).sum()) + 'T')
                    occur_year = str(len(month_i_min)) + 'N'
                    occur_month = month_i_min.iloc[0, 3]

                    array = np.array([prs_data, occur_day, occur_year, occur_month]).reshape(1, -1)
                    min_df = pd.DataFrame(array, columns=month_i_min.columns, index=[month_i_min.index[0]])

                else:
                    min_df = month_i_min

                min_prs_accum.append(min_df)

            # 结果合成为DateFrame
            # mean
            mean_prs_accum = pd.concat(mean_prs_accum, axis=1, ignore_index=True)
            mean_prs_accum.index = ['平均气压(hPa)', '平均最高气压(hPa)', '平均最低气压(hPa)']
            mean_prs_accum['全年'] = mean_prs_accum.iloc[:, :].mean(axis=1).round(1)

            # max
            max_prs_accum = pd.concat(max_prs_accum, axis=0, ignore_index=True)
            max_prs_accum['PRS_Max'] = max_prs_accum['PRS_Max'].astype(float)
            max_row = max_prs_accum[max_prs_accum['PRS_Max'] == max_prs_accum['PRS_Max'].max()].reset_index(drop=True)  # 在max_prs_accum里面，气压最大值所对应的行，也可能存在多行的情况

            if len(max_row) == 1:
                prs = max_row.loc[0, 'PRS_Max']
                date = (max_row['Mon'].map(str) + '-' + max_row['PRS_Max_ODay_C'].map(str))  # 气压最大值对应的月-日
                year = max_row.loc[0, 'Year']  # 气压最大值对应的年份
                values_list = [prs, date.values[0], year]

            elif len(max_row) > 1:
                prs = max_row.loc[0, 'PRS_Max']
                date = str(len(max_row)) + 'T'
                year = str(max_row['Year'].apply(sample).sum()) + 'N'
                values_list = [prs, date, year]

            max_prs_accum.drop('Mon', axis=1, inplace=True)  # 删除月份列
            max_prs_accum = max_prs_accum.T
            max_prs_accum.index = ['极端最高气压(hPa)', '极端最高气压出现日期', '极端最高气压出现年份']
            max_prs_accum['全年'] = values_list

            # min
            min_prs_accum = pd.concat(min_prs_accum, axis=0, ignore_index=True)
            min_prs_accum['PRS_Min'] = min_prs_accum['PRS_Min'].astype(float)
            min_row = min_prs_accum[min_prs_accum['PRS_Min'] == min_prs_accum['PRS_Min'].min()].reset_index(drop=True)

            if len(min_row) == 1:
                prs = min_row.loc[0, 'PRS_Min']
                date = (min_row['Mon'].map(str) + '-' + min_row['PRS_Min_ODay_C'].map(str))  # 气压最大值对应的月-日
                year = min_row.loc[0, 'Year']  # 气压最大值对应的年份
                values_list = [prs, date.values[0], year]

            elif len(min_row) > 1:
                prs = min_row.loc[0, 'PRS_Min']
                date = str(len(min_row)) + 'T'
                year = str(min_row['Year'].apply(sample).sum()) + 'N'
                values_list = [prs, date, year]

            min_prs_accum.drop('Mon', axis=1, inplace=True)  # 删除月份列
            min_prs_accum = min_prs_accum.T
            min_prs_accum.index = ['极端最低气压(hPa)', '极端最低气压出现日期', '极端最低气压出现年份']
            min_prs_accum['全年'] = values_list

            # 计算结果concat在一起
            basic_prs_accum = pd.concat([mean_prs_accum, max_prs_accum, min_prs_accum], axis=0)

            # 增加月份
            month_list = [str(i) + '月' for i in range(1, 13)]
            month_list.append('年')
            basic_prs_accum.columns = month_list
            basic_prs_accum.reset_index(inplace=True)
            basic_prs_accum.rename(columns={'index': '要素'}, inplace=True)

            tmp = basic_prs_accum.dropna(axis=1, how='all')
            if len(tmp.columns) == 1:
                basic_prs_accum = None
            else:
                basic_prs_accum = basic_prs_accum.to_dict(orient='records')

        except Exception as e:
            logging.exception(e)
            basic_prs_accum = None

        finally:
            try:
                report_path = prs_report(basic_prs_yearly, basic_prs_accum, prs_month, data_dir)
            except:
                report_path = None
                
            return basic_prs_yearly, basic_prs_accum, report_path


if __name__ == '__main__':
    daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    monthly_df = pd.read_csv(cfg.FILES.QH_DATA_MONTH, low_memory=False)
    sta_ids = '52707'
    years = '2000,2020'

    daily_elements = 'PRS_Avg,PRS_Max,PRS_Min,'
    day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements[:-1]).split(',')
    post_daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')
    
    monthly_elements = 'PRS_Avg,PRS_Max,PRS_Min,PRS_Max_ODay_C,PRS_Min_ODay_C,'
    month_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,' + monthly_elements[:-1]).split(',')
    post_monthly_df = get_local_data(monthly_df, sta_ids, month_eles, years, 'Month')
    
    data_dir = r'D:\Project\3_项目\2_气候评估和气候可行性论证\5_time\20250206'
    basic_prs_yearly, basic_prs_accum, report_path = basic_prs_statistics(post_daily_df, post_monthly_df, data_dir)
