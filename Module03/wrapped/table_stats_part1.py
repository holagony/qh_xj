import numpy as np
import pandas as pd
from Utils.data_processing import monthly_data_processing, monthly_data_processing
import logging

def table_stats_part1(data_df, element_name):
    '''
    用于各个天气现象要素的统计，第一部分，表1-3
    月数据源组合月要素，日数据源组合日要素
    如果某个要素全是nan，也不影响结果生成
    多个站点同时统计，适用并需要统计的要素如下：
    
    A.月数据要素
    雨 PRE_Days
    冰雹 Hail_Days
    雾 Fog_Days
    轻雾 Mist_Days
    雨凇 Glaze_Days
    雾凇 SoRi_Days	
    龙卷 Tord_Days	
    沙尘暴 SaSt_Days	
    扬沙 FlSa_Days
    浮尘 FlDu_Days
    霾 Haze_Days
    大风 GaWIN_Days

    B.日数据要素
    飑 Squa
    闪电 Lit
    尘卷风 DuWhr
    吹雪 DrSnow
    雪 Snow
    霜 Frost
    积雪 GSS
    结冰 ICE
    雷暴 Thund
    高温 TEM_Max
    低温 TEM_Min
    暴雨 PRE_Time_2020
    
    
    输出的表格为：
    table1: 各个站历年的天气现象次数
    table2: 各个站累年的天气现象总数、平均次数、最多次数及对应年份、最少次数及对应年份
    table3: 各个站累年各月的天气现象总数、平均次数、最多次数、最少次数
    '''

    # 表1
    def table1_stats(x):
        x = x[element_name]
        x = x.resample('1A', closed='right', label='right').sum()
        return x

    # 表2
    def table2_stats(x):
        x = x[element_name]
        x = x.resample('1A', closed='right', label='right').sum()

        sum_val = x.sum()  # 所有年的总日数
        mean_val = round(x.mean(), 1)  # 所有年的平均日数，保留1位小数
        max_val = x.max()  # 最多的雨日数
        max_val_year = x.idxmax().strftime('%Y')  # 最多的雨日数对应的年份
        min_val = x.min()  # 最少的雨日数
        min_val_year = x.idxmin().strftime('%Y')  # 最少的雨日数对应的年份

        values = np.array([sum_val, mean_val, max_val, max_val_year, min_val, min_val_year]).T
        row = pd.DataFrame(values)

        return row
    

    # 表3 累年各月
    def table3_stats(x):
        x = x[element_name]
        x = x.resample('1M', closed='right', label='right').sum()

        sum_accum = []
        mean_accum = []
        max_accum = []
        min_accum = []

        for i in range(1, 13):
            # sum
            month_i_sum = x[x.index.month == i].sum()
            sum_accum.append(month_i_sum)

            # mean
            month_i_mean = round(x[x.index.month == i].mean(), 1)  # 保留1位小数
            mean_accum.append(month_i_mean)

            # max
            month_i_max = x[x.index.month == i].max()
            max_accum.append(month_i_max)

            # min
            month_i_min = x[x.index.month == i].min()
            min_accum.append(month_i_min)

        sum_accum = pd.DataFrame(sum_accum).T
        mean_accum = pd.DataFrame(mean_accum).T
        max_accum = pd.DataFrame(max_accum).T
        min_accum = pd.DataFrame(min_accum).T
        concat = pd.concat([sum_accum, mean_accum, max_accum, min_accum], axis=0)

        return concat
    
    try:
        if element_name == 'TEM_Max':
            data_df[element_name]=(data_df[element_name]>30).astype(int)
        elif element_name == 'TEM_Min':
            data_df[element_name]=(data_df[element_name]<0).astype(int)
        elif element_name == 'PRE_Time_2020':
            data_df[element_name]=(data_df[element_name]>25).astype(int)
        
        station_name = data_df['Station_Name'].unique().tolist()
        table1 = data_df.groupby('Station_Name').apply(table1_stats).T
        table1.columns = [name + '站' for name in table1.columns]
        table1.insert(loc=0, column='年份', value=table1.index.year)  # 插入年份
        table1.reset_index(drop=True, inplace=True)
        table1 = table1.round(1).to_dict(orient='records')
        
        table2 = data_df.groupby('Station_Name').apply(table2_stats).unstack().reset_index()
        table2[table2.columns[1:]] = table2[table2.columns[1:]].apply(pd.to_numeric)
        table2.columns = ['站点', '总数', '年平均', '最多', '最多对应的年份', '最少', '最少对应的年份']
        table2 = table2.round(1).to_dict(orient='records')
        
        table3 = data_df.groupby('Station_Name').apply(table3_stats).reset_index()
        table3.columns = ['站名', '项目'] + [str(i) + '月' for i in range(1, 13)]
        table3['项目'] = ['总数', '平均', '最多', '最少'] * len(station_name)
        table3 = table3.round(1).to_dict(orient='records')
    
    except Exception as e:
        logging.info(e)
        table1 = None
        table2 = None
        table3 = None

    return table1, table2, table3


if __name__ == '__main__':
    path = r'D:\Project\3_项目\2_气候评估和气候可行性论证\qhkxxlz\Files\old_data\Module03_data\month.csv'
    month_data = pd.read_csv(path)
    month_data = monthly_data_processing(month_data)
    month_data.loc[month_data['Station_Id_C'] == '54843', 'PRE_Days'] = np.nan
    
    table1, table2, table3 = table_stats_part1(month_data, 'GaWIN_Days')
    data_df=month_data
    element_name='TEM_Max'