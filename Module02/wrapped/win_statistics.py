import logging
import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.get_local_data import get_local_data
from Utils.data_processing import wind_direction_to_symbol


# 统计更新：累年各月表格-风速要素-最多风向/最多风向对应的最大频率所在的行，
# 最后一列(全年)对应的数值替换为 年最多风向及对应的频率


def basic_win_statistics(win_day, win_month):
    '''
    风速要素，历年和累年各月统计，
    使用天擎上的年数据和月数据，要素名称为天擎上默认的名称
    年值要素：[WIN_S_2mi_Avg,WIN_S_Max,WIN_D_S_Max_C,V11042_067,WIN_S_Inst_Max,WIN_D_INST_Max_C,
              WIN_S_INST_Max_ODate_C,WIN_D_Max_C,WIN_D_Max_Freq]
    月值要素：['Station_Id_C', 'Station_Name', 'Year', 'Mon', 'WIN_S_2mi_Avg', 'WIN_S_Max', 
              'WIN_D_S_Max_C', 'WIN_S_Max_ODay_C', 'WIN_S_Inst_Max', 'WIN_D_INST_Max_C', 
              'WIN_S_INST_Max_ODay_C', 'WIN_D_Max_C', 'WIN_D_Max_Freq']
    return: dataframe
    '''
    try:
        # A.历年统计 天擎年值序列直接输出
        # 1. 年平均风速
        avg_wind = win_day['WIN_S_2mi_Avg'].resample('1A').mean().round(1)
        avg_wind.index = avg_wind.index.year

        # 2&3&4. 年最大风速及其日期和风向
        max_wind_dates = win_day.dropna(subset=['WIN_S_Max']).groupby(lambda x: x.year)['WIN_S_Max'].idxmax()
        max_wind_info = win_day.loc[max_wind_dates[max_wind_dates.notna()], ['WIN_S_Max', 'WIN_D_S_Max']]
        max_wind_info['最大风速出现日期'] = max_wind_info.index.strftime('%m月%d日')
        max_wind_info = max_wind_info[['WIN_S_Max', '最大风速出现日期', 'WIN_D_S_Max']]
        max_wind_info.index = max_wind_info.index.year

        # 5&6&7. 年极大风速及其日期和风向
        # 首先处理缺测值
        valid_data = win_day[win_day['WIN_S_Inst_Max'].notna()]
        max_inst_dates = valid_data.groupby(valid_data.index.year)['WIN_S_Inst_Max'].idxmax()
        max_inst_info = win_day.loc[max_inst_dates, ['WIN_S_Inst_Max', 'WIN_D_INST_Max']]
        max_inst_info['极大风速出现日期'] = max_inst_info.index.strftime('%m月%d日')
        max_inst_info = max_inst_info[['WIN_S_Inst_Max', 'WIN_D_INST_Max', '极大风速出现日期']]
        max_inst_info.index = max_inst_info.index.year

        # 8&9. 计算年最多风向及其频率
        def get_most_freq_direction(group):
            direction_counts = group['WIN_D_S_Max'].value_counts()
            if len(direction_counts) == 0:  # 处理全部为空值的情况
                return pd.Series({'最多风向': np.nan, '最多风向频率': np.nan})
            
            most_freq_dir = direction_counts.index[0]
            freq_percentage = (direction_counts.iloc[0] / len(group) * 100).round(1)
            return pd.Series({'最多风向': most_freq_dir, '最多风向频率': freq_percentage})

        wind_direction_stats = win_day.groupby(win_day.index.year).apply(get_most_freq_direction)
        
        # concat
        basic_win_yearly = pd.concat([avg_wind,max_wind_info,max_inst_info,wind_direction_stats], axis=1)
        basic_win_yearly.insert(loc=0, column='年份', value=basic_win_yearly.index)
        basic_win_yearly.columns = ['年份', '平均风速(m/s)', '最大风速(m/s)', '最大风速出现日期', '最大风速的风向', '极大风速(m/s)', '极大风速出现日期', '极大风速的风向', '最多风向', '最多风向出现频率%']
        basic_win_yearly.reset_index(drop=True, inplace=True)

        # 新增
        # 获取年最多风向及对应的频率 后续累年各月统计会用到
        directions = basic_win_yearly['最多风向'].value_counts().to_frame().reset_index()  #统计累年同月份里面的风向频数
        directions = directions[directions['index'] != 'nan']  # 删除nan的value_counts
        directions.columns = ['wind_dircetion', 'counts']

        max_direction = directions.iloc[0, 0]  # 最多风向
        max_direction_counts = directions.iloc[0, 1]  # 最多风向的统计次数
        max_direction_freq = basic_win_yearly[basic_win_yearly['最多风向'] == max_direction]['最多风向出现频率%'].max()  # 累年同月份中，最多风向所对应的最大频率
        # float去掉小数点
        max_direction_freq = str(int(max_direction_freq))
        # 判断是否有相同频数，但不同的风向，如果有生成结果如：NNW,SW
        for j in range(1, len(directions)):
            if directions.iloc[j, 1] == max_direction_counts:
                temp_direction = directions.iloc[j, 0]  # 风向
                temp_direction_freq = basic_win_yearly[basic_win_yearly['最多风向'] == temp_direction]['最多风向出现频率%'].max()

                max_direction += ',' + temp_direction
                # float去掉小数点再累加
                max_direction_freq += ',' + str(int(temp_direction_freq))

        vals_yearly = [max_direction, max_direction_freq]

        # 判断
        tmp = basic_win_yearly.dropna(axis=1, how='all')
        if len(tmp.columns) == 1:  # 如果只有年份一列，说明全部没有数据
            basic_win_yearly = None
        else:
            basic_win_yearly = basic_win_yearly.round(1).to_dict(orient='records')

    except Exception as e:
        logging.exception(e)
        basic_win_yearly = None
        vals_yearly = [np.nan, np.nan]

    finally:
        try:
            # B.累年各月统计
            win_mean = win_month['WIN_S_2mi_Avg'].to_frame()
            win_max_part1 = win_month['WIN_S_2mi_Avg'].to_frame()
            win_max_part2 = win_month[['WIN_D_Max_C', 'WIN_D_Max_Freq']]  # 最多风向及频率
            win_max_part3 = win_month[['WIN_S_Max', 'WIN_D_S_Max_C', 'WIN_S_Max_ODay_C', 'Year', 'Mon']]
            win_max_part4 = win_month[['WIN_S_Inst_Max', 'WIN_D_INST_Max_C', 'WIN_S_INST_Max_ODay_C', 'Year', 'Mon']]

            mean_win_accum = []
            max_win_accum_part1 = []
            max_win_accum_part2 = []
            max_win_accum_part3 = []
            max_win_accum_part4 = []

            def sample(x):
                x = str(x)
                if x[-1] == 'T':
                    x = int(x[:-1])
                elif x[-1] == 'N':
                    x = int(x[:-1])
                elif x[-1] == 'G':
                    x = int(x[:-1])
                else:
                    x = 1
                return x

            for i in range(1, 13):
                # mean
                month_i_mean = win_mean[win_mean.index.month == i].mean().round(1).to_frame()
                mean_win_accum.append(month_i_mean)

                # max_part1
                month_i_max_part1 = win_max_part1[win_max_part1.index.month == i].max().to_frame()
                max_win_accum_part1.append(month_i_max_part1)

                # max_part2
                month_i_max_part2 = win_max_part2[win_max_part2.index.month == i]
                directions = month_i_max_part2['WIN_D_Max_C'].value_counts().to_frame().reset_index()  #统计累年同月份里面的风向频数
                directions = directions[directions['index'] != 'nan']  # 删除nan的value_counts
                directions.columns = ['wind_dircetion', 'counts']

                max_direction = directions.iloc[0, 0]  # 最多风向
                max_direction_counts = directions.iloc[0, 1]  # 最多风向的统计次数
                max_direction_freq = month_i_max_part2[month_i_max_part2['WIN_D_Max_C'] == max_direction]['WIN_D_Max_Freq'].max()  # 累年同月份中，最多风向所对应的最大频率
                max_direction_freq = str(int(max_direction_freq))

                # 判断是否有相同频数，但不同的风向，如果有生成结果如：NNW,SW
                for j in range(1, len(directions)):
                    if directions.iloc[j, 1] == max_direction_counts:
                        temp_direction = directions.iloc[j, 0]  # 风向
                        temp_direction_freq = month_i_max_part2[month_i_max_part2['WIN_D_Max_C'] == temp_direction]['WIN_D_Max_Freq'].max()  # 风向对应的最大频率

                        max_direction += ',' + temp_direction
                        max_direction_freq += ',' + str(int(temp_direction_freq))

                array = np.array([max_direction, max_direction_freq]).reshape(1, -1)
                max_df = pd.DataFrame(array, columns=month_i_max_part2.columns, index=[month_i_max_part2.index[0]])
                max_win_accum_part2.append(max_df)

                # max_part3
                month_i_max_part3 = win_max_part3[win_max_part3.index.month == i]
                month_i_max_part3 = month_i_max_part3[month_i_max_part3['WIN_S_Max'] == month_i_max_part3['WIN_S_Max'].max()]

                # 针对多个时间点数值相同的情况
                if len(month_i_max_part3) > 1:
                    win_data = month_i_max_part3.iloc[0, 0]  # columns: ['WIN_S_Max','WIN_D_S_Max_C','WIN_S_Max_ODay_C','Year','Mon']
                    win_d = str(len(month_i_max_part3)) + 'G'
                    occur_day = str(month_i_max_part3['WIN_S_Max_ODay_C'].apply(sample).sum()) + 'T'
                    occur_year = str(len(month_i_max_part3)) + 'N'
                    occur_month = month_i_max_part3.iloc[0, 4]

                    array = np.array([win_data, win_d, occur_day, occur_year, occur_month]).reshape(1, -1)
                    max_df = pd.DataFrame(array, columns=month_i_max_part3.columns, index=[month_i_max_part3.index[0]])

                else:
                    max_df = month_i_max_part3

                max_win_accum_part3.append(max_df)

                # max_part4
                month_i_max_part4 = win_max_part4[win_max_part4.index.month == i]
                month_i_max_part4 = month_i_max_part4[month_i_max_part4['WIN_S_Inst_Max'] == month_i_max_part4['WIN_S_Inst_Max'].max()]

                # 针对多个时间点数值相同的情况
                if len(month_i_max_part4) > 1:
                    win_data = month_i_max_part4.iloc[0, 0]  # columns: ['WIN_S_Inst_Max','WIN_D_INST_Max_C','WIN_S_INST_Max_ODay_C','Year','Mon']
                    win_d = str(len(month_i_max_part4)) + 'G'
                    occur_day = str(month_i_max_part4['WIN_S_INST_Max_ODay_C'].apply(sample).sum()) + 'T'
                    occur_year = str(len(month_i_max_part4)) + 'N'
                    occur_month = month_i_max_part4.iloc[0, 4]

                    array = np.array([win_data, win_d, occur_day, occur_year, occur_month]).reshape(1, -1)
                    max_df = pd.DataFrame(array, columns=month_i_max_part4.columns, index=[month_i_max_part4.index[0]])

                else:
                    max_df = month_i_max_part4

                max_win_accum_part4.append(max_df)

            ####################################################
            # 结果合成为DateFrame
            # mean
            mean_win_accum = pd.concat(mean_win_accum, axis=1, ignore_index=True)
            mean_win_accum.index = ['平均2分钟风速(m/s)']
            mean_win_accum['全年'] = mean_win_accum.iloc[:, :].mean(axis=1).round(1)

            # max_part1
            max_win_accum_part1 = pd.concat(max_win_accum_part1, axis=1, ignore_index=True)
            max_win_accum_part1.index = ['最大2分钟风速(m/s)']
            max_win_accum_part1['全年'] = max_win_accum_part1.iloc[:, :].max(axis=1)

            # max_part2
            max_win_accum_part2 = pd.concat(max_win_accum_part2, axis=0, ignore_index=True)
            # most_directions = max_win_accum_part2['WIN_D_Max_C'].value_counts().to_frame().reset_index()
            # most_directions = most_directions[most_directions['index'] != 'nan']  # 删除nan的value_counts
            # most_directions.columns = ['wind_dircetion', 'counts']

            # first_direction = most_directions.iloc[0, 0]  # 最多风向
            # first_direction_counts = most_directions.iloc[0, 1]  # 最多风向的统计次数
            # first_direction_freq = max_win_accum_part2[max_win_accum_part2['WIN_D_Max_C'] == first_direction]['WIN_D_Max_Freq'].max()

            # for k in range(1, len(most_directions)):
            #     if most_directions.iloc[k, 1] == first_direction_counts:
            #         tmp_direction = most_directions.iloc[k, 0]  # 风向
            #         tmp_direction_freq = max_win_accum_part2[max_win_accum_part2['WIN_D_Max_C'] == tmp_direction]['WIN_D_Max_Freq'].max()  # 风向对应的最大频率

            #         first_direction += ',' + tmp_direction
            #         first_direction_freq += ',' + str(tmp_direction_freq)

            # values_list = [first_direction, first_direction_freq]
            max_win_accum_part2 = max_win_accum_part2.T
            max_win_accum_part2.index = ['最多风向', '最多风向对应的最大频率%']
            # max_win_accum_part2['全年'] = values_list
            max_win_accum_part2['全年'] = vals_yearly  # 新增link到前面

            # max_part3
            max_win_accum_part3 = pd.concat(max_win_accum_part3, axis=0, ignore_index=True)
            max_win_accum_part3['WIN_S_Max'] = max_win_accum_part3['WIN_S_Max'].astype(float)
            max_row = max_win_accum_part3[max_win_accum_part3['WIN_S_Max'] == max_win_accum_part3['WIN_S_Max'].max()].reset_index(drop=True)

            if len(max_row) == 1:
                win = max_row.loc[0, 'WIN_S_Max']
                win_d = max_row.loc[0, 'WIN_D_S_Max_C']
                date = max_row['Mon'].map(str) + '-' + max_row['WIN_S_Max_ODay_C'].map(str)
                year = max_row.loc[0, 'Year']
                values_list = [win, win_d, date.values[0], year]

            elif len(max_row) > 1:
                win = max_row.loc[0, 'WIN_S_Max']
                win_d = str(max_row['WIN_D_S_Max_C'].apply(sample).sum()) + 'G'
                date = str(len(max_row)) + 'T'
                year = str(max_row['Year'].apply(sample).sum()) + 'N'
                values_list = [win, win_d, date, year]

            max_win_accum_part3.drop('Mon', axis=1, inplace=True)  # 删除月份列
            max_win_accum_part3 = max_win_accum_part3.T
            max_win_accum_part3.index = ['最大风速(m/s)', '最大风速相应风向', '最大风速出现日期', '最大风速出现年份']
            max_win_accum_part3['全年'] = values_list

            # max_part3
            max_win_accum_part4 = pd.concat(max_win_accum_part4, axis=0, ignore_index=True)
            max_win_accum_part4['WIN_S_Inst_Max'] = max_win_accum_part4['WIN_S_Inst_Max'].astype(float)
            max_row = max_win_accum_part4[max_win_accum_part4['WIN_S_Inst_Max'] == max_win_accum_part4['WIN_S_Inst_Max'].max()].reset_index(drop=True)

            if len(max_row) == 1:
                win = max_row.loc[0, 'WIN_S_Inst_Max']
                win_d = max_row.loc[0, 'WIN_D_INST_Max_C']
                date = max_row['Mon'].map(str) + '-' + max_row['WIN_S_INST_Max_ODay_C'].map(str)
                year = max_row.loc[0, 'Year']
                values_list = [win, win_d, date.values[0], year]

            elif len(max_row) > 1:
                win = max_row.loc[0, 'WIN_S_Inst_Max']
                win_d = str(max_row['WIN_D_INST_Max_C'].apply(sample).sum()) + 'G'
                date = str(len(max_row)) + 'T'
                year = str(max_row['Year'].apply(sample).sum()) + 'N'
                values_list = [win, win_d, date, year]

            max_win_accum_part4.drop('Mon', axis=1, inplace=True)  # 删除月份列
            max_win_accum_part4 = max_win_accum_part4.T
            max_win_accum_part4.index = ['极大风速(m/s)', '极大风速相应风向', '极大风速出现日期', '极大风速出现年份']
            max_win_accum_part4['全年'] = values_list

            # 计算结果concat在一起
            basic_win_accum = pd.concat([mean_win_accum, max_win_accum_part1, max_win_accum_part2, max_win_accum_part3, max_win_accum_part4], axis=0)

            # 增加月份
            month_list = [str(i) + '月' for i in range(1, 13)]
            month_list.append('年')
            basic_win_accum.columns = month_list
            basic_win_accum.reset_index(inplace=True)
            basic_win_accum.rename(columns={'index': '要素'}, inplace=True)

            tmp = basic_win_accum.dropna(axis=1, how='all')
            if len(tmp.columns) == 1:
                basic_win_accum = None
            else:
                basic_win_accum = basic_win_accum.to_dict(orient='records')

        except Exception as e:
            logging.exception(e)
            basic_win_accum = None

        finally:
            return basic_win_yearly, basic_win_accum


