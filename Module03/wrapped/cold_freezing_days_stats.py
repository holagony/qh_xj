import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.data_processing import daily_data_processing
import logging

def cold_freeing_days_statistics(data_df):
    '''
    多站低温冰冻过程统计
    表格类型和寒潮一样
    如果某个站缺少要素，导致不能统计，则输出结果里面没有这个站
    如果所有站都缺少要素，导致不能统计，则输出None
    '''

    def table_stats(x):
        x.reset_index(inplace=True)
        rows = x[~((x['TEM_Avg'] <= 1) & (x['TEM_Min'] <= 0) & (x['PRE_Time_2020'] > 0.1))]

        seg_points = rows.index.tolist()
        seg_list = np.split(x, seg_points)

        # 先删除小于3天的过程数据，加快后续循环遍历的速度
        seg_list = list(filter(lambda x: len(x) >= 3, seg_list))
        new_list = []

        for df in seg_list:
            if df.iloc[0, 2] > 1 or df.iloc[0, 3] > 0 or df.iloc[0, 4] <= 0.1:
                df.drop(df.index[0], inplace=True)  # 删除第1行

            if len(df) >= 3:
                df.reset_index(drop=True, inplace=True)
                new_df = pd.DataFrame(columns=['站名', '开始日期', '结束日期', '开始平均温度', '结束平均温度', '开始日降水量', '结束日降水量', '过程天数'])
                new_df.loc[0, '站名'] = df.iloc[0, 1]
                new_df['开始日期'] = df.iloc[0, 0].strftime('%Y-%m-%d')
                new_df['结束日期'] = df.iloc[-1, 0].strftime('%Y-%m-%d')
                new_df['开始平均温度'] = df.iloc[0, 2]
                new_df['结束平均温度'] = df.iloc[-1, 2]
                new_df['开始日降水量'] = df.iloc[0, 4]
                new_df['结束日降水量'] = df.iloc[-1, 4]
                new_df['过程天数'] = len(df)
                new_df['类型'] = '低温冰冻'
                new_list.append(new_df)

        try:
            result = pd.concat(new_list, axis=0)
            return result

        except Exception as e:
            pass

    try:
        data_df = data_df[['Station_Name', 'TEM_Avg', 'TEM_Min', 'PRE_Time_2020']]
        data_df = data_df.dropna(axis=0, how='any')

        if data_df.shape[0] != 0:
            result_table = data_df.groupby('Station_Name').apply(table_stats)
            result_table.reset_index(drop=True, inplace=True)
            result_table = result_table.round(1).to_dict(orient='records')

        else:
            result_table = None

    except Exception as e:
        result_table = None

    return result_table


if __name__ == '__main__':
    path = r'D:\Project\3_项目\2_气候评估和气候可行性论证\qhkxxlz\Files\old_data\Module03_data\day.csv'
    day_data = pd.read_csv(path)
    day_data = daily_data_processing(day_data)
    # day_data.loc[day_data['Station_Id_C'] == '54843', 'TEM_Avg'] = np.nan  # 模拟某个站该要素全是nan
    # day_data.loc[day_data['Station_Id_C'] == '54736', 'TEM_Avg'] = np.nan
    # day_data.loc[day_data['Station_Id_C'] == '54857', 'TEM_Avg'] = np.nan
    # day_data.loc[day_data['Station_Id_C'] == '54823', 'TEM_Avg'] = np.nan
    # day_data.loc[day_data['Station_Id_C'] == '54714', 'TEM_Avg'] = np.nan
    cold_freezing = cold_freeing_days_statistics(day_data)