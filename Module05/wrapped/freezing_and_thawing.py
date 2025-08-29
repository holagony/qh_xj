import simplejson
import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.get_local_data import get_local_data
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_processing import daily_data_processing

def calc_freezing_and_thawing_times(input_df, hourly=1):
    '''
    冻融交替次数计算计算 支持使用小时数据或日数据 不用做插值处理
    小数数据：从逐时的干球温度中计算，逐时气温从 3℃以上降至-3℃以下，然后再回升到 3℃ 以上算1次冻融交替循环
    日数据：以一年内的逐日的日最低气温判断，若日最低气温从+3℃以上降至-3℃以下，然后回升到+3℃以上的过程
    日数据基于 《水工建筑物抗冻设计规范》 SL211-98
    注意：假如输入10年的数据2000.1-2009.12,由于采用气象年计算，最后只会得到9年的结果。
    '''
    start_year = input_df.index.year[0]
    num_years = len(input_df.index.year.unique())

    if hourly == 1:
        input_df = input_df['TEM'].to_frame()
    else:
        input_df = input_df['TEM_Min'].to_frame()

    input_df.columns = ['气温']
    year_list = []
    num_list = []

    for i in range(num_years - 1):
        try:
            year = start_year + i
            start_date = str(year) + '0701'
            meteo_year_idx = pd.bdate_range(start=start_date, periods=12, freq='M').strftime('%Y-%m').tolist()  # 每年7月到次年6月
            # print(meteo_year_idx)
            # print('-------------')
    
            for j in range(len(meteo_year_idx)):
                data = input_df.loc[meteo_year_idx[j]]
                if j == 0:
                    final_data = data
                else:
                    final_data = pd.concat([final_data, data], axis=0)
    
            begin_year = final_data.index.year[0]
            last_year = final_data.index.year[-1]
            new_index = str(begin_year) + '.7' + '-' + str(last_year) + '.6'
    
            num = 0
            idx3 = final_data[final_data['气温'] > 3].index
    
            for i in range(1, len(idx3)):
                start_idx = idx3[i - 1]
                end_idx = idx3[i]
                segment = final_data.loc[start_idx:end_idx]
    
                if True in (segment.values < -3):
                    num = num + 1
        except:
            new_index=np.nan
            num=np.nan
        year_list.append(new_index)
        num_list.append(num)
            

    result = list(zip(year_list, num_list))
    df = pd.DataFrame(result, columns=['时间段', '冻融交替次数'])
    df = df.round(1)
    df = df.dropna()

    return df


def calc_freezing_and_thawing_day(daily_df):
    '''
    GJB 1172.11-1991 军用设备气候极值 地表温度、冻土深度和冻融循环日数
    对每一天的日最高气温、日最低气温分别判断，
    若一天内同时满足最高气温在0℃以上、最低气温在0℃以下，则作为一个冻融循环日
    '''
    input_df = daily_df[['TEM_Max', 'TEM_Min']]
    start_year = input_df.index.year[0]
    num_years = len(input_df.index.year.unique())

    for i in range(num_years - 1):
        try:
            year = start_year + i
            start_date = str(year) + '0701'
            meteo_year_idx = pd.bdate_range(start=start_date, periods=12, freq='M').strftime('%Y-%m').tolist()  # 每年7月到次年6月
            # print(meteo_year_idx)
            # print('-------------')
    
            for j in range(len(meteo_year_idx)):
                data = input_df.loc[meteo_year_idx[j]]
    
                if j == 0:
                    final_data = data
                else:
                    final_data = pd.concat([final_data, data], axis=0)
    
            begin_year = final_data.index.year[0]
            last_year = final_data.index.year[-1]
            new_index = str(begin_year) + '.7' + '-' + str(last_year) + '.6'
            freezing = final_data[(final_data['TEM_Max'] > 0) & (final_data['TEM_Min'] < 0)].shape[0]
            result_df = pd.DataFrame([new_index, freezing]).T
    
            freezing_day = pd.DataFrame(index=final_data[(final_data['TEM_Max'] > 0) & (final_data['TEM_Min'] < 0)].index)
            freezing_day['次数'] = 1
    
            if i == 0:
                total_df = result_df
                all_freezing_day = freezing_day
            else:
                total_df = pd.concat([total_df, result_df], axis=0)
                all_freezing_day = pd.concat([all_freezing_day, freezing_day], axis=0)
    
            # 累年各月
            freezing_accum = []
            for i in range(1, 13):
                month_i_mean = all_freezing_day[all_freezing_day.index.month == i].sum().to_frame()
                freezing_accum.append(month_i_mean)
        except:
            pass

    total_df.columns = ['时间段', '冻融交替次数']
    total_df['冻融交替次数'] = total_df['冻融交替次数'].map(int)
    freezing_accum = pd.concat(freezing_accum, axis=1)
    freezing_accum.columns = [str(i) + '月' for i in range(1, 13)]
    freezing_accum = freezing_accum/len(total_df)
    freezing_accum = freezing_accum.round(1)
    freezing_accum.insert(loc=0, column='月份', value='次数')
    freezing_accum.reset_index(drop=True, inplace=True)

    return total_df, freezing_accum


if __name__ == '__main__':

    daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    hourly_df = pd.read_csv(cfg.FILES.QH_DATA_HOUR)
    sta_ids = '56067'
    day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + 'TEM_Max,TEM_Min').split(',')
    hour_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,' + 'TEM').split(',')
    years = '2000,2020'
    daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')
    hourly_df = get_local_data(hourly_df, sta_ids, hour_eles, years, 'Hour')
    
    # result1 = calc_freezing_and_thawing_times(hourly_df, hourly=1)
    result2 = calc_freezing_and_thawing_times(daily_df, hourly=0)
    result3, freezing_accum = calc_freezing_and_thawing_day(daily_df)

