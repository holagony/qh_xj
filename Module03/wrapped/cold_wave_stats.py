import numpy as np
import pandas as pd
from Utils.data_processing import daily_data_processing, hourly_data_processing
from Utils.get_local_data import get_local_data
import logging


def generate_group_num(values, diff=1):
    group_ids = []
    group_id = 0
    last_v = 0

    for value in values:
        if value - last_v > diff:
            group_id += 1

        group_ids.append(group_id)
        last_v = value

    return group_ids


def get_cold_wave_idxs(df, cold_wave_level=(8, 10, 12)):
    cold_wave_idxs = set()
    ids = df.index[df['TEM_Min'].diff(-1) >= cold_wave_level[0]].values
    cold_wave_idxs.update(ids)
    cold_wave_idxs.update(ids + 1)

    ids = df.index[df['TEM_Min'].diff(-2) >= cold_wave_level[1]].values
    cold_wave_idxs.update(ids)
    cold_wave_idxs.update(ids + 1)
    cold_wave_idxs.update(ids + 2)

    ids = df.index[df['TEM_Min'].diff(-3) >= cold_wave_level[2]].values
    cold_wave_idxs.update(ids)
    cold_wave_idxs.update(ids + 1)
    cold_wave_idxs.update(ids + 2)
    cold_wave_idxs.update(ids + 3)

    return sorted(cold_wave_idxs)


