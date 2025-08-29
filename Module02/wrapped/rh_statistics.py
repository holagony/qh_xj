import logging
import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.data_processing import yearly_data_processing, monthly_data_processing
from Report.code.Module02.rh import rh_report


def basic_rh_statistics(rh_day, rh_month, data_dir):
    '''
    相对湿度要素，历年和累年各月统计，
    使用天擎上的年数据和月数据，要素名称为天擎上默认的名称
    年值要素：['Station_Id_C', 'Station_Name', 'Year', 'RHU_Avg', 'RHU_Min', 'V13007_067']
    月值要素：['Station_Id_C', 'Station_Name', 'Year', 'Mon', 'RHU_Avg', 'RHU_Min', 'RHU_Min_ODay_C']
    return: dataframe
    '''
    try:
        yearly_total_rhu = rh_day['RHU_Avg'].resample('1A').mean().round(1).to_frame()
        yearly_total_rhu.index = yearly_total_rhu.index.year

        min_rhu_dates = rh_day.dropna(subset=['RHU_Min']).groupby(lambda x: x.year)['RHU_Min'].idxmax()
        min_rhu_info = rh_day.loc[min_rhu_dates[min_rhu_dates.notna()], ['RHU_Min']]
        min_rhu_info['最小相对湿度出现日期'] = min_rhu_info.index.strftime('%m月%d日')
        min_rhu_info.index = min_rhu_info.index.year

        # 合并结果
        basic_rh_yearly = pd.concat([yearly_total_rhu, min_rhu_info], axis=1)
        basic_rh_yearly.insert(loc=0, column='年份', value=basic_rh_yearly.index)
        basic_rh_yearly.reset_index(drop=True, inplace=True)
        basic_rh_yearly.columns = ['年份', '平均相对湿度(%)', '最小相对湿度(%)', '最小相对湿度出现日期']

        tmp = basic_rh_yearly.dropna(axis=1, how='all')
        if len(tmp.columns) == 1:  # 如果只有年份一列，说明全部没有数据
            basic_rh_yearly = None
        else:
            basic_rh_yearly = basic_rh_yearly.round(1).to_dict(orient='records')

    except Exception as e:
        logging.exception(e)
        basic_rh_yearly = None

    finally:
        try:
            # B.累年各月统计
            rh = rh_month['RHU_Avg'].to_frame()
            rh_min = rh_month[['RHU_Min', 'RHU_Min_ODay_C', 'Year', 'Mon']]

            mean_rh_accum = []
            min_rh_accum = []

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
                month_i_mean = rh[rh.index.month == i].mean().round(0).to_frame()
                mean_rh_accum.append(month_i_mean)

                # min
                month_i_min = rh_min[rh_min.index.month == i]
                month_i_min = month_i_min[month_i_min['RHU_Min'] == month_i_min['RHU_Min'].min()]

                # 针对多个时间点数值相同的情况
                if len(month_i_min) > 1:
                    rh_data = month_i_min.iloc[0, 0]  # columns: ['RHU_Min','RHU_Min_ODay_C','Year','Mon']
                    occur_day = str(month_i_min['RHU_Min_ODay_C'].apply(sample).sum()) + 'T'
                    occur_year = str(len(month_i_min)) + 'N'
                    occur_month = month_i_min.iloc[0, 3]

                    array = np.array([rh_data, occur_day, occur_year, occur_month]).reshape(1, -1)
                    min_df = pd.DataFrame(array, columns=month_i_min.columns, index=[month_i_min.index[0]])

                else:
                    min_df = month_i_min

                min_rh_accum.append(min_df)

            ####################################################
            # 结果合成为DateFrame
            # mean
            mean_rh_accum = pd.concat(mean_rh_accum, axis=1, ignore_index=True)
            mean_rh_accum.index = ['平均相对湿度(%)']
            mean_rh_accum['全年'] = mean_rh_accum.iloc[:, :].mean(axis=1).round(0)

            # min
            min_rh_accum = pd.concat(min_rh_accum, axis=0, ignore_index=True)
            min_rh_accum['RHU_Min'] = min_rh_accum['RHU_Min'].astype(float)
            min_row = min_rh_accum[min_rh_accum['RHU_Min'] == min_rh_accum['RHU_Min'].min()].reset_index(drop=True)

            if len(min_row) == 1:
                rh = min_row.loc[0, 'RHU_Min']
                date = min_row['Mon'].map(str) + '-' + min_row['RHU_Min_ODay_C'].map(str)
                year = min_row.loc[0, 'Year']
                values_list = [rh, date.values[0], year]

            elif len(min_row) > 1:
                rh = min_row.loc[0, 'RHU_Min']
                date = str(len(min_row)) + 'T'
                year = str(min_row['Year'].apply(sample).sum()) + 'N'
                values_list = [rh, date, year]

            min_rh_accum.drop('Mon', axis=1, inplace=True)  # 删除月份列
            min_rh_accum = min_rh_accum.T
            min_rh_accum.index = ['最小相对湿度(%)', '最小相对湿度出现日期', '最小相对湿度出现年份']
            min_rh_accum['全年'] = values_list

            # 计算结果concat在一起
            basic_rh_accum = pd.concat([mean_rh_accum, min_rh_accum], axis=0)

            # 增加月份
            month_list = [str(i) + '月' for i in range(1, 13)]
            month_list.append('年')
            basic_rh_accum.columns = month_list
            basic_rh_accum.reset_index(inplace=True)
            basic_rh_accum.rename(columns={'index': '要素'}, inplace=True)

            tmp = basic_rh_accum.dropna(axis=1, how='all')
            if len(tmp.columns) == 1:
                basic_rh_accum = None
            else:
                basic_rh_accum = basic_rh_accum.to_dict(orient='records')

        except Exception as e:
            logging.exception(e)
            basic_rh_accum = None

        finally:
            try:
                report_path = rh_report(basic_rh_yearly, basic_rh_accum, rh_month, data_dir)
            except:
                report_path = None

            return basic_rh_yearly, basic_rh_accum, report_path


if __name__ == '__main__':
    yearly_df = pd.read_csv(cfg.FILES.module2_year_CSV)
    monthly_df = pd.read_csv(cfg.FILES.module2_month_CSV)
    post_yearly_df = yearly_data_processing(yearly_df)
    post_monthly_df = monthly_data_processing(monthly_df)
    data_dir=r'D:\Project\3_项目\2_气候评估和气候可行性论证\qhkxxlz\Report\report\Module02'
    basic_rh_yearly, basic_rh_accum, report_path = basic_rh_statistics(post_yearly_df, post_monthly_df,data_dir)
