import logging
import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.data_processing import yearly_data_processing, monthly_data_processing
from Report.code.Module02.pre import pre_report

# 统计更新：累年各月表格-降水量要素-最大降水量/最小降水量所在的行，
# 最后一列(全年)对应的数值替换为 年最大降水量数值及对应的年份/年最小降水量及对应的年份


def basic_pre_statistics(pre_day, pre_month, data_dir):
    '''
    降水要素，历年和累年各月统计，
    使用天擎上的年数据和月数据，要素名称为天擎上默认的名称
    年值要素：['Station_Id_C', 'Station_Name', 'Year', 'PRE_Time_2020', 'PRE_Max_Day', 'V13052_067', 
              'PRE_A0p1mm_Days', 'PRE_A10mm_Days', 'PRE_A25mm_Days', 'PRE_A50mm_Days', 'PRE_A100mm_Days', 
              'PRE_A150mm_Days', 'Days_Max_Coti_PRE', 'PRE_Conti_Max', 'PRE_LCDays_EMon', 'EDay_Max_Coti_PRE',
              'NPRE_LCDays', 'NPRE_LCDays_EMon', 'NPRE_LCDays_EDay', 'PRE_Max_Conti', 'Days_Max_Conti_PRE',
              'PRE_Coti_Max_EMon', 'PRE_Coti_Max_EDay', '最长连续降水止月日', '最长连续无降水止月日', '最大连续降水止月日']
    月值要素：['Station_Id_C', 'Station_Name', 'Year', 'Mon', 'PRE_Time_2020', 'PRE_Max_Day', 'PRE_Max_ODay_C',
              'PRE_A0p1mm_Days', 'PRE_A10mm_Days', 'PRE_A25mm_Days', 'PRE_A50mm_Days', 'PRE_A100mm_Days',
              'PRE_A150mm_Days', 'Days_Max_Coti_PRE', 'PRE_Conti_Max', 'EDay_Max_Coti_PRE', 'NPRE_LCDays', 
              'NPRE_LCDays_EDay', 'PRE_Max_Conti', 'Days_Max_Conti_PRE', 'PRE_Coti_Max_EDay']
    return: dataframe
    '''
    try:
        # 计算历年总降水量
        yearly_total_pre = pre_day['PRE_Time_2020'].resample('1A').sum().round(1).to_frame()
        yearly_total_pre.index = yearly_total_pre.index.year

        # 计算历年日最大降水量及其出现日期
        max_pre_dates = pre_day.dropna(subset=['PRE_Time_2020']).groupby(lambda x: x.year)['PRE_Time_2020'].idxmax()
        max_pre_info = pre_day.loc[max_pre_dates[max_pre_dates.notna()], ['PRE_Time_2020']]
        max_pre_info['最大降水量出现日期'] = max_pre_info.index.strftime('%m月%d日')
        max_pre_info.index = max_pre_info.index.year

        # 合并结果
        basic_pre_yearly = pd.concat([yearly_total_pre, max_pre_info], axis=1)
        basic_pre_yearly.insert(loc=0, column='年份', value=basic_pre_yearly.index)
        basic_pre_yearly.reset_index(drop=True, inplace=True)
        basic_pre_yearly.columns = ['年份', '总降水量(mm)', '日最大降水量(mm)', '日最大降水量出现日期']

        # 年最大降水量数值及对应的年份/年最小降水量及对应的年份
        # 后续累年各月统计会用到
        max_pre = basic_pre_yearly.loc[basic_pre_yearly['总降水量(mm)'] == basic_pre_yearly['总降水量(mm)'].max(), '总降水量(mm)'].values[0]
        max_pre_year = basic_pre_yearly.loc[basic_pre_yearly['总降水量(mm)'] == basic_pre_yearly['总降水量(mm)'].max(), '年份'].values[0]
        min_pre = basic_pre_yearly.loc[basic_pre_yearly['总降水量(mm)'] == basic_pre_yearly['总降水量(mm)'].min(), '总降水量(mm)'].values[0]
        min_pre_year = basic_pre_yearly.loc[basic_pre_yearly['总降水量(mm)'] == basic_pre_yearly['总降水量(mm)'].min(), '年份'].values[0]

        # 判断
        tmp = basic_pre_yearly.dropna(axis=1, how='all')
        if len(tmp.columns) == 1:  # 如果只有年份一列，说明全部没有数据
            basic_pre_yearly = None
        else:
            basic_pre_yearly = basic_pre_yearly.round(1).to_dict(orient='records')

    except Exception as e:
        logging.exception(e)
        basic_pre_yearly = None
        max_pre = np.nan
        max_pre_year = np.nan
        min_pre = np.nan
        min_pre_year = np.nan

    finally:
        try:
            # B.累年各月统计
            pre = pre_month[['PRE_Time_2020', 'PRE_A0p1mm_Days', 'PRE_A10mm_Days', 'PRE_A25mm_Days', 'PRE_A50mm_Days', 'PRE_A100mm_Days', 'PRE_A150mm_Days']]

            pre_max_part1 = pre_month[['PRE_Max_Day', 'PRE_Max_ODay_C', 'Year', 'Mon']]
            pre_max_part2 = pre_month[['Days_Max_Coti_PRE', 'PRE_Conti_Max', 'EDay_Max_Coti_PRE', 'Year', 'Mon']]
            pre_max_part3 = pre_month[['NPRE_LCDays', 'NPRE_LCDays_EDay', 'Year', 'Mon']]
            pre_max_part4 = pre_month[['Days_Max_Conti_PRE', 'PRE_Max_Conti', 'PRE_Coti_Max_EDay', 'Year', 'Mon']]
            pre_2020 = pre_month[['PRE_Time_2020', 'Year']]

            mean_pre_accum = []
            max_pre_accum_part1 = []
            max_pre_accum_part2 = []
            max_pre_accum_part3 = []
            max_pre_accum_part4 = []
            max_pre2020_accum = []
            min_pre2020_accum = []

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
                month_i_mean = pre[pre.index.month == i].mean().round(1).to_frame()
                mean_pre_accum.append(month_i_mean)

                # max_part1
                month_i_max_part1 = pre_max_part1[pre_max_part1.index.month == i]
                month_i_max_part1 = month_i_max_part1[month_i_max_part1['PRE_Max_Day'] == month_i_max_part1['PRE_Max_Day'].max()].round(1)

                # 针对多个时间点数值相同的情况
                if len(month_i_max_part1) > 1:
                    pre_data = month_i_max_part1.iloc[0, 0]  # columns: ['PRE_Max_Day', 'PRE_Max_ODay_C', 'Year', 'Mon']
                    occur_day = str(month_i_max_part1['PRE_Max_ODay_C'].apply(sample).sum()) + 'T'
                    occur_year = str(len(month_i_max_part1)) + 'N'
                    occur_month = month_i_max_part1.iloc[0, 3]

                    array = np.array([pre_data, occur_day, occur_year, occur_month]).reshape(1, -1)
                    max_df_part1 = pd.DataFrame(array, columns=month_i_max_part1.columns, index=[month_i_max_part1.index[0]])

                else:
                    max_df_part1 = month_i_max_part1

                max_pre_accum_part1.append(max_df_part1)

                # max_part2
                # 最长连续降水日数/最长连续降水量/最长连续降水止日
                month_i_max_part2 = pre_max_part2[pre_max_part2.index.month == i]
                month_i_max_part2 = month_i_max_part2[month_i_max_part2['Days_Max_Coti_PRE'] == month_i_max_part2['Days_Max_Coti_PRE'].max()]

                # 针对多个时间点数值相同的情况，不同的是，因为有多列特征，且特征之间有联系，所以采用排序后选择第一行数据
                if len(month_i_max_part2) > 1:
                    month_i_max_part2.sort_values(by=['Days_Max_Coti_PRE', 'PRE_Conti_Max'], ascending=[False, False], inplace=True)  # 先排序降水日，再排序对应降水量

                    pre_data1 = month_i_max_part2.iloc[0, 0]  # columns: ['Days_Max_Coti_PRE','PRE_Conti_Max','EDay_Max_Coti_PRE','Year','Mon']
                    pre_data2 = month_i_max_part2.iloc[0, 1]
                    occur_day = month_i_max_part2.iloc[0, 2]
                    occur_year = month_i_max_part2.iloc[0, 3]
                    occur_month = month_i_max_part2.iloc[0, 4]

                    array = np.array([pre_data1, pre_data2, occur_day, occur_year, occur_month]).reshape(1, -1)
                    max_df_part2 = pd.DataFrame(array, columns=month_i_max_part2.columns, index=[month_i_max_part2.index[0]])

                else:
                    max_df_part2 = month_i_max_part2

                max_pre_accum_part2.append(max_df_part2)

                # max_part3
                # 最长连续无降水日数/最长连续无降水止日
                month_i_max_part3 = pre_max_part3[pre_max_part3.index.month == i]
                month_i_max_part3 = month_i_max_part3[month_i_max_part3['NPRE_LCDays'] == month_i_max_part3['NPRE_LCDays'].max()]

                # 针对多个时间点数值相同的情况
                if len(month_i_max_part3) > 1:
                    pre_data = month_i_max_part3.iloc[0, 0]  # columns: ['NPRE_LCDays','NPRE_LCDays_EDay','Year','Mon']
                    occur_day = str(month_i_max_part3['NPRE_LCDays'].apply(sample).sum()) + 'T'
                    occur_year = str(len(month_i_max_part3)) + 'N'
                    occur_month = month_i_max_part3.iloc[0, 3]

                    array = np.array([pre_data, occur_day, occur_year, occur_month]).reshape(1, -1)
                    max_df_part3 = pd.DataFrame(array, columns=month_i_max_part3.columns, index=[month_i_max_part3.index[0]])

                else:
                    max_df_part3 = month_i_max_part3

                max_pre_accum_part3.append(max_df_part3)

                # max_part4
                # 最大连续降水量/最大连续降水日数/最大连续降水止日
                month_i_max_part4 = pre_max_part4[pre_max_part4.index.month == i]
                month_i_max_part4 = month_i_max_part4[month_i_max_part4['Days_Max_Conti_PRE'] == month_i_max_part4['Days_Max_Conti_PRE'].max()]

                # 针对多个时间点数值相同的情况，不同的是，因为有多列特征，且特征之间有联系，所以采用排序后选择第一行数据
                if len(month_i_max_part4) > 1:
                    month_i_max_part4.sort_values(by=['Days_Max_Conti_PRE', 'PRE_Max_Conti'], ascending=[False, False], inplace=True)  # 先排序降水日，再排序对应降水量

                    pre_data1 = month_i_max_part4.iloc[0, 0]  # columns: ['Days_Max_Conti_PRE','PRE_Max_Conti','PRE_Coti_Max_EDay','Year','Mon']
                    pre_data2 = month_i_max_part4.iloc[0, 1]
                    occur_day = month_i_max_part4.iloc[0, 2]
                    occur_year = month_i_max_part4.iloc[0, 3]
                    occur_month = month_i_max_part4.iloc[0, 4]

                    array = np.array([pre_data1, pre_data2, occur_day, occur_year, occur_month]).reshape(1, -1)
                    max_df_part4 = pd.DataFrame(array, columns=month_i_max_part4.columns, index=[month_i_max_part4.index[0]])

                else:
                    max_df_part4 = month_i_max_part4

                max_pre_accum_part4.append(max_df_part4)

                # pre_2020_max
                month_i_max_2020 = pre_2020[pre_2020.index.month == i]
                month_i_max_2020 = month_i_max_2020[month_i_max_2020['PRE_Time_2020'] == month_i_max_2020['PRE_Time_2020'].max()].round(1)

                # 针对多个时间点数值相同的情况
                if len(month_i_max_2020) > 1:
                    pre_data = month_i_max_2020.iloc[0, 0]  # columns: ['PRE_Time_2020', 'Year']
                    occur_year = str(len(month_i_max_2020)) + 'N'

                    array = np.array([pre_data, occur_year]).reshape(1, -1)
                    max_df = pd.DataFrame(array, columns=month_i_max_2020.columns, index=[month_i_max_2020.index[0]])

                else:
                    max_df = month_i_max_2020

                max_pre2020_accum.append(max_df)

                # pre_2020_min
                month_i_min_2020 = pre_2020[pre_2020.index.month == i]
                month_i_min_2020 = month_i_min_2020[month_i_min_2020['PRE_Time_2020'] == month_i_min_2020['PRE_Time_2020'].min()]

                # 针对多个时间点数值相同的情况
                if len(month_i_min_2020) > 1:
                    pre_data = month_i_min_2020.iloc[0, 0]  # columns: ['PRE_Time_2020', 'Year']
                    occur_year = str(len(month_i_min_2020)) + 'N'

                    array = np.array([pre_data, occur_year]).reshape(1, -1)
                    min_df = pd.DataFrame(array, columns=month_i_min_2020.columns, index=[month_i_min_2020.index[0]])

                else:
                    min_df = month_i_min_2020

                min_pre2020_accum.append(min_df)

            ####################################################
            # 结果合成为DateFrame
            # mean
            mean_pre_accum = pd.concat(mean_pre_accum, axis=1, ignore_index=True)
            mean_pre_accum.index = ['平均降水量(mm)', '降水量≥0.1mm日数', '降水量≥10mm日数', '降水量≥25mm日数', '降水量≥50mm日数', '降水量≥100mm日数', '日降水量≥150mm日数']
            mean_pre_accum['全年'] = mean_pre_accum.iloc[:, :].sum(axis=1).round(1)

            # max_part1
            max_pre_accum_part1 = pd.concat(max_pre_accum_part1, axis=0, ignore_index=True)
            max_pre_accum_part1['PRE_Max_Day'] = max_pre_accum_part1['PRE_Max_Day'].astype(float)
            max_row = max_pre_accum_part1[max_pre_accum_part1['PRE_Max_Day'] == max_pre_accum_part1['PRE_Max_Day'].max()].reset_index(drop=True)

            if len(max_row) == 1:
                pre = max_row.loc[0, 'PRE_Max_Day']
                date = max_row['Mon'].map(str) + '-' + max_row['PRE_Max_ODay_C'].map(str)
                year = max_row.loc[0, 'Year']  # 气压最大值对应的年份
                values_list = [pre, date.values[0], year]

            elif len(max_row) > 1:
                pre = max_row.loc[0, 'PRE_Max_Day']
                date = str(len(max_row)) + 'T'
                year = str(max_row['Year'].apply(sample).sum()) + 'N'
                values_list = [pre, date, year]

            max_pre_accum_part1.drop('Mon', axis=1, inplace=True)  # 删除月份列
            max_pre_accum_part1 = max_pre_accum_part1.T
            max_pre_accum_part1.index = ['日最大降水量(mm)', '日最大降水量出现日期', '日最大降水量出现年份']
            max_pre_accum_part1['全年'] = values_list

            # max_part2
            max_pre_accum_part2 = pd.concat(max_pre_accum_part2, axis=0, ignore_index=True)
            max_pre_accum_part2['Days_Max_Coti_PRE'] = max_pre_accum_part2['Days_Max_Coti_PRE'].astype(float)

            max_row = max_pre_accum_part2[max_pre_accum_part2['Days_Max_Coti_PRE'] == max_pre_accum_part2['Days_Max_Coti_PRE'].max()].reset_index(drop=True)
            max_row.sort_values(by=['Days_Max_Coti_PRE', 'PRE_Conti_Max'], ascending=[False, False], inplace=True)

            pre1 = max_row.loc[0, 'Days_Max_Coti_PRE']
            pre2 = max_row.loc[0, 'PRE_Conti_Max']
            date = str(max_row.loc[0, 'Mon']) + '-' + str(max_row.loc[0, 'EDay_Max_Coti_PRE'])
            year = max_row.loc[0, 'Year']  # 气压最大值对应的年份
            values_list = [pre1, pre2, date, year]

            max_pre_accum_part2.drop('Mon', axis=1, inplace=True)  # 删除月份列
            max_pre_accum_part2 = max_pre_accum_part2.T
            max_pre_accum_part2.index = ['最长连续降水日数', '最长连续降水量(mm)', '最长连续降水止日', '最长连续降水出现年份']
            max_pre_accum_part2['全年'] = values_list

            # max_part3
            max_pre_accum_part3 = pd.concat(max_pre_accum_part3, axis=0, ignore_index=True)
            max_pre_accum_part3['NPRE_LCDays'] = max_pre_accum_part3['NPRE_LCDays'].astype(float)
            max_row = max_pre_accum_part3[max_pre_accum_part3['NPRE_LCDays'] == max_pre_accum_part3['NPRE_LCDays'].max()].reset_index(drop=True)

            if len(max_row) == 1:
                pre = max_row.loc[0, 'NPRE_LCDays']
                date = max_row['Mon'].map(str) + '-' + max_row['NPRE_LCDays_EDay'].map(str)
                year = max_row.loc[0, 'Year']  # 气压最大值对应的年份
                values_list = [pre, date.values[0], year]

            elif len(max_row) > 1:
                pre = max_row.loc[0, 'NPRE_LCDays']
                date = str(len(max_row)) + 'T'
                year = str(max_row['Year'].apply(sample).sum()) + 'N'
                values_list = [pre, date, year]

            max_pre_accum_part3.drop('Mon', axis=1, inplace=True)  # 删除月份列
            max_pre_accum_part3 = max_pre_accum_part3.T
            max_pre_accum_part3.index = ['最长连续无降水日数', '最长连续无降水止日', '最长连续无降水出现年份']
            max_pre_accum_part3['全年'] = values_list

            # max_part4
            max_pre_accum_part4 = pd.concat(max_pre_accum_part4, axis=0, ignore_index=True)
            max_pre_accum_part4['Days_Max_Conti_PRE'] = max_pre_accum_part4['Days_Max_Conti_PRE'].astype(float)

            max_row = max_pre_accum_part4[max_pre_accum_part4['Days_Max_Conti_PRE'] == max_pre_accum_part4['Days_Max_Conti_PRE'].max()].reset_index(drop=True)
            max_row.sort_values(by=['Days_Max_Conti_PRE', 'PRE_Max_Conti'], ascending=[False, False], inplace=True)

            pre1 = max_row.loc[0, 'Days_Max_Conti_PRE']
            pre2 = max_row.loc[0, 'PRE_Max_Conti']
            date = str(max_row.loc[0, 'Mon']) + '-' + str(max_row.loc[0, 'PRE_Coti_Max_EDay'])
            year = max_row.loc[0, 'Year']  # 气压最大值对应的年份
            values_list = [pre1, pre2, date, year]

            max_pre_accum_part4.drop('Mon', axis=1, inplace=True)  # 删除月份列
            max_pre_accum_part4 = max_pre_accum_part4.T
            # todo '最大连续降水日数', '最大连续降水量(mm)' 两个要素是否有关系？目前是有关系，先确定日数，再找相应的降水量
            max_pre_accum_part4.index = ['最大连续降水日数', '最大连续降水量(mm)', '最大连续降水止日', '最大连续降水出现年份']
            max_pre_accum_part4['全年'] = values_list

            # pre_2020_max
            max_pre2020_accum = pd.concat(max_pre2020_accum, axis=0, ignore_index=True)
            max_pre2020_accum['PRE_Time_2020'] = max_pre2020_accum['PRE_Time_2020'].astype(float)

            # max_row = max_pre2020_accum[max_pre2020_accum['PRE_Time_2020'] == max_pre2020_accum['PRE_Time_2020'].max()].reset_index(drop=True)

            # if len(max_row) == 1:
            #     pre = max_row.loc[0, 'PRE_Time_2020']
            #     year = max_row.loc[0, 'Year']
            #     values_list = [pre, year]

            # elif len(max_row) > 1:
            #     pre = max_row.loc[0, 'PRE_Time_2020']
            #     year = str(max_row['Year'].apply(sample).sum()) + 'N'
            #     values_list = [pre, year]
            values_list = [max_pre, max_pre_year]

            max_pre2020_accum = max_pre2020_accum.T
            max_pre2020_accum.index = ['最大降水量(mm)', '最大降水量出现年份']
            max_pre2020_accum['全年'] = values_list

            # pre_2020_min
            min_pre2020_accum = pd.concat(min_pre2020_accum, axis=0, ignore_index=True)
            min_pre2020_accum['PRE_Time_2020'] = min_pre2020_accum['PRE_Time_2020'].astype(float)

            # min_row = min_pre2020_accum[min_pre2020_accum['PRE_Time_2020'] == min_pre2020_accum['PRE_Time_2020'].min()].reset_index(drop=True)

            # if len(min_row) == 1:
            #     pre = min_row.loc[0, 'PRE_Time_2020']
            #     year = min_row.loc[0, 'Year']
            #     values_list = [pre, year]

            # elif len(min_row) > 1:
            #     pre = min_row.loc[0, 'PRE_Time_2020']
            #     year = str(min_row['Year'].apply(sample).sum()) + 'N'
            #     values_list = [pre, year]
            values_list = [min_pre, min_pre_year]

            min_pre2020_accum = min_pre2020_accum.T
            min_pre2020_accum.index = ['最小降水量(mm)', '最小降水量出现年份']
            min_pre2020_accum['全年'] = values_list

            # 计算结果concat在一起
            basic_pre_accum = pd.concat([mean_pre_accum, max_pre_accum_part1, max_pre_accum_part2, max_pre_accum_part3, max_pre_accum_part4, max_pre2020_accum, min_pre2020_accum], axis=0)

            # 增加月份
            month_list = [str(i) + '月' for i in range(1, 13)]
            month_list.append('年')
            basic_pre_accum.columns = month_list
            basic_pre_accum.reset_index(inplace=True)
            basic_pre_accum.rename(columns={'index': '要素'}, inplace=True)

            tmp = basic_pre_accum.dropna(axis=1, how='all')
            if len(tmp.columns) == 1:
                basic_pre_accum = None
            else:
                basic_pre_accum = basic_pre_accum.to_dict(orient='records')

        except Exception as e:
            logging.exception(e)
            basic_pre_accum = None

        finally:
            try:
                report_path = pre_report(basic_pre_yearly, basic_pre_accum, pre_month, data_dir)
            except:
                report_path = None
                
            return basic_pre_yearly, basic_pre_accum, report_path


if __name__ == '__main__':
    yearly_df = pd.read_csv(cfg.FILES.module2_year_CSV)
    monthly_df = pd.read_csv(cfg.FILES.module2_month_CSV)
    post_yearly_df = yearly_data_processing(yearly_df)
    post_monthly_df = monthly_data_processing(monthly_df)
    data_dir=r'D:\Project\3_项目\2_气候评估和气候可行性论证\qhkxxlz\Report\report\Module02'

    basic_pre_yearly, basic_pre_accum, report_path = basic_pre_statistics(post_yearly_df, post_monthly_df,data_dir)