def cold_wave_statistics(data_df):
    '''
    table1.多站点寒潮过程统计表
    table2.多站点寒潮大风统计表
    table3.多站寒潮大风风向频数统计表
    需要的要素：'TEM_Avg','TEM_Min','WIN_S_Max','WIN_D_S_Max'
    
    如果某个站缺少要素，导致不能统计，则输出结果的三个表里面没有这个站
    如果所有站都缺少要素，导致不能统计，则输出None
    '''

    def sample_row(x):
        '''
        table2寒潮大风的pandas apply函数
        '''
        x = x.to_frame().T
        name = x.iloc[0, 0]  # 站名
        start_date = x.iloc[0, 1]
        end_date = x.iloc[0, 2]

        data = sample_data[sample_data['Station_Name'] == name]
        rows = data[start_date:end_date]
        rows = rows[(rows['WIN_S_Max'] > 10.8) & (rows['WIN_D_S_Max'].isin(['WNW', 'NW', 'NNW', 'N', 'NNE', 'NE', 'ENE']))]

        if len(rows) != 0:
            rows = rows[rows['WIN_S_Max'] == rows['WIN_S_Max'].max()]  # 取风速最大的一行
            rows = rows.head(1)
            rows['降温幅度'] = x.loc[:, '降温幅度'].values
            rows['影响前日期'] = str(x.loc[:, '开始日期'].values[0])[5:]
            rows['影响前平均气温'] = str(x.loc[:, '开始日平均气温'].values[0])
            rows['影响前最低气温'] = str(x.loc[:, '开始日最低气温'].values[0])
            rows['过程最低气温'] = x.loc[:, '过程最低气温'].values
            rows['过程平均气温'] = x.loc[:, '过程平均气温'].values
            return rows

    def sample(x):
        '''
        table3的pandas apply函数
        '''
        t = x['当日风向'].value_counts().to_frame()
        t['频数'] = (t['当日风向'] / t['当日风向'].sum()).round(3)
        return t

    try:
        # 寒潮/寒潮大风所需要素
        ######################################################
        # 新增读取小时数据，转化为日数据
        # def sample_station(x):
        #     tem_avg = x['TEM'].resample('1D').mean().round(1).to_frame()
        #     tem_min = x['TEM'].resample('1D').min().to_frame()
        #     ws = x['WIN_S_Max'].resample('1D').max().to_frame()

        #     def sample_wd(x):
        #         wd = x[x['WIN_S_Max']==x['WIN_S_Max'].max()]['WIN_D_S_Max'].to_frame()
        #         return wd

        #     wd = x.resample('1D').apply(sample_wd)
        #     wd.reset_index(level=1,drop=True,inplace=True)
        #     wd = wd[~wd.index.duplicated(keep='first')]

        #     data = pd.concat([tem_avg,tem_min,ws,wd],axis=1)

        #     return data

        # df1 = data_df.groupby('Station_Name').apply(sample_station)
        # df1.sort_index(inplace=True)
        # df1.reset_index(level=0,inplace=True)
        # df1.columns = ['Station_Name', 'TEM_Avg', 'TEM_Min', 'WIN_S_Max', 'WIN_D_S_Max']
        # df1.insert(loc=1, column='Year', value=df1.index.year)
        # df1.insert(loc=2, column='Mon', value=df1.index.month)
        # df1.insert(loc=3, column='Day', value=df1.index.day)
        # sample_data = df1

        sample_data = data_df[['Station_Id_C', 'Station_Name', 'Year', 'Mon', 'Day', 'TEM_Avg', 'TEM_Min', 'WIN_S_Max', 'WIN_D_S_Max']]
        cold_wave_dict = {'cold_wave_temperature_diffs': (8, 10, 12), 'min_temperature_limit': 4, 'cold_wave_type': '寒潮'}

        # table1 寒潮过程
        cold_wave_result = []
        for number, tmp in sample_data.groupby('Station_Name'):
            tmp = tmp.reset_index()
            cold_wave_idxs = get_cold_wave_idxs(tmp, cold_wave_dict['cold_wave_temperature_diffs'])

            if len(cold_wave_idxs) < 2:
                continue

            for i, cold_wave_idx_serial in pd.Series(cold_wave_idxs).groupby(generate_group_num(cold_wave_idxs)):
                cold_wave_idx_serial = cold_wave_idx_serial.values
                start_id, end_id = cold_wave_idx_serial[0], cold_wave_idx_serial[-1]

                # 假如最低温度小于指定度数，则说明满足全部条件
                if tmp.loc[end_id, 'TEM_Min'] <= cold_wave_dict['min_temperature_limit']:
                    cold_wave_result.append((
                        number,
                        tmp.loc[start_id, 'index'], # 原来是Datetime
                        tmp.loc[end_id, 'index'], # 原来是Datetime
                        tmp.loc[start_id, 'TEM_Min'],
                        tmp.loc[end_id, 'TEM_Min'],
                        tmp.loc[start_id, 'TEM_Avg'],
                        tmp.loc[end_id, 'TEM_Avg'],
                        end_id - start_id + 1,
                        tmp.loc[start_id, 'TEM_Min'] - tmp.loc[end_id, 'TEM_Min'],  # 降温幅度
                        tmp.loc[start_id:end_id + 1, 'TEM_Min'].min(),
                        tmp.loc[start_id:end_id + 1, 'TEM_Avg'].mean(),
                        cold_wave_dict['cold_wave_type']))

        cold_wave_result = pd.DataFrame(cold_wave_result)
        cold_wave_result.columns = ['站名', '开始日期', '结束日期', '开始日最低气温', '结束日最低气温', '开始日平均气温', '结束日平均气温', '寒潮天数', '降温幅度', '过程最低气温', '过程平均气温', '类型']
        cold_wave_result['开始日期'] = cold_wave_result['开始日期'].dt.strftime('%Y-%m-%d')
        cold_wave_result['结束日期'] = cold_wave_result['结束日期'].dt.strftime('%Y-%m-%d')

        # table2 寒潮大风
        cold_wave_wind = cold_wave_result.apply(sample_row, axis=1)
        cold_wave_wind = cold_wave_wind[~cold_wave_wind.isnull()].tolist()

        if len(cold_wave_wind) != 0:
            cold_wave_wind = pd.concat(cold_wave_wind, axis=0)
            cold_wave_wind['日期'] = cold_wave_wind['Year'].map(int).map(str) + '-' + cold_wave_wind['Mon'].map(int).map(str) + '-' + cold_wave_wind['Day'].map(int).map(str)
            cold_wave_wind = cold_wave_wind[['Station_Name', '日期', 'WIN_S_Max', 'WIN_D_S_Max', '降温幅度', '过程最低气温', '过程平均气温', '影响前日期', '影响前最低气温', '影响前平均气温']]
            cold_wave_wind.columns = ['站名', '寒潮大风日期', '当日最大风速', '当日风向', '降温幅度', '过程最低气温', '过程平均气温', '影响前日期', '影响前最低气温', '影响前平均气温']

            cold_wave_wind.reset_index(drop=True, inplace=True)
            cold_wave_wind['降温幅度'] = cold_wave_wind['降温幅度'].map(float)
            cold_wave_wind['过程最低气温'] = cold_wave_wind['过程最低气温'].map(float)
            cold_wave_wind['过程平均气温'] = cold_wave_wind['过程平均气温'].map(float)

            # table3
            cold_wave_wind_d = cold_wave_wind.groupby('站名').apply(sample)
            cold_wave_wind_d.reset_index(inplace=True)
            cold_wave_wind_d.columns = ['站名', '风向类型', '风向频数', '百分比']

            cold_wave_result = cold_wave_result.round(1).to_dict(orient='records')
            cold_wave_wind = cold_wave_wind.round(1).to_dict(orient='records')
            cold_wave_wind_d = cold_wave_wind_d.round(1).to_dict(orient='records')

        else:
            cold_wave_result = cold_wave_result.round(1).to_dict(orient='records')
            cold_wave_wind = None
            cold_wave_wind_d = None

    except Exception as e:
        logging.exception(e)
        cold_wave_result = None
        cold_wave_wind = None
        cold_wave_wind_d = None

    finally:
        return cold_wave_result, cold_wave_wind, cold_wave_wind_d


if __name__ == '__main__':
    day_eles = ('Station_Id_C,Station_Name,Lat,Lon,Datetime,Year,Mon,Day,' + 'TEM_Avg,TEM_Min,WIN_S_Max,WIN_D_S_Max,SSH,PRE_Time_2020').split(',')
    path = r'C:\Users\MJY\Desktop\qhkxxlz\app\Files\test_data\qh_day.csv'
    df = pd.read_csv(path)
    years = '1950,2020'
    sta_ids = '52866,52862,56067'
    day_data = get_local_data(df, sta_ids, day_eles, years, 'Day')
    cold_wave_result, cold_wave_wind, cold_wave_wind_d = cold_wave_statistics(day_data)