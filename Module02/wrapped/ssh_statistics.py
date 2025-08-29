# -*- coding: utf-8 -*-
"""
Created on Wed May  7 15:29:17 2025

@author: hx
"""

import logging
import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.data_processing import daily_data_processing
from Report.code.Module02.vapor import vapor_report


def basic_ssh_statistics(vapor_day, data_dir):
    '''
    日照时数要素，历年和累年各月统计，
    使用天擎上的日数据，要素名称为天擎上默认的名称
    日值要素：['Station_Id_C', 'Station_Name', 'Year', 'Mon', 'Day', 'SSH']
    return: dataframe
    '''

    try:
        vapor = vapor_day['SSH'].to_frame()
        vapor.dropna(axis=0, how='any', inplace=True)

        # A.历年统计
        vapor_yearly = vapor.resample('1A', closed='right', label='right').sum()
        vapor_yearly['year'] = vapor_yearly.index.year
        vapor_yearly = vapor_yearly[['year', 'SSH']]
        vapor_yearly.reset_index(drop=True, inplace=True)

        year_max_idx = vapor.groupby([vapor.index.year], as_index=False)['SSH'].idxmax()
        max_idx = year_max_idx['SSH'].tolist()
        vapor_max = vapor.loc[max_idx]
        vapor_max['date'] = vapor_max.index.strftime("%m月%d日")
        vapor_max.reset_index(drop=True, inplace=True)

        year_min_idx = vapor.groupby([vapor.index.year], as_index=False)['SSH'].idxmin()
        min_idx = year_min_idx['SSH'].tolist()
        vapor_min = vapor.loc[min_idx]
        vapor_min['date'] = vapor_min.index.strftime("%m月%d日")
        vapor_min.reset_index(drop=True, inplace=True)

        basic_vapor_yearly = pd.concat([vapor_yearly, vapor_max, vapor_min], axis=1)
        basic_vapor_yearly.columns = ['年份', '总日照时数(h)', '最大日照时数(h)', '最大日照时数出现日期', '最小日照时数(h)', '最小日照时数出现日期']

        tmp = basic_vapor_yearly.dropna(axis=1, how='all')
        if len(tmp.columns) == 1:  # 如果只有年份一列，说明全部没有数据
            basic_vapor_yearly = None
        else:
            basic_vapor_yearly = basic_vapor_yearly.round(1).to_dict(orient='records')

    except Exception as e:
        logging.exception(e)
        basic_vapor_yearly = None

    finally:
        try:
            # B.累年各月统计
            vapor_monthly = vapor.resample('1M', closed='right', label='right').mean()

            vapor_max_idx = vapor.groupby([vapor.index.year, vapor.index.month], as_index=False)['SSH'].idxmax()
            max_idx = vapor_max_idx['SSH'].tolist()

            vapor_max = vapor.loc[max_idx]
            vapor_max['date'] = vapor_max.index.strftime("%d")
            vapor_max['Year'] = vapor_max.index.strftime("%Y")
            vapor_max['Mon'] = vapor_max.index.strftime("%m")

            vapor_min_idx = vapor.groupby([vapor.index.year, vapor.index.month], as_index=False)['SSH'].idxmin()
            min_idx = vapor_min_idx['SSH'].tolist()
            vapor_min = vapor.loc[min_idx]
            vapor_min['date'] = vapor_min.index.strftime("%d")
            vapor_min['Year'] = vapor_min.index.strftime("%Y")
            vapor_min['Mon'] = vapor_min.index.strftime("%m")

            mean_vapor_accum = []
            max_vapor_accum = []
            min_vapor_accum = []

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
                month_i_mean = vapor_monthly[vapor_monthly.index.month == i].mean().round(1).to_frame()
                mean_vapor_accum.append(month_i_mean)

                # max
                month_i_max = vapor_max[vapor_max.index.month == i]
                month_i_max = month_i_max[month_i_max['SSH'] == month_i_max['SSH'].max()]

                # 针对多个时间点数值相同的情况
                if len(month_i_max) > 1:
                    vapor_data = month_i_max.iloc[0, 0]  # columns: ['vapor', 'date', 'Year', 'Mon']
                    occur_day = str(month_i_max['date'].apply(sample).sum()) + 'T'
                    occur_year = str(len(month_i_max)) + 'N'
                    occur_month = month_i_max.iloc[0, 3]

                    array = np.array([vapor_data, occur_day, occur_year, occur_month]).reshape(1, -1)
                    max_df = pd.DataFrame(array, columns=month_i_max.columns, index=[month_i_max.index[0]])

                else:
                    max_df = month_i_max

                max_vapor_accum.append(max_df)

                # min
                month_i_min = vapor_min[vapor_min.index.month == i]
                month_i_min = month_i_min[month_i_min['SSH'] == month_i_min['SSH'].min()]

                # 针对多个时间点数值相同的情况
                if len(month_i_min) > 1:
                    vapor_data = month_i_min.iloc[0, 0]  # columns: ['SSH', 'date', 'Year', 'Mon']
                    occur_day = str(month_i_min['date'].apply(sample).sum()) + 'T'
                    occur_year = str(len(month_i_min)) + 'N'
                    occur_month = month_i_min.iloc[0, 3]

                    array = np.array([vapor_data, occur_day, occur_year, occur_month]).reshape(1, -1)
                    min_df = pd.DataFrame(array, columns=month_i_min.columns, index=[month_i_min.index[0]])

                else:
                    min_df = month_i_min

                min_vapor_accum.append(min_df)

            ####################################################
            # 结果合成为DateFrame
            # mean
            mean_vapor_accum = pd.concat(mean_vapor_accum, axis=1, ignore_index=True)
            mean_vapor_accum.index = ['总日照时数(h)']
            mean_vapor_accum['全年'] = mean_vapor_accum.iloc[:, :].mean(axis=1).round(1)

            # max
            max_vapor_accum = pd.concat(max_vapor_accum, axis=0, ignore_index=True)
            max_vapor_accum['SSH'] = max_vapor_accum['SSH'].astype(float)
            max_row = max_vapor_accum[max_vapor_accum['SSH'] == max_vapor_accum['SSH'].max()].reset_index(drop=True)

            if len(max_row) == 1:
                vapor = max_row.loc[0, 'SSH']
                date = max_row['Mon'].map(str) + '-' + max_row['date'].map(str)
                year = max_row.loc[0, 'Year']
                values_list = [vapor, date.values[0], year]

            elif len(max_row) > 1:
                vapor = max_row.loc[0, 'SSH']
                date = str(len(max_row)) + 'T'
                year = str(max_row['Year'].apply(sample).sum()) + 'N'
                values_list = [vapor, date, year]

            max_vapor_accum.drop('Mon', axis=1, inplace=True)  # 删除月份列
            max_vapor_accum = max_vapor_accum.T
            max_vapor_accum.index = ['最大日照时数(h)', '最大日照时数出现日期', '最大日照时数出现年份']
            max_vapor_accum['全年'] = values_list

            # min
            min_vapor_accum = pd.concat(min_vapor_accum, axis=0, ignore_index=True)
            min_vapor_accum['SSH'] = min_vapor_accum['SSH'].astype(float)
            min_row = min_vapor_accum[min_vapor_accum['SSH'] == min_vapor_accum['SSH'].min()].reset_index(drop=True)

            if len(min_row) == 1:
                vapor = min_row.loc[0, 'SSH']
                date = min_row['Mon'].map(str) + '-' + min_row['date'].map(str)
                year = min_row.loc[0, 'Year']
                values_list = [vapor, date.values[0], year]

            elif len(min_row) > 1:
                vapor = min_row.loc[0, 'SSH']
                date = str(len(min_row)) + 'T'
                year = str(min_row['Year'].apply(sample).sum()) + 'N'
                values_list = [vapor, date, year]

            min_vapor_accum.drop('Mon', axis=1, inplace=True)  # 删除月份列
            min_vapor_accum = min_vapor_accum.T
            min_vapor_accum.index = ['最小日照时数(h)', '最小日照时数出现日期', '最小日照时数出现年份']
            min_vapor_accum['全年'] = values_list

            # 计算结果concat在一起
            basic_vapor_accum = pd.concat([mean_vapor_accum, max_vapor_accum, min_vapor_accum], axis=0)

            # 增加月份
            month_list = [str(i) + '月' for i in range(1, 13)]
            month_list.append('年')
            basic_vapor_accum.columns = month_list
            basic_vapor_accum.reset_index(inplace=True)
            basic_vapor_accum.rename(columns={'index': '要素'}, inplace=True)

            tmp = basic_vapor_accum.dropna(axis=1, how='all')
            if len(tmp.columns) == 1:  # 如果只有年份一列，说明全部没有数据
                basic_vapor_accum = None
            else:
                basic_vapor_accum = basic_vapor_accum.to_dict(orient='records')

        except Exception as e:
            logging.exception(e)
            basic_vapor_accum = None

        finally:
            try:
                report_path = vapor_report(basic_vapor_yearly, basic_vapor_accum, vapor_day, data_dir)
            except:
                report_path = None
                
            return basic_vapor_yearly, basic_vapor_accum, report_path


if __name__ == '__main__':
    daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    post_daily_df = daily_data_processing(daily_df)
    post_daily_df = post_daily_df[post_daily_df['Station_Id_C']=='52866']
    data_dir = r'D:\Project'
    vapor_day=post_daily_df
    basic_vapor_yearly, basic_vapor_accum, report_path = basic_vapor_statistics(post_daily_df,data_dir)
    
    
    
    
