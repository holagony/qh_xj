import numpy as np
import pandas as pd
from collections import OrderedDict
from Utils.data_processing import monthly_data_processing, daily_data_processing
import logging

def all_weather_statistics_accum(data_month, data_day, elements_list, station):
    '''
    输出所有天气现象的累年各月总表
    '''
    try:
        if data_month is not None:
            data_month = data_month[data_month['Station_Name'] == station]
            data_month = data_month.resample('1M', closed='right', label='right').sum()
        if data_day is not None:
            
            if 'TEM_Max' in elements_list:
                data_day['TEM_Max']=(data_day['TEM_Max']>30).astype(int)
            elif 'TEM_Min' in elements_list:
                data_day['TEM_Min']=(data_day['TEM_Min']<0).astype(int)
            elif 'PRE_Time_2020' in elements_list:
                data_day['PRE_Time_2020' ]=(data_day['PRE_Time_2020' ]>25).astype(int)
                
            data_day = data_day[data_day['Station_Name'] == station]
            data_day = data_day.resample('1M', closed='right', label='right').sum()
    
    
        if data_day is not None:
            weather_data = data_day
        if data_month is not None:
            weather_data = data_month
        if data_month is not None and data_day is not None:
            weather_data = pd.concat([data_month,data_day],axis=0)
    
        # 提取相应列数据
        weather_data = weather_data[elements_list]
    
        # 计算
        total_mean = weather_data.mean().round(1).tolist()
        total_max = weather_data.max().tolist()
        total_min = weather_data.min().tolist()
    
        mean_weather_accum = []
        max_weather_accum = []
        min_weather_accum = []
    
        for i in range(1, 13):
            # mean
            month_i_mean = weather_data[weather_data.index.month == i].mean().round(1).to_frame()
            mean_weather_accum.append(month_i_mean)
    
            # max
            month_i_max = weather_data[weather_data.index.month == i].max().to_frame()
            max_weather_accum.append(month_i_max)
    
            # mean
            month_i_min = weather_data[weather_data.index.month == i].min().to_frame()
            min_weather_accum.append(month_i_min)
    
        ####################################################
        # 结果合成为DateFrame
        features = [
            'PRE_Days', 'Hail_Days', 'Fog_Days', 'Mist_Days', 'Glaze_Days', 'SoRi_Days', 'Tord_Days', 'SaSt_Days', 'FlSa_Days', 'FlDu_Days',
            'Haze_Days', 'GaWIN_Days', 'Squa', 'Lit', 'DuWhr', 'DrSnow', 'Snow', 'Frost', 'GSS', 'ICE', 'Thund','TEM_Max','TEM_Min','PRE_Time_2020','EICE_Days'
        ]
        ch_names = [
            '雨日数', '冰雹日数', '雾日数', '轻雾日数', '雨凇日数', '雾凇日数', '龙卷日数', '沙尘暴日数', '扬沙日数', '浮尘日数', '霾日数', '大风日数', '飑日数', '闪电数', '尘卷风日数', '吹雪日数', '雪日数', '霜日数',
            '积雪日数', '结冰日数', '雷暴日数','高温日数','低温日数','强降水日数','电线结冰'
        ]
    
        name_info = OrderedDict(zip(features, ch_names))
    
        name_list = []
        for ele in elements_list:
            for key, value in name_info.items():
                if key == ele:
                    name_list.append(value)
    
        # mean
        mean_weather_accum = pd.concat(mean_weather_accum, axis=1, ignore_index=True)
        mean_weather_accum.index = ['平均' + name for name in name_list]
        mean_weather_accum['累年'] = total_mean
        mean_weather_accum.reset_index(inplace=True)
        mean_weather_accum.index = range(0, len(name_list) * 3, 3)
    
        # max
        max_weather_accum = pd.concat(max_weather_accum, axis=1, ignore_index=True)
        max_weather_accum.index = ['最大' + name for name in name_list]
        max_weather_accum['累年'] = total_max
        max_weather_accum.reset_index(inplace=True)
        max_weather_accum.index = range(1, len(name_list) * 3 + 1, 3)
    
        # min
        min_weather_accum = pd.concat(min_weather_accum, axis=1, ignore_index=True)
        min_weather_accum.index = ['最小' + name for name in name_list]
        min_weather_accum['累年'] = total_min
        min_weather_accum.reset_index(inplace=True)
        min_weather_accum.index = range(2, len(name_list) * 3 + 2, 3)
    
        # 计算结果concat在一起
        weather_accum = pd.concat([mean_weather_accum, max_weather_accum, min_weather_accum], axis=0)
    
        # 增加月份
        # columns = [station + '站要素', '1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月', '年']
        columns = ['要素', '1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月', '年']
        weather_accum.columns = columns
        weather_accum.sort_index(inplace=True)
        weather_accum = weather_accum.round(1).to_dict(orient='records')

    except Exception as e:
        logging.exception(e)
        weather_accum = None

    return weather_accum


if __name__ == '__main__':
    path1 = r'C:\Users\mjynj\Desktop\sd-scdp-algo\Files\Module03_data\day.csv'
    day_data = pd.read_csv(path1)
    day_data = daily_data_processing(day_data)

    path2 = r'C:\Users\mjynj\Desktop\sd-scdp-algo\Files\Module03_data\month.csv'
    month_data = pd.read_csv(path2)
    month_data = monthly_data_processing(month_data)

    # month_data = None
    # day_data = None

    # 筛选要素
    element = [
        'PRE_Days', 'Hail_Days', 'Fog_Days', 'Mist_Days', 'Glaze_Days', 'SoRi_Days', 'Tord_Days', 'SaSt_Days', 'FlSa_Days', 'FlDu_Days', 'Haze_Days',
        'GaWIN_Days', 'Squa', 'Lit', 'DuWhr', 'DrSnow', 'Snow', 'Frost', 'GSS', 'ICE', 'Thund'
    ]

    # month_data.loc[month_data['Station_Id_C'] == '54823', 'PRE_Days'] = np.nan  # 模拟某个站该要素全是nan
    result = all_weather_statistics_accum(month_data, day_data, element, '济南')
