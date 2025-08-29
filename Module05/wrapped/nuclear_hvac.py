import math
import simplejson
import numpy as np
import pandas as pd
import metpy.calc as mcalc
from metpy.units import units
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_processing import hourly_data_processing


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


def calc_nuclear_havc(df_hourly, interpolation):
    '''
    计算核岛参数，采用小时数据
    核岛采暖通风与空气调节室外空气计算参数
    '''
    df_hourly = df_hourly[['PRS', 'TEM', 'RHU']]
    num_years = len(df_hourly.index.year.unique())

    if interpolation == 0:
        df_hourly = df_hourly[df_hourly.index.hour.isin([0, 6, 12, 18])]  # 4次定时
        df_hourly.dropna(inplace=True)
    else:
        df_hourly = df_hourly.interpolate(method='spline', order=3)

    ######################################################
    # 1.最高正常设计干球温度TAS/最高正常设计湿球温度TAH
    sample_data = df_hourly['TEM'].resample('1M', closed='right', label='right').mean()
    hot_four_yearly = sample_data.groupby(sample_data.index.year).nlargest(4)  # 历年最高温度的四个月
    idx = hot_four_yearly.index.levels[1].strftime('%Y-%m').tolist()

    # 提取最热四个月的小时数据
    for i in range(len(idx)):
        data = df_hourly.loc[idx[i]]

        if i == 0:
            final_data = data
        else:
            final_data = pd.concat([final_data, data], axis=0)

    # 排序、计算位置索引
    tmp = final_data.sort_values(by='TEM', ascending=False).reset_index()
    tmp.rename(columns={'index':'Datetime'}, inplace=True)

    # len(tmp)包括：年数*历年4个月的天数*每日样本数
    pos = math.floor(len(tmp) * 0.01)

    # TAS/TAH
    dewpoint = calc_dewpoint_temperature_with_rh(tmp.loc[pos - 1, 'TEM'], tmp.loc[pos - 1, 'RHU'])
    TAH = calc_wet_bulb_temperature([tmp.loc[pos - 1, 'PRS']], [tmp.loc[pos - 1, 'TEM']], dewpoint)
    TAS = tmp.loc[pos - 1, 'TEM']

    # TAS及对应TAH出现时刻
    all_TAS = tmp[tmp['TEM'] == TAS]
    dewpoint = calc_dewpoint_temperature_with_rh(all_TAS['TEM'], all_TAS['RHU'])
    wbt = calc_wet_bulb_temperature(all_TAS['PRS'], all_TAS['TEM'], dewpoint)
    all_result1 = all_TAS[['Datetime', 'TEM']].copy()
    all_result1['wbt'] = wbt  #all TAS/TAH
    all_result1['Datetime'] = all_result1['Datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
    all_result1 = all_result1.reset_index(drop=True)
    all_result1.columns = ['出现时间','干球温度(C°)','湿球温度(C°)']

    ######################################################
    # 2.最低正常设计干球温度TBS/最低正常设计湿球温度TBH
    sample_data = df_hourly['TEM'].resample('1M', closed='right', label='right').mean()
    cold_three_yearly = sample_data.groupby(sample_data.index.year).nsmallest(3)  # 历年最冷三月

    # 提取最冷三个月的小时数据
    idx = cold_three_yearly.index.levels[1].strftime('%Y-%m').tolist()
    for i in range(len(idx)):
        data = df_hourly.loc[idx[i]]

        if i == 0:
            final_data = data
        else:
            final_data = pd.concat([final_data, data], axis=0)

    # 排序、计算位置索引
    tmp = final_data.sort_values(by='TEM', ascending=True).reset_index()  # 从小到大
    tmp.rename(columns={'index':'Datetime'}, inplace=True)

    pos = math.floor(len(tmp) * 0.01)

    # TBS/TBH
    dewpoint = calc_dewpoint_temperature_with_rh(tmp.loc[pos - 1, 'TEM'], tmp.loc[pos - 1, 'RHU'])
    TBH = calc_wet_bulb_temperature([tmp.loc[pos - 1, 'PRS']], [tmp.loc[pos - 1, 'TEM']], dewpoint)
    TBS = tmp.loc[pos - 1, 'TEM']

    # TBS及对应TBH出现时刻
    all_TBS = tmp[tmp['TEM'] == TBS]
    dewpoint = calc_dewpoint_temperature_with_rh(all_TBS['TEM'], all_TBS['RHU'])
    wbt = calc_wet_bulb_temperature(all_TBS['PRS'], all_TBS['TEM'], dewpoint)
    all_result2 = all_TBS[['Datetime', 'TEM']].copy()
    all_result2['wbt'] = wbt  #all TBS/TBH
    all_result2['Datetime'] = all_result2['Datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
    all_result2 = all_result2.reset_index(drop=True)
    all_result2.columns = ['出现时间','干球温度(C°)','湿球温度(C°)']

    ######################################################
    # 3.最高安全设计干球温度TCS/最高安全设计湿球温度TCH
    sample_data = df_hourly['TEM'].resample('1M', closed='right', label='right').mean()
    hot_four_yearly = sample_data.groupby(sample_data.index.year).nlargest(4)  # 历年最高温度的四个月

    # 提取最热四个月的小时数据
    idx = hot_four_yearly.index.levels[1].strftime('%Y-%m').tolist()
    for i in range(len(idx)):
        data = df_hourly.loc[idx[i]]

        if i == 0:
            final_data = data
        else:
            final_data = pd.concat([final_data, data], axis=0)

    # 排序、计算位置索引
    tmp = final_data.sort_values(by='TEM', ascending=False).reset_index()
    tmp.rename(columns={'index':'Datetime'}, inplace=True)

    if interpolation == 0:
        pos = math.floor((2 / 6) * num_years)
    else:
        pos = 2 * num_years

    # TCS/TCH
    dewpoint = calc_dewpoint_temperature_with_rh(tmp.loc[pos - 1, 'TEM'], tmp.loc[pos - 1, 'RHU'])
    TCH = calc_wet_bulb_temperature([tmp.loc[pos - 1, 'PRS']], [tmp.loc[pos - 1, 'TEM']], dewpoint)
    TCS = tmp.loc[pos - 1, 'TEM']

    # TCS及对应TCH出现时刻
    all_TCS = tmp[tmp['TEM'] == TCS]
    dewpoint = calc_dewpoint_temperature_with_rh(all_TCS['TEM'], all_TCS['RHU'])
    wbt = calc_wet_bulb_temperature(all_TCS['PRS'], all_TCS['TEM'], dewpoint)
    all_result3 = all_TCS[['Datetime', 'TEM']].copy()
    all_result3['wbt'] = wbt  #all TCS/TCH
    all_result3['Datetime'] = all_result3['Datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
    all_result3 = all_result3.reset_index(drop=True)
    all_result3.columns = ['出现时间','干球温度(C°)','湿球温度(C°)']

    ######################################################
    # 4.最低安全设计干球温度TDS/最低安全设计湿球温度TDH
    sample_data = df_hourly['TEM'].resample('1M', closed='right', label='right').mean()
    cold_three_yearly = sample_data.groupby(sample_data.index.year).nsmallest(3)  # 历年最冷三月

    # 提取最冷三个月的小时数据
    idx = cold_three_yearly.index.levels[1].strftime('%Y-%m').tolist()
    for i in range(len(idx)):
        data = df_hourly.loc[idx[i]]

        if i == 0:
            final_data = data
        else:
            final_data = pd.concat([final_data, data], axis=0)

    # 排序、计算位置索引
    tmp = final_data.sort_values(by='TEM', ascending=True).reset_index()  # 从小到大
    tmp.rename(columns={'index':'Datetime'}, inplace=True)

    if interpolation == 0:
        pos = math.floor((2 / 6) * num_years)
    else:
        pos = 2 * num_years

    # TDS/TDH
    dewpoint = calc_dewpoint_temperature_with_rh(tmp.loc[pos - 1, 'TEM'], tmp.loc[pos - 1, 'RHU'])
    TDH = calc_wet_bulb_temperature([tmp.loc[pos - 1, 'PRS']], [tmp.loc[pos - 1, 'TEM']], dewpoint)
    TDS = tmp.loc[pos - 1, 'TEM']

    # TDS及对应TDH出现时刻
    all_TDS = tmp[tmp['TEM'] == TDS]
    dewpoint = calc_dewpoint_temperature_with_rh(all_TDS['TEM'], all_TDS['RHU'])
    wbt = calc_wet_bulb_temperature(all_TDS['PRS'], all_TDS['TEM'], dewpoint)
    all_result4 = all_TDS[['Datetime', 'TEM']].copy()
    all_result4['wbt'] = wbt  #all TDS/TDH
    all_result4['Datetime'] = all_result4['Datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
    all_result4 = all_result4.reset_index(drop=True)
    all_result4.columns = ['出现时间','干球温度(C°)','湿球温度(C°)']

    ######################################################
    # 5.不保证5%最高干球温度及对应湿球温度
    sample_data = df_hourly['TEM'].resample('1M', closed='right', label='right').mean()
    hot_four_yearly = sample_data.groupby(sample_data.index.year).nlargest(4)  # 历年最高温度的四个月

    # 提取最热四个月的小时数据
    idx = hot_four_yearly.index.levels[1].strftime('%Y-%m').tolist()
    for i in range(len(idx)):
        data = df_hourly.loc[idx[i]]

        if i == 0:
            final_data = data
        else:
            final_data = pd.concat([final_data, data], axis=0)

    # 排序、计算位置索引
    tmp = final_data.sort_values(by='TEM', ascending=False).reset_index()
    pos = math.floor(len(tmp) * 0.05)
    tmp.rename(columns={'index':'Datetime'}, inplace=True)

    # 不保证5%干球/湿球
    dewpoint = calc_dewpoint_temperature_with_rh(tmp.loc[pos - 1, 'TEM'], tmp.loc[pos - 1, 'RHU'])
    wbt_5 = calc_wet_bulb_temperature([tmp.loc[pos - 1, 'PRS']], [tmp.loc[pos - 1, 'TEM']], dewpoint)
    tem_5 = tmp.loc[pos - 1, 'TEM']

    # 出现的时刻
    all_tem_5 = tmp[tmp['TEM'] == tem_5]
    dewpoint = calc_dewpoint_temperature_with_rh(all_tem_5['TEM'], all_tem_5['RHU'])
    wbt = calc_wet_bulb_temperature(all_tem_5['PRS'], all_tem_5['TEM'], dewpoint)
    all_result5 = all_tem_5[['Datetime', 'TEM']].copy()
    all_result5['wbt'] = wbt
    all_result5['Datetime'] = all_result5['Datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
    all_result5 = all_result5.reset_index(drop=True)
    all_result5.columns = ['出现时间','干球温度(C°)','湿球温度(C°)']

    ######################################################
    # 6.不保证5%最低干球温度及对应湿球温度
    sample_data = df_hourly['TEM'].resample('1M', closed='right', label='right').mean()
    cold_three_yearly = sample_data.groupby(sample_data.index.year).nsmallest(3)  # 历年最冷三月

    # 提取最冷三个月的小时数据
    idx = cold_three_yearly.index.levels[1].strftime('%Y-%m').tolist()
    for i in range(len(idx)):
        data = df_hourly.loc[idx[i]]

        if i == 0:
            final_data = data
        else:
            final_data = pd.concat([final_data, data], axis=0)

    # 排序、计算位置索引
    tmp = final_data.sort_values(by='TEM', ascending=True).reset_index()  # 从小到大
    pos = math.floor(len(tmp) * 0.05)
    tmp.rename(columns={'index':'Datetime'}, inplace=True)

    # 不保证5%干球/湿球
    dewpoint = calc_dewpoint_temperature_with_rh(tmp.loc[pos - 1, 'TEM'], tmp.loc[pos - 1, 'RHU'])
    wbt_5_cold = calc_wet_bulb_temperature([tmp.loc[pos - 1, 'PRS']], [tmp.loc[pos - 1, 'TEM']], dewpoint)
    tem_5_cold = tmp.loc[pos - 1, 'TEM']

    # 出现的时刻
    all_tem_5 = tmp[tmp['TEM'] == tem_5_cold]
    dewpoint = calc_dewpoint_temperature_with_rh(all_tem_5['TEM'], all_tem_5['RHU'])
    wbt = calc_wet_bulb_temperature(all_tem_5['PRS'], all_tem_5['TEM'], dewpoint)
    all_result6 = all_tem_5[['Datetime', 'TEM']].copy()
    all_result6['wbt'] = wbt
    all_result6['Datetime'] = all_result6['Datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
    all_result6 = all_result6.reset_index(drop=True)
    all_result6.columns = ['出现时间','干球温度(C°)','湿球温度(C°)']

    ######################################################
    # 结果输出
    all_result1 = all_result1.round(1).to_dict(orient='records')
    all_result2 = all_result2.round(1).to_dict(orient='records')
    all_result3 = all_result3.round(1).to_dict(orient='records')
    all_result4 = all_result4.round(1).to_dict(orient='records')
    all_result5 = all_result5.round(1).to_dict(orient='records')
    all_result6 = all_result6.round(1).to_dict(orient='records')

    result_dict = edict()
    result_dict.TAS = round(TAS, 1)
    result_dict.TAH = round(TAH, 1)
    result_dict.TBS = round(TBS, 1)
    result_dict.TBH = round(TBH, 1)
    result_dict.TCS = round(TCS, 1)
    result_dict.TCH = round(TCH, 1)
    result_dict.TDS = round(TDS, 1)
    result_dict.TDH = round(TDH, 1)

    result_dict.result1 = all_result1
    result_dict.result2 = all_result2
    result_dict.result3 = all_result3
    result_dict.result4 = all_result4
    result_dict.result5 = all_result5
    result_dict.result6 = all_result6

    result_dict.note = ['TAS-最高正常设计干球温度', 'TAH-最高正常设计湿球温度', 'TBS-最低正常设计干球温度', 'TBH-最低正常设计湿球温度', 
                        'TCS-最高安全设计干球温度', 'TCH-最高安全设计湿球温度', 'TDS-最低安全设计干球温度', 'TDH-最低安全设计湿球温度', 
                        'result1-最高正常设计干球温度对应湿球温度及出现时刻', 
                        'result2-最低正常设计干球温度对应湿球温度及出现时刻', 
                        'result3-最高安全设计干球温度对应湿球温度及出现时刻',
                        'result4-最低安全设计干球温度对应湿球温度及出现时刻', 
                        'result5-不保证5%最高干球温度对应湿球温度及出现时刻', 
                        'result6-不保证5%最低干球温度对应湿球温度及出现时刻']

    return result_dict


if __name__ == '__main__':
    hourly_elements = 'PRS,TEM,RHU'
    hour_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,' + hourly_elements).split(',')
    hourly_df = pd.read_csv(cfg.FILES.QH_DATA_HOUR)
    hourly_df = hourly_df.loc[hourly_df['Station_Id_C'] == int(52866), hour_eles]
    hourly_df = hourly_data_processing(hourly_df)
    hourly_df['RHU'] = hourly_df['RHU'] / 100
    hourly_df = hourly_df[(hourly_df.index.year>=2000) & (hourly_df.index.year<=2020)]

    result = calc_nuclear_havc(hourly_df, interpolation=0)
