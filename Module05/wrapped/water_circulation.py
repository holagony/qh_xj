import simplejson
import numpy as np
import pandas as pd
import metpy.calc as mcalc
from metpy.units import units
from scipy import stats
from scipy import interpolate
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_processing import daily_data_processing


def calc_dewpoint_temperature(vapor_p):
    '''
    使用水汽压计算露点温度
    '''
    vp = np.array(vapor_p) * units('hPa')
    dewpoint = mcalc.dewpoint(vp)
    return dewpoint


def calc_dewpoint_temperature_with_rh(tem, rh):
    '''
    使用RH计算露点温度
    rh 0~1
    '''
    tem = np.array(tem) * units('degC')
    rh = np.array(rh)
    dewpoint = mcalc.dewpoint_from_relative_humidity(tem, rh)
    return dewpoint


def calc_wet_bulb_temperature(prs, tem, dewpoint):
    '''
    计算湿球温度
    '''
    prs = np.array(prs) * units('hPa')
    tem = np.array(tem) * units('degC')
    wbt = mcalc.wet_bulb_temperature(prs, tem, dewpoint)
    return wbt.m


def calc_water_circulation(input_df):
    '''
    冷却塔循环水系统设计气象参数 使用日数据
    '''
    ######################################################
    # 1.夏季最热三个月累积频率为10%/5%/1%的湿球温度
    '''
    夏季1%、5%、10%累积频率的日平均湿球温度及对应的干球温度、大气压、相对湿度
    '''
    sample_data = input_df[['TEM_Avg', 'PRS_Avg', 'RHU_Avg']]
    dewpoint = calc_dewpoint_temperature_with_rh(sample_data['TEM_Avg'], sample_data['RHU_Avg'])
    wbt = calc_wet_bulb_temperature(sample_data['PRS_Avg'], sample_data['TEM_Avg'], dewpoint).round(1)
    data1 = sample_data.copy()
    data1['wbt'] = wbt

    hot_month = data1['TEM_Avg'].resample('1M', closed='right', label='right').mean()
    hot_three_yearly = hot_month.groupby(hot_month.index.year).nlargest(3)
    month_idx = hot_three_yearly.index.levels[1].strftime("%Y-%m").tolist()

    # 提取的最热三个月数据
    for i in range(len(month_idx)):
        data = data1.loc[month_idx[i]]

        if i == 0:
            final_data = data
        else:
            final_data = pd.concat([final_data, data], axis=0)

    # 湿球温度CDF估计、插值
    wbt_res = stats.relfreq(final_data['wbt'], numbins=50)
    wbt_cdf = np.cumsum(wbt_res.frequency)
    wbt_data = wbt_res.lowerlimit + np.linspace(0, wbt_res.binsize * wbt_res.frequency.size, wbt_res.frequency.size)
    wbt_prob = np.arange(0.01, 1.01, 0.01).reshape(-1, 1)
    interp = interpolate.interp1d(wbt_cdf, wbt_data, fill_value='extrapolate')
    wbt_result = interp(wbt_prob)
    
    # 找到累积频率气温对应的时间和真实数据
    freq_list = [9, 4, 0]  # 10%/5%/1%
    result_summer = []

    for freq in freq_list:
        freq_wbt = float(wbt_result[freq][0])
        df_sort = final_data.iloc[(final_data['wbt'] - freq_wbt).abs().argsort(), :]
        closest_value = df_sort.iloc[0, -1]

        selected_df = final_data[final_data['wbt'] == closest_value]  # 与累积频率wbt最邻近的真实wbt的df，并包含对应的气压和湿度
        selected_df_cp = selected_df.copy()
        selected_df_cp[str(freq + 1) + '%累积频率湿球温度'] = freq_wbt
        selected_df_cp['日期'] = selected_df_cp.index.strftime("%Y-%m-%d")
        selected_df_cp = selected_df_cp.reset_index(drop=True)
        result_summer.append(selected_df_cp)

    ######################################################
    # 2.每年最高第七个日平均湿球温度的历年平均值，及对应的干球温度、大气压、相对湿度
    # sample_data = input_df[['TEM_Avg','PRS_Avg','RHU_Avg']]
    # dewpoint = calc_dewpoint_temperature_with_rh(sample_data['TEM_Avg'], sample_data['RHU_Avg'])
    # wbt = calc_wet_bulb_temperature(sample_data['PRS_Avg'], sample_data['TEM_Avg'], dewpoint)
    # data1 = sample_data.copy()
    # data1['wbt'] = wbt

    largest7 = data1.groupby(data1.index.year)['wbt'].nlargest(7)
    seventh = largest7.groupby(largest7.index.levels[1].year).idxmin()

    idx = [seventh.iloc[i][1] for i in range(len(seventh))]
    result4 = data1.loc[idx]
    result4 = result4.mean().to_frame().T  # 结果
    result4 = result4[['wbt', 'TEM_Avg', 'PRS_Avg', 'RHU_Avg']]
    result4.index = ['result']

    ######################################################
    # 3.历年最高湿球温度及对应的干球温度、大气压、相对湿度
    #sample_data = input_df[['TEM_Avg','PRS_Avg','RHU_Avg']]
    #dewpoint = calc_dewpoint_temperature_with_rh(sample_data['TEM_Avg'], sample_data['RHU_Avg'])
    #wbt = calc_wet_bulb_temperature(sample_data['PRS_Avg'], sample_data['TEM_Avg'], dewpoint)
    #data1 = sample_data.copy()
    #data1['wbt'] = wbt

    max_val = data1.resample('1A', closed='right', label='right')['wbt'].idxmax()
    idx = [max_val.iloc[i] for i in range(len(max_val))]
    result5 = data1.loc[idx]
    result5['date'] = result5.index.strftime("%Y-%m-%d").tolist()
    result5 = result5[['date', 'wbt', 'TEM_Avg', 'PRS_Avg', 'RHU_Avg']]
    result5 = result5.reset_index(drop=True)
    result5.set_index('date', inplace=True)

    ######################################################
    # 4.历年最低湿球温度及对应的干球温度、大气压、相对湿度
    #sample_data = input_df[['TEM_Avg','PRS_Avg','RHU_Avg']]
    #dewpoint = calc_dewpoint_temperature_with_rh(sample_data['TEM_Avg'], sample_data['RHU_Avg'])
    #wbt = calc_wet_bulb_temperature(sample_data['PRS_Avg'], sample_data['TEM_Avg'], dewpoint)
    #data1 = sample_data.copy()
    #data1['wbt'] = wbt

    min_val = data1.resample('1A', closed='right', label='right')['wbt'].idxmin()
    idx = [min_val.iloc[i] for i in range(len(min_val))]
    result6 = data1.loc[idx]
    result6['date'] = result6.index.strftime("%Y-%m-%d").tolist()
    result6 = result6[['date', 'wbt', 'TEM_Avg', 'PRS_Avg', 'RHU_Avg']]
    result6 = result6.reset_index(drop=True)
    result6.set_index('date', inplace=True)

    ######################################################
    # 5.平均年湿球温度及对应的干球温度、气压与相对湿度
    '''
    取历年年湿球温度及对应的干球温度、气压与相对湿度，求各自年平均值。
    '''
    #sample_data = input_df[['TEM_Avg','PRS_Avg','RHU_Avg']]
    #dewpoint = calc_dewpoint_temperature_with_rh(sample_data['TEM_Avg'], sample_data['RHU_Avg'])
    #wbt = calc_wet_bulb_temperature(sample_data['PRS_Avg'], sample_data['TEM_Avg'], dewpoint)
    #data1 = sample_data.copy()
    #data1['wbt'] = wbt

    result7 = data1.resample('1A', closed='right', label='right').mean()
    result7['date'] = result7.index.year.astype(str)
    result7 = result7[['date', 'wbt', 'TEM_Avg', 'PRS_Avg', 'RHU_Avg']]
    result7 = result7.reset_index(drop=True)
    result7.set_index('date', inplace=True)

    ######################################################
    # 6.平均逐月湿球温度及对应的干球温度、气压与相对湿度
    '''
    取历年逐月湿球温度及对应的干球温度、气压与相对湿度，求各自逐月平均值。
    '''
    #sample_data = input_df[['TEM_Avg','PRS_Avg','RHU_Avg']]
    #dewpoint = calc_dewpoint_temperature_with_rh(sample_data['TEM_Avg'], sample_data['RHU_Avg'])
    #wbt = calc_wet_bulb_temperature(sample_data['PRS_Avg'], sample_data['TEM_Avg'], dewpoint)
    #data1 = sample_data.copy()
    #data1['wbt'] = wbt

    result8 = data1.resample('1M', closed='right', label='right').mean()
    result8['date'] = result8.index.strftime("%Y-%m").tolist()
    result8 = result8[['date', 'wbt', 'TEM_Avg', 'PRS_Avg', 'RHU_Avg']]
    result8 = result8.reset_index(drop=True)
    result8.set_index('date', inplace=True)

    ######################################################
    # 合并所有结果
    result_dict = edict()
    result_dict.result1 = result_summer[0].round(1).to_dict(orient='records')
    result_dict.result2 = result_summer[1].round(1).to_dict(orient='records')
    result_dict.result3 = result_summer[2].round(1).to_dict(orient='records')
    result_dict.result4 = result4.round(1).to_dict(orient='records')
    result_dict.result5 = result5.round(1).to_dict(orient='index')
    result_dict.result6 = result6.round(1).to_dict(orient='index')
    result_dict.result7 = result7.round(1).to_dict(orient='index')
    result_dict.result8 = result8.round(1).to_dict(orient='index')

    result_dict.note = [
        'result1-夏季10%累积频率的日湿球温度及对应的干球温度、气压、相对湿度', 
        'result2-夏季5%累积频率的日湿球温度及对应的干球温度、气压、相对湿度', 
        'result3-夏季1%累积频率的日湿球温度及对应的干球温度、气压、相对湿度', 
        'result4-每年最高第七个日平均湿球温度的历年平均值及对应的干球温度、气压、相对湿度', 
        'result5-历年最高湿球温度及对应的干球温度、气压、相对湿度',
        'result6-历年最低湿球温度及对应的干球温度、气压、相对湿度', 
        'result7-历年平均湿球温度及对应的干球温度、气压、相对湿度', 
        'result8-历年逐月湿球温度及对应的干球温度、气压、相对湿度']

    return result_dict


if __name__ == '__main__':
    # df_day = pd.read_csv(r'D:\Project\3_项目\2_气候评估和气候可行性论证\qhkxxlz\Files\old_data\Module05_data\day.csv')
    # df_day.set_index('Datetime', inplace=True)
    # df_day.index = pd.DatetimeIndex(df_day.index)
    # #df_day.iloc[:,7:] = df_day.iloc[:,7:].interpolate(method='linear',axis=0) # 缺失值插值填充
    # #df_day.iloc[:,7:] = df_day.iloc[:,7:].fillna(method='bfill') # 填充后一条数据的值，但是后一条也不一定有值
    # df_day.drop(['Unnamed: 0'], axis=1, inplace=True)
    
    
    daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    post_daily_df = daily_data_processing(daily_df)
    post_daily_df = post_daily_df[post_daily_df['Station_Id_C']=='52853']
    post_daily_df = post_daily_df[post_daily_df.index.year>=1994]
    df_day = post_daily_df[post_daily_df.index.year<=2023]
    df_day['RHU_Avg'] = df_day['RHU_Avg'] / 100
    df_day.dropna(inplace=True)
    result = calc_water_circulation(df_day)