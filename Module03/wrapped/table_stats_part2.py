import logging
import numpy as np
import pandas as pd
from Utils.data_processing import daily_data_processing
from Utils.get_local_data import get_local_data

def table_stats_part2(data_df, element_name):
    '''
    用于各个天气现象要素的统计，第二部分，表4-5
    日数据源组合日要素，如果某一列要素全部nan，则报错
    多个站点同时统计，适用并需要统计的要素如下：
    
    日数据要素 都跨年统计
    雪 Snow
    霜 Frost 多一列要素统计
    积雪 GSS
    结冰 ICE
    雷暴 Thund 不跨年
    最低气温小于等于0 TEM_Min 跨年
    地面最低气温小于等于0 GST_Min 跨年
    
    输出的表格为：
    table4: 各个站点历年天气现象的日数、初日、终日、间日等
    table5: 各个站点累年天气现象的日数、初日、终日、间日等
    '''

    def table4_stats(x):
        '''
        统计table4的pandas apply函数
        '''
        x = x[element_name]
        start_year = x.index.year[0]
        num_years = len(x.index.year.unique())
        all_row = []

        if element_name == 'Thund':
            total_years = num_years
        else:
            total_years = num_years - 1  # 应为跨年，所以少一年

        for i in range(total_years):
            try:
                year = start_year + i
    
                if element_name == 'Thund':
                    start_date = str(year) + '0101'
                    meteo_year_idx = pd.bdate_range(start=start_date, periods=12, freq='M').strftime('%Y-%m').tolist()  # 每年1月到每年12月
                    #print(meteo_year_idx)
                    #print('-------------')
    
                else:
                    start_date = str(year) + '0701'
                    meteo_year_idx = pd.bdate_range(start=start_date, periods=12, freq='M').strftime('%Y-%m').tolist()  # 每年7月到次年6月
                    #print(meteo_year_idx)
                    #print('-------------')
    
                # 得到这个气象年的数据
                for j in range(len(meteo_year_idx)):
                    data = x.loc[meteo_year_idx[j]]
    
                    if j == 0:
                        all_data = data
                    else:
                        all_data = pd.concat([all_data, data], axis=0)
    
                # 接下来获取天气现象日数、初日时间、终日时间、间日数
                all_data = all_data.to_frame()
                num_days = len(all_data[all_data[element_name] == 1])  # 天气现象日数
    
                if num_days == 0:
                    start_day = np.nan
                    end_day = np.nan
                    during_day = 0
    
                else:
                    start_day = all_data[all_data[element_name] == 1].index[0]  # 初日时间
                    end_day = all_data[all_data[element_name] == 1].index[-1]  # 终日时间
                    during_day = (end_day - start_day).days  # 间日数
    
                if element_name == 'Frost':  # 如果是霜要素，增加无霜期
                    year = all_data.index.year[0]
    
                    if year % 4 == 0 and year % 100 != 0 or year % 400 == 0:  # 判断平年、闰年
                        days = 366
                    else:
                        days = 365
    
                    no_frost_day = days - during_day  # 无霜期日数
    
                    try:
                        values = np.array([num_days, start_day.strftime('%Y-%m-%d'), end_day.strftime('%Y-%m-%d'), during_day, no_frost_day]).T
                    except:
                        values = np.array([num_days, start_day, end_day, during_day, no_frost_day]).T
    
                else:  # 如果不是霜要素，就四个输出量
                    try:
                        values = np.array([num_days, start_day.strftime('%Y-%m-%d'), end_day.strftime('%Y-%m-%d'), during_day]).T
                    except:
                        values = np.array([num_days, start_day, end_day, during_day]).T
    
                row = pd.DataFrame(values)
                all_row.append(row)

            except Exception as e:
                # 如果出现错误，打印错误信息，并将该年的数据设置为NaN
                print(f"Error in year {year}: {e}")
                nan_row = pd.DataFrame([[np.nan, np.nan, np.nan, np.nan, np.nan] if element_name == 'Frost' else [np.nan, np.nan, np.nan, np.nan]])
                all_row.append(nan_row)
        
        all_row = pd.concat(all_row, axis=1)

        return all_row

    try:
        # 1.判断某个站的某个要素是不是全是nan，如果是，就删掉该站
        station_name = data_df['Station_Name'].unique().tolist()
        nan_list = []  # 要素全是nan的站点列表

        for name in station_name:
            tmp = data_df.loc[data_df['Station_Name'] == name, element_name]
            missing_rate = (tmp.isnull().sum()) / tmp.shape[0]

            if missing_rate == 1:
                nan_list.append(name)

        data_df = data_df[~data_df['Station_Name'].isin(nan_list)]

        # 2.第四个表的统计 历年初终日
        table4 = data_df.groupby('Station_Name').apply(table4_stats).T

        # # 检查列是否是多重索引
        # if isinstance(table4.columns, pd.MultiIndex):
        #     table4.columns = table4.columns.get_level_values(0)
        # 重新设置列名
        if element_name == 'Frost':
            columns = ['日数', '初日', '终日', '间日', '无霜日数']
        else:
            columns = ['日数', '初日', '终日', '间日']

        label0 = table4.columns.get_level_values(0)
        label1 = columns * len(station_name)
        new_columns = [j + '(' + i + ')' for i, j in zip(label0, label1)]
        table4.columns = new_columns

        table4.reset_index(inplace=True,drop=True)
        # 获取起始年份
        begin_year = data_df.index.year[0]
        last_year = data_df.index.year[-1]

        # 重新设置行名
        if element_name == 'Thund':
            table4.insert(loc=0, column='时间段', value=data_df.index.year.unique())

        else:
            time_index = list(zip(range(begin_year, last_year), range(begin_year + 1, last_year + 1)))
            new_index = [str(i) + '.7' + '-' + str(j) + '.6' for i, j in time_index]
            table4 = table4.loc[np.arange(len(new_index))]

            table4.insert(loc=0, column='时间段', value=new_index)

        table4.reset_index(drop=True, inplace=True)
        table4 = table4.round(1).to_dict(orient='records')

        # 3.第五个表的统计 累年初终日
        temp_table = pd.DataFrame(table4).copy()
        stats_years = temp_table['时间段'].tolist()  # 统计的时间段，自动区分是否跨年
        station_name_new_order = label0.unique()  # 获取新的站点名称顺序 重要

        if element_name == 'Frost':
            for num, i in enumerate(range(1, temp_table.shape[1], 5)):
                st_name = station_name_new_order[num]  # 此时的站点名称
                df = temp_table.iloc[:, i:i + 5]
                df_cp = df.copy()
                df_cp['year'] = list(range(begin_year, last_year))
                df_cp['stats_years'] = stats_years

                # 计算日期平均 年份都固定位1999和2000年(一平年、一润年)
                # 先删除日期为nan的行，注意要reset_index
                df_cp = df_cp.dropna()
                df_cp.reset_index(drop=True, inplace=True)

                # 增加替换了年份的列，以便于计算平均和提取对应的真实数据
                df_cp['start_year_trans'] = df_cp.iloc[:, 1].apply(lambda x: '1999' + x[4:]
                                                                    if int(x.split('-')[1]) >= 7 else '2000' + x[4:])  # 初日
                df_cp['end_year_trans'] = df_cp.iloc[:, 2].apply(lambda x: '1999' + x[4:] if int(x.split('-')[1]) >= 7 else '2000' + x[4:])  # 终日
                df_cp['start_year_trans'] = pd.to_datetime(df_cp['start_year_trans'])
                df_cp['end_year_trans'] = pd.to_datetime(df_cp['end_year_trans'])

                # 平均
                mean_start_day = df_cp.iloc[:, -2].mean().strftime("%m-%d")
                mean_end_day = df_cp.iloc[:, -1].mean().strftime("%m-%d")
                mean_during_day = round(df_cp.iloc[:, 3].astype(float).mean(), 1)
                mean_no_frost_day = round(df_cp.iloc[:, 4].astype(float).mean(), 1)

                # 最早(最小/最少)
                min_start_day_idx = df_cp.iloc[:, -2].idxmin()
                min_start_day = df_cp.iloc[min_start_day_idx, 1]
                min_end_day_idx = df_cp.iloc[:, -1].idxmin()
                min_end_day = df_cp.iloc[min_end_day_idx, 2]

                min_during_day_idx = df_cp.iloc[:, 3].astype(float).idxmin()
                min_during_day = df_cp.iloc[min_during_day_idx, 3]
                min_during_day_year = df_cp.iloc[min_during_day_idx, -3]  # 间日对应的统计年份段

                min_no_frost_day = df_cp.iloc[:, 4].min()

                # 最晚(最大/最多)
                max_start_day_idx = df_cp.iloc[:, -2].idxmax()
                max_start_day = df_cp.iloc[max_start_day_idx, 1]
                max_end_day_idx = df_cp.iloc[:, -1].idxmax()
                max_end_day = df_cp.iloc[max_end_day_idx, 2]

                max_during_day_idx = df_cp.iloc[:, 3].astype(float).idxmax()
                max_during_day = df_cp.iloc[max_during_day_idx, 3]
                max_during_day_year = df_cp.iloc[max_during_day_idx, -3]  # 间日对应的统计年份段

                max_no_frost_day = df_cp.iloc[:, 4].max()

                # 组合结果
                min_during_day = str(min_during_day) + '(' + str(min_during_day_year) + ')'
                max_during_day = str(max_during_day) + '(' + str(max_during_day_year) + ')'

                array = np.array([[mean_start_day, mean_end_day, mean_during_day, mean_no_frost_day],
                                    [min_start_day, min_end_day, min_during_day, min_no_frost_day],
                                    [max_start_day, max_end_day, max_during_day, max_no_frost_day]],
                                    dtype=object)

                result = pd.DataFrame(array)
                columns = ['初日', '终日', '间日数', '无霜期日数']
                result.columns = [col + '(' + st_name + ')' for col in columns]

                if num == 0:
                    table5 = result
                else:
                    table5 = pd.concat([table5, result], axis=1)

            table5.insert(loc=0, column='统计', value=['平均', '最早(少)', '最晚(多)'])
            table5 = table5.round(1).to_dict(orient='records')

        else:
            for num, i in enumerate(range(1, temp_table.shape[1], 4)):
                st_name = station_name_new_order[num]  # 此时的站点名称
                df = temp_table.iloc[:, i:i + 4]
                df_cp = df.copy()

                if element_name == 'Thund':  # 因为不跨年统计，所以多一年的统计结果
                    df_cp['year'] = list(range(begin_year, last_year + 1))

                else:
                    df_cp['year'] = list(range(begin_year, last_year))

                df_cp['stats_years'] = stats_years

                # 计算日期平均 年份都固定位1999和2000年(一平年、一润年) # 1999年里面出现2.29号时，会报错，这里后续需要改进
                # 先删除日期为nan的行
                df_cp = df_cp.dropna()
                df_cp.reset_index(drop=True, inplace=True)

                # 增加替换了年份的列，以便于计算平均和提取对应的真实数据
                df_cp['start_year_trans'] = df_cp.iloc[:, 1].apply(lambda x: '1999' + x[4:]
                                                                    if int(x.split('-')[1]) >= 7 else '2000' + x[4:])  # 初日
                df_cp['end_year_trans'] = df_cp.iloc[:, 2].apply(lambda x: '1999' + x[4:] if int(x.split('-')[1]) >= 7 else '2000' + x[4:])  # 终日
                df_cp['start_year_trans'] = pd.to_datetime(df_cp['start_year_trans'])
                df_cp['end_year_trans'] = pd.to_datetime(df_cp['end_year_trans'])

                # 平均
                mean_start_day = df_cp.iloc[:, -2].mean().strftime("%m-%d")
                mean_end_day = df_cp.iloc[:, -1].mean().strftime("%m-%d")
                mean_during_day = round(df_cp.iloc[:, 3].astype(float).mean(), 1)

                # 最早(最小/最少)
                min_start_day_idx = df_cp.iloc[:, -2].idxmin()
                min_start_day = df_cp.iloc[min_start_day_idx, 1]
                min_end_day_idx = df_cp.iloc[:, -1].idxmin()
                min_end_day = df_cp.iloc[min_end_day_idx, 2]

                min_during_day_idx = df_cp.iloc[:, 3].astype(float).idxmin()
                min_during_day = df_cp.iloc[min_during_day_idx, 3]
                min_during_day_year = df_cp.iloc[min_during_day_idx, -3]  # 间日对应的统计年份段

                # 最晚(最大/最多)
                max_start_day_idx = df_cp.iloc[:, -2].idxmax()
                max_start_day = df_cp.iloc[max_start_day_idx, 1]
                max_end_day_idx = df_cp.iloc[:, -1].idxmax()
                max_end_day = df_cp.iloc[max_end_day_idx, 2]

                max_during_day_idx = df_cp.iloc[:, 3].astype(float).idxmax()
                max_during_day = df_cp.iloc[max_during_day_idx, 3]
                max_during_day_year = df_cp.iloc[max_during_day_idx, -3]  # 间日对应的统计年份段

                # 组合结果
                min_during_day = str(min_during_day) + '(' + str(min_during_day_year) + ')'
                max_during_day = str(max_during_day) + '(' + str(max_during_day_year) + ')'

                array = np.array([[mean_start_day, mean_end_day, mean_during_day], [min_start_day, min_end_day, min_during_day],
                                    [max_start_day, max_end_day, max_during_day]],
                                    dtype=object)

                result = pd.DataFrame(array)
                columns = ['初日', '终日', '间日数']
                result.columns = [col + '(' + st_name + ')' for col in columns]

                if num == 0:
                    table5 = result
                else:
                    table5 = pd.concat([table5, result], axis=1)

            table5.insert(loc=0, column='统计', value=['平均', '最早(少)', '最晚(多)'])
            table5 = table5.round(1).to_dict(orient='records')

    except Exception as e:
        table4 = None
        table5 = None

    return table4, table5


if __name__ == '__main__':
    day_eles = ('Station_Id_C,Station_Name,Lat,Lon,Datetime,Year,Mon,Day,' + 'Frost').split(',')
    path = r'C:\Users\MJY\Desktop\qhkxxlz\app\Files\test_data\qh_day.csv'
    df = pd.read_csv(path)
    years = '1950,2020'
    sta_ids = '52866,52862,56067'
    day_data = get_local_data(df, sta_ids, day_eles, years, 'Day')
    table4, table5 = table_stats_part2(day_data, 'Frost')