if __name__ == '__main__':
    daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    monthly_df = pd.read_csv(cfg.FILES.QH_DATA_MONTH, low_memory=False)
    sta_ids = '52866'
    years = '2000,2020'

    daily_elements = 'WIN_S_2mi_Avg,WIN_S_Max,WIN_D_S_Max,WIN_S_Inst_Max,'
    day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements[:-1]).split(',')
    post_daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')
    post_daily_df['WIN_D_INST_Max'] = np.random.randint(0, 361, size=len(post_daily_df)) # 极大风速风向
    post_daily_df['WIN_D_INST_Max'] = post_daily_df['WIN_D_INST_Max'].astype(str).apply(wind_direction_to_symbol)

    monthly_elements = 'WIN_S_2mi_Avg,WIN_S_Max,WIN_D_S_Max_C,WIN_S_Max_ODay_C,WIN_S_Inst_Max,WIN_D_INST_Max_C,WIN_S_INST_Max_ODay_C,WIN_D_Max_C,WIN_D_Max_Freq,WIN_NNE_Freq,WIN_NE_Freq,WIN_ENE_Freq,WIN_E_Freq,WIN_ESE_Freq,WIN_SE_Freq,WIN_SSE_Freq,WIN_S_Freq,WIN_SSW_Freq,WIN_SW_Freq,WIN_WSW_Freq,WIN_W_Freq,WIN_WNW_Freq,WIN_NW_Freq,WIN_NNW_Freq,WIN_N_Freq,WIN_C_Freq,WIN_S_Avg_NNE,WIN_S_Avg_NE,WIN_S_Avg_ENE,WIN_S_Avg_E,WIN_S_Avg_ESE,WIN_S_Avg_SE,WIN_S_Avg_SSE,WIN_S_Avg_S,WIN_S_Avg_SSW,WIN_S_Avg_SW,WIN_S_Avg_WSW,WIN_S_Avg__W,WIN_S_Avg_WNW,WIN_S_Avg_NW,WIN_S_Avg_NNW,WIN_S_Avg__N,'
    month_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,' + monthly_elements[:-1]).split(',')
    post_monthly_df = get_local_data(monthly_df, sta_ids, month_eles, years, 'Month')
    
    basic_win_yearly, basic_win_accum = basic_win_statistics(post_daily_df, post_monthly_df)