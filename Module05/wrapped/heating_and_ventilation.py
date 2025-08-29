import simplejson
import numpy as np
import pandas as pd
import metpy.calc as mcalc
from metpy.units import units
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_processing import hourly_data_processing, daily_data_processing, monthly_data_processing

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


def calc_heating_and_ventilation(df_monthly, df_daily, df_hourly):
    '''
    基于《工业建筑供暖通风与空气调节设计规范》（GB 50019-2015）重做 20231127
    计算供暖通风及室外空气参数，采用小时/日/月数据
    1-9 室外计算温、湿度
    10-19 风向、风速及频率
    20 冬季日照百分率
    21 最大冻土深度(cm)
    22-23 大气压力
    24-29 设计计算用供暖期天数及其平均温度
    30-35 极端参数
    '''
    df_hourly = df_hourly[['PRS', 'TEM', 'RHU']]
    df_hourly = df_hourly.interpolate(method='spline', order=3)
    hour_start_year = df_hourly.index.year[0]

    # 1.冬季采暖室外计算温度 (使用日数据)
    '''
    在用于统计的年份(n年)中，将所有年份的日平均温度由小到大进行排序，
    选择第5n+1个数值作为供暖室外计算温度，累年不保证5n天，即累年平均每年不保证5天。
    '''
    try:
        num_years = len(df_daily.index.year.unique())
        result1 = df_daily['TEM_Avg'].sort_values(ascending=True)
        result1 = float(result1[5 * num_years])
        result1 = round(result1, 1)

    except:
        result1 = np.nan

    # 2.冬季通风室外计算温度 (使用月数据)
    '''
    在用于统计的年份(n年)中，分别选出每年最冷月的月平均温度，
    即得到n个月平均温度，将n个月平均温度进行平均即为冬季通风室外计算温度。
    '''
    try:
        tem_yearly = df_monthly['TEM_Avg'].resample('1A', closed='right', label='right').min().values
        result2 = float(tem_yearly.mean())
        result2 = round(result2, 1)

    except:
        result2 = np.nan

    # 3.冬季空气调节室外计算温度 (使用日数据)
    '''
    在用于统计的年份(n年)中，将所有年份的日平均温度由小到大进行排序，
    选择第n+1个数值作为供暖室外计算温度，累年不保证n天，即累年平均每年不保证1天。
    '''
    try:
        num_years = len(df_daily.index.year.unique())
        result3 = df_daily['TEM_Avg'].sort_values(ascending=True)
        result3 = float(result3[num_years])
        result3 = round(result3, 1)

    except:
        result3 = np.nan

    # 4.冬季空气调节室外计算相对湿度 (使用月数据)
    '''
    在用于统计的年份(n年)中，分别选出每年最冷月，即得到n个月，
    将n个月的平均相对湿度进行平均即为冬季空气调节室外计算相对湿度。
    '''
    try:
        sample_data = df_monthly[['TEM_Avg', 'RHU_Avg']]
        month_idx = sample_data.groupby(sample_data.index.year)['TEM_Avg'].idxmin().reset_index(name='index')
        time_idx = month_idx['index'].tolist()

        val = sample_data.loc[time_idx]
        result4 = val['RHU_Avg'].mean()
        result4 = round(result4, 1)

    except:
        result4 = np.nan

    # 5.夏季空气调节室外计算干球温度 (使用小时数据)
    '''
    在用于统计的年份(n年)中，将所有年份的逐时温度由大到小进行排序，
    选择第50n+1个数值作为夏季空气调节室外计算干球温度，累年不保证50nh，即累年平均每年不保证50h。
    '''
    try:
        # 逐日数据转换为逐小时数据 并由大到小排序
        num_years = len(df_hourly.index.year.unique())
        sample_data = df_hourly['TEM'].sort_values(ascending=False)
        result5 = float(sample_data[50 * num_years])
        result5 = round(result5, 1)

    except:
        result5 = np.nan

    # 6.夏季空气调节室外计算湿球温度 (使用小时数据)
    '''
    在用于统计的年份(n年)中，将所有年份的逐时湿球温度由大到小进行排序，
    选择第50n+1个数值作为夏季空气调节室外计算湿球温度，累年不保证50nh，即累年平均每年不保证50h。
    '''
    try:
        tmp = df_hourly[df_hourly['TEM'] > 25]
        num_years = len(df_hourly.index.year.unique())
        dewpoint = calc_dewpoint_temperature_with_rh(tmp['TEM'], tmp['RHU'])  # 计算露点
        wbt = calc_wet_bulb_temperature(tmp['PRS'], tmp['TEM'], dewpoint)  # 计算整个序列的湿球温度
        result6 = np.sort(wbt)[::-1]  # 从大到小排序
        result6 = float(result6[50 * num_years])
        result6 = round(result6, 1)

    except:
        result6 = np.nan

    # 7.夏季通风室外计算温度 (使用月数据+小时数据)
    '''
    在用于统计的年份(n年)中，分别选出每年最热月，即得到n个月，
    将n个月的逐日14时的温度进行平均，即为夏季通风室外计算温度。
    '''
    try:
        sample_data = df_monthly['TEM_Avg'].to_frame()
        sample_data = sample_data[sample_data.index.year>=hour_start_year] # 针对青海项目，处理小时数据和月数据年份不一致的情况
        hotest_idx = sample_data.groupby(sample_data.index.year).idxmax().reset_index()
        time_idx = hotest_idx['TEM_Avg'].dt.strftime("%Y-%m").tolist()  # 每年最高平均气温的月份
        hourly_data = df_hourly['TEM'].to_frame()

        for i in range(len(time_idx)):
            data = hourly_data.loc[time_idx[i]]  # 每年最高气温的月份的所有小时数据

            if i == 0:
                final_data = data
            else:
                final_data = pd.concat([final_data, data], axis=0)

        hour_mean = final_data.groupby(final_data.index.hour).mean().reset_index()
        result7 = float(hour_mean.loc[14, 'TEM'])
        result7 = round(result7, 1)

    except:
        result7 = np.nan

    # 8.夏季通风室外计算相对湿度 (使用月数据+小时数据)
    '''
    在用于统计的年份(n年)中，分别选出每年最热月，即得到n个月，
    将n个月的逐日14时的相对湿度进行平均即为夏季通风室外计算相对湿度。
    '''
    try:
        sample_data = df_monthly['TEM_Avg'].to_frame()
        sample_data = sample_data[sample_data.index.year>=hour_start_year] # 针对青海项目，处理小时数据和月数据年份不一致的情况
        hotest_idx = sample_data.groupby(sample_data.index.year).idxmax().reset_index()
        time_idx = hotest_idx['TEM_Avg'].dt.strftime("%Y-%m").tolist()  # 每年最高平均温度的月份
        hourly_rh_data = df_hourly['RHU'].to_frame()

        for i in range(len(time_idx)):
            data = hourly_rh_data.loc[time_idx[i]]  # 每年最高平均湿度的月份的所有小时数据

            if i == 0:
                final_data = data
            else:
                final_data = pd.concat([final_data, data], axis=0)

        hour_rh_mean = final_data.groupby(final_data.index.hour).mean().reset_index()
        result8 = float(hour_rh_mean.loc[14, 'RHU'])
        result8 = round(result8, 1)

    except:
        result8 = np.nan

    # 9.夏季空气调节室外计算日平均温度 (使用日数据)
    '''
    在用于统计的年份(n年)中，将所有年份的日平均温度由大到小进行排序，
    选择第5n+1个数值作为夏季空气调节室外计算日平均温度，累年不保证5nd，即累年平均每年不保证5d。
    '''
    try:
        num_years = len(df_daily.index.year.unique())
        result9 = df_daily['TEM_Avg'].sort_values(ascending=False)
        result9 = float(result9[5 * num_years])
        result9 = round(result9, 1)

    except:
        result9 = np.nan

    # 10.夏季室外平均风速 (使用月数据)
    '''
    应采用累年最热3个月，各月平均风速的平均值
    '''
    try:
        sample_data = df_monthly['TEM_Avg'].nlargest(3)
        time_idx = sample_data.index  # 相应的index
        wind_data = df_monthly['WIN_S_2mi_Avg']
        result10 = wind_data[time_idx].mean()
        result10 = round(result10, 1)

    except:
        result10 = np.nan

    # 11~12.夏季最多风向/夏季最多风向的频率 (使用月数据)
    '''
    应采用累年最热3个月的最多风向及其平均频率
    '''
    try:
        sample_data = df_monthly['TEM_Avg'].nlargest(3)
        time_idx = sample_data.index  # 相应的index
        time_idx = time_idx.strftime("%Y-%m").tolist()  # 相应的index 年-月

        # 提取最热三个月的所有月数据
        for i in range(len(time_idx)):
            data = df_monthly.loc[time_idx[i]]

            if i == 0:
                final_data = data
            else:
                final_data = pd.concat([final_data, data], axis=0)

        # 找到三个月最大的风向
        wind_d_freq = final_data[[
            'WIN_NNE_Freq', 'WIN_NE_Freq', 'WIN_ENE_Freq', 'WIN_E_Freq', 'WIN_ESE_Freq', 'WIN_SE_Freq', 'WIN_SSE_Freq', 'WIN_S_Freq', 'WIN_SSW_Freq', 'WIN_SW_Freq', 'WIN_WSW_Freq', 'WIN_W_Freq', 'WIN_WNW_Freq', 'WIN_NW_Freq', 'WIN_NNW_Freq',
            'WIN_N_Freq'
        ]]

        # 统计这三个月的风向频数
        result12 = wind_d_freq.max().max()  # 风速
        result11 = wind_d_freq.max().idxmax()  # 风向

        # freq_sum = wind_d_freq.sum()
        # result11 = freq_sum.idxmax()  # 风向
        # result12 = float((freq_sum[result11] / freq_sum.sum()) * 100)  # 频率
        # result12 = round(result12,1)
        result11 = result11.split('_')[1]

    except:
        result11 = np.nan
        result12 = np.nan

    # 13.夏季室外最多风向的平均风速 (使用月数据)
    '''
    应采用累年最热3个月最多风向(静风除外)的各月平均风速的平均值。
    '''
    try:
        sample_data = df_monthly['TEM_Avg'].nlargest(3)
        time_idx = sample_data.index  # 相应的index
        time_idx = time_idx.strftime("%Y-%m").tolist()  # 相应的index 年-月

        # 提取最热三个月的所有月数据
        for i in range(len(time_idx)):
            data = df_monthly.loc[time_idx[i]]  # 每年最低气温的月份的所有日数据

            if i == 0:
                final_data = data
            else:
                final_data = pd.concat([final_data, data], axis=0)

        # 找到三个月最大的风向
        wind_d_freq = final_data[[
            'WIN_NNE_Freq', 'WIN_NE_Freq', 'WIN_ENE_Freq', 'WIN_E_Freq', 'WIN_ESE_Freq', 'WIN_SE_Freq', 'WIN_SSE_Freq', 'WIN_S_Freq', 'WIN_SSW_Freq', 'WIN_SW_Freq', 'WIN_WSW_Freq', 'WIN_W_Freq', 'WIN_WNW_Freq', 'WIN_NW_Freq', 'WIN_NNW_Freq',
            'WIN_N_Freq'
        ]]

        max_freq_column = wind_d_freq.sum().idxmax()
        max_spd_column = 'WIN_S_Avg_' + max_freq_column.split('_')[1]  # 最大风向对应的风速列名
        result13 = final_data[max_spd_column].mean()
        result13 = round(result13, 1)

    except:
        result13 = np.nan

    # 14.冬季室外平均风速 (使用月数据)
    '''
    应采用累年最冷3个月，各月平均风速的平均值 (全部月份里面找3个月)
    '''
    try:
        sample_data = df_monthly['TEM_Avg'].nsmallest(3)  # 最冷三个月的平均气温
        time_idx = sample_data.index  # 相应的index
        wind = df_monthly['WIN_S_2mi_Avg'].to_frame()
        result14 = float(wind.loc[time_idx].mean().values[0])
        result14 = round(result14, 1)

    except:
        result14 = np.nan

    # 15~16.冬季最多风向/冬季最多风向的频率 (使用月数据)
    '''
    应采用累年最冷3个月的最多风向及其平均频率
    '''
    try:
        sample_data = df_monthly['TEM_Avg'].nsmallest(3)
        time_idx = sample_data.index  # 相应的index
        time_idx = time_idx.strftime("%Y-%m").tolist()  # 相应的index 年-月

        # 提取最冷三个月的所有月数据
        for i in range(len(time_idx)):
            data = df_monthly.loc[time_idx[i]]  # 每年最低气温的月份的所有日数据

            if i == 0:
                final_data = data
            else:
                final_data = pd.concat([final_data, data], axis=0)

        # 找到三个月最大的风向
        wind_d_freq = final_data[[
            'WIN_NNE_Freq', 'WIN_NE_Freq', 'WIN_ENE_Freq', 'WIN_E_Freq', 'WIN_ESE_Freq', 'WIN_SE_Freq', 'WIN_SSE_Freq', 'WIN_S_Freq', 'WIN_SSW_Freq', 'WIN_SW_Freq', 'WIN_WSW_Freq', 'WIN_W_Freq', 'WIN_WNW_Freq', 'WIN_NW_Freq', 'WIN_NNW_Freq',
            'WIN_N_Freq'
        ]]

        # 统计这三个月的风向频数
        freq_sum = wind_d_freq.sum()
        result15 = freq_sum.idxmax()  # 风向
        result16 = float((freq_sum[result15] / freq_sum.sum()) * 100)  # 频率
        result16 = round(result16, 1)
        result15 = result15.split('_')[1]

    except:
        result15 = np.nan
        result16 = np.nan

    # 17.冬季室外最多风向的平均风速 (使用月数据)
    '''
    应采用累年最冷3个月最多风向(静风除外)的各月平均风速的平均值
    '''
    try:
        sample_data = df_monthly['TEM_Avg'].nsmallest(3)  # 最冷三个月的平均气温
        time_idx = sample_data.index  # 相应的index
        time_idx = time_idx.strftime("%Y-%m").tolist()  # 把相应的index转化为'年-月'形式

        # 提取最冷三个月的所有月数据
        for i in range(len(time_idx)):
            data = df_monthly.loc[time_idx[i]]  # 每年最低气温的月份的所有日数据

            if i == 0:
                final_data = data
            else:
                final_data = pd.concat([final_data, data], axis=0)

        # 找到三个月最大的风向
        wind_d_freq = final_data[['WIN_NNE_Freq', 'WIN_NE_Freq', 'WIN_ENE_Freq', 'WIN_E_Freq', 
                                  'WIN_ESE_Freq', 'WIN_SE_Freq', 'WIN_SSE_Freq', 'WIN_S_Freq', 
                                  'WIN_SSW_Freq', 'WIN_SW_Freq', 'WIN_WSW_Freq', 'WIN_W_Freq', 
                                  'WIN_WNW_Freq', 'WIN_NW_Freq', 'WIN_NNW_Freq', 'WIN_N_Freq']]

        max_freq_column = wind_d_freq.sum().idxmax()
        max_spd_column = 'WIN_S_Avg_' + max_freq_column.split('_')[1]  # 最大风向对应的风速列名
        result17 = final_data[max_spd_column].mean()
        result17 = round(result17, 1)

    except:
        result17 = np.nan

    # 18~19.年最多风向/年最多风向的频率 (使用月数据)
    '''
    应采用累年最多风向及其平均频率
    '''
    try:
        wind_d_freq = df_monthly[['WIN_NNE_Freq', 'WIN_NE_Freq', 'WIN_ENE_Freq', 'WIN_E_Freq', 
                                  'WIN_ESE_Freq', 'WIN_SE_Freq', 'WIN_SSE_Freq', 'WIN_S_Freq', 
                                  'WIN_SSW_Freq', 'WIN_SW_Freq', 'WIN_WSW_Freq', 'WIN_W_Freq', 
                                  'WIN_WNW_Freq', 'WIN_NW_Freq', 'WIN_NNW_Freq', 'WIN_N_Freq']]

        # 统计这风向频数
        freq_sum = wind_d_freq.sum()
        result18 = freq_sum.idxmax()  # 风向
        result19 = float((freq_sum[result18] / freq_sum.sum()) * 100)  # 频率
        result19 = round(result19, 1)
        result18 = result18.split('_')[1]

    except:
        result18 = np.nan
        result19 = np.nan

    # 20.冬季日照百分率 (使用月数据)
    '''
    应采用累年最冷3个月，各月平均日照百分率的平均值
    '''
    try:
        sample_data = df_monthly['TEM_Avg'].nsmallest(3)  # 最冷三个月的平均气温
        time_idx = sample_data.index  # 相应的index
        ssp = df_monthly['SSP_Mon'].to_frame()
        result20 = float(ssp.loc[time_idx].mean().values[0])
        result20 = round(result20, 1)

    except:
        result20 = np.nan

    # 21.最大冻土深度 (使用月数据)
    '''
    月最大冻土深度算累年最大
    '''
    try:
        result21 = df_monthly['FRS_Depth_Max'].resample('1A').max().values
        result21 = result21.max()

    except:
        result21 = np.nan

    # 22.冬季室外大气压力 (使用月数据)
    '''
    应采用累年最冷3个月各月平均大气压力的平均值
    '''
    try:
        sample_data = df_monthly['TEM_Avg'].nsmallest(3)  # 最冷三个月的平均气温
        time_idx = sample_data.index  # 相应的index
        sample_prs = df_monthly['PRS_Avg'].to_frame()
        result22 = float(sample_prs.loc[time_idx].mean().values[0])
        result22 = round(result22, 1)

    except:
        result22 = np.nan

    # 23.夏季室外大气压力 (使用月数据)
    '''
    应采用累年最热3个月各月平均大气压力的平均值
    '''
    try:
        sample_data = df_monthly['TEM_Avg'].nlargest(3)
        time_idx = sample_data.index  # 相应的index
        sample_prs = df_monthly['PRS_Avg'].to_frame()
        result23 = float(sample_prs.loc[time_idx].mean().values[0])
        result23 = round(result23, 1)

    except:
        result23 = np.nan

    # 24~26.日平均气温≤+5.0℃的天数/日平均温度≤+5℃的起止日期/平均温度≤+5℃期间内的平均温度(℃) (使用日数据)
    '''
    对历年10月至5月的日平均气温进行逐日求对应日的平均，即可得到日平均气温≤+5.0℃的天数及其起止日期。
    '''
    try:
        sample_data = df_daily.loc[~((df_daily.index.month > 5) & (df_daily.index.month < 10)), 'TEM_Avg']
        tem_year = sample_data.groupby([sample_data.index.month, sample_data.index.day]).mean()
        result24 = int((tem_year <= 5).sum(axis=0))

        start = tem_year[(10, 1):]
        start = pd.DataFrame(start)
        start_idx = start[start['TEM_Avg'] <= 5].index.tolist()[0]
        result25_start_time = str(start_idx[0]) + '-' + str(start_idx[1])

        end = tem_year[:(5, 31)]
        end = pd.DataFrame(end)
        end_idx = end[end['TEM_Avg'] <= 5].index.tolist()[-1]
        result25_end_time = str(end_idx[0]) + '-' + str(end_idx[1])
        result25 = ','.join([result25_start_time, result25_end_time])
        result26 = pd.concat([tem_year[start_idx:(12, 31)], tem_year[(1, 1):end_idx]], axis=0).mean().round(1)

    except:
        result24 = np.nan
        result25 = np.nan
        result26 = np.nan

    # 27~29.日平均气温≤+8.0℃的天数/日平均温度≤+8℃的起止日期/平均温度≤+8℃期间内的平均温度(℃) (使用日数据)
    '''
    对历年10月至5月的日平均气温进行逐日求对应日的平均，即可得到日平均气温≤+8.0℃的天数及其起止日期。
    '''
    try:
        sample_data = df_daily.loc[~((df_daily.index.month > 5) & (df_daily.index.month < 10)), 'TEM_Avg']
        tem_year = sample_data.groupby([sample_data.index.month, sample_data.index.day]).mean()
        result27 = int((tem_year <= 8).sum(axis=0))

        start = tem_year[(10, 1):]
        start = pd.DataFrame(start)
        start_idx = start[start['TEM_Avg'] <= 8].index.tolist()[0]
        result28_start_time = str(start_idx[0]) + '-' + str(start_idx[1])

        end = tem_year[:(5, 31)]
        end = pd.DataFrame(end)
        end_idx = end[end['TEM_Avg'] <= 8].index.tolist()[-1]
        result28_end_time = str(end_idx[0]) + '-' + str(end_idx[1])
        result28 = ','.join([result28_start_time, result28_end_time])
        result29 = pd.concat([tem_year[start_idx:(12, 31)], tem_year[(1, 1):end_idx]], axis=0).mean().round(1)

    except:
        result27 = np.nan
        result28 = np.nan
        result29 = np.nan

    # 30.极端最高气温 (使用日数据)
    '''
    应选择累年逐日最高温度的最高值
    '''
    try:
        tem_max = df_daily['TEM_Max']
        result30 = tem_max.max()

    except:
        result30 = np.nan

    # 31.极端最低气温 (使用日数据)
    '''
    应选择累年逐日最低温度的最低值
    '''
    try:
        tem_min = df_daily['TEM_Min']
        result31 = tem_min.min()

    except:
        result31 = np.nan

    # 32.历年极端最高气温平均值 (使用日数据)
    '''
    在用于统计的年份(n年)中，选择逐年的极端最高温度，
    得到n个极端最高温度进行平均得到历年极端最高气温平均值。
    '''
    try:
        tem_max = df_daily['TEM_Max'].resample('1A', closed='right', label='right').max()
        result32 = float(np.nanmean(tem_max.values))
        result32 = round(result32, 1)

    except:
        result32 = np.nan

    # 33.历年极端最低气温平均值 (使用日数据)
    '''
    在用于统计的年份（n年）中，选择逐年的极端最低温度，
    得到n个极端最低温度进行平均得到历年极端最低气温平均值。
    '''
    try:
        tem_min = df_daily['TEM_Min'].resample('1A', closed='right', label='right').min()
        result33 = float(np.nanmean(tem_min.values))
        result33 = round(result33, 1)

    except:
        result33 = np.nan

    # 34.累年最低日平均温度 (使用日数据)
    '''
    在用于统计的年份(n年)中，选择所有日平均温度的最低值即为累年最低日平均温度。
    '''
    try:
        tem_min = df_daily['TEM_Avg'].resample('1A', closed='right', label='right').min()
        result34 = float(np.nanmean(tem_min.values))
        result34 = round(result34, 1)

    except:
        result34 = np.nan

    # 35.累年最热月平均相对湿度 (使用月数据)
    '''
    在用于统计的年份(n年)中，选择所有月平均温度最高的月份，
    此月的平均相对湿度即为累年最热月平均相对湿度。
    '''
    try:
        sample_data = df_monthly[['TEM_Avg', 'RHU_Avg']].resample('1M', closed='right', label='right').mean()
        month_idx = sample_data['TEM_Avg'].idxmax()
        result35 = float(sample_data.loc[month_idx]['RHU_Avg'])
        result35 = round(result35, 1)

    except:
        result35 = np.nan

    # 36.夏季室外计算平均日较差计算
    try:
        result36 = float((result5 - result9) / 0.52)
        result36 = round(result36, 1)

    except:
        result36 = np.nan

    # new
    # 37.设计计算用供暖期天数 (使用日数据)
    '''
    设计计算用供暖期天数应按累年日平均温度稳定低于或等于供暖室外临界温度的总日数确定；
    工业建筑供暖室外临界温度宜采用5℃。
    '''
    try:
        tem_year = df_daily.groupby([df_daily.index.month, df_daily.index.day])['TEM_Avg'].mean()
        tem_roll_5d = tem_year.rolling(5).mean().round(1)
        result37 = int((tem_roll_5d <= 5).sum(axis=0))

    except:
        result37 = np.nan

    # 38.夏季最热3个月干球温度 (使用月数据)
    '''
    计算历年最热3个月及其对应3个月的月平均干球温度（℃），求其平均值作为夏季最热3个月干球温度。
    '''
    try:
        sample_data = df_monthly['TEM_Avg'].to_frame()
        three_month = sample_data.groupby(sample_data.index.year)['TEM_Avg'].nlargest(3)
        result38 = three_month.mean().round(1)

    except:
        result38 = np.nan

    # 39.夏季最热3个月湿球温度 (使用月数据)
    '''
    计算历年最热3个月及其对应3个月的月平均湿球温度（℃），求其平均值作为夏季最热3个月湿球温度。
    '''
    try:
        sample_data = df_monthly[['TEM_Avg', 'PRS_Avg', 'RHU_Avg']]
        three_month = sample_data.groupby(sample_data.index.year)['TEM_Avg'].nlargest(3)
        idx = three_month.index.levels[1].strftime("%Y-%m").tolist()

        # 提取的最热三个月数据
        for i in range(len(idx)):
            data = df_monthly.loc[idx[i]]

            if i == 0:
                final_data = data
            else:
                final_data = pd.concat([final_data, data], axis=0)

        dewpoint = calc_dewpoint_temperature_with_rh(final_data['TEM_Avg'], final_data['RHU_Avg'])  # 计算露点
        wbt = calc_wet_bulb_temperature(final_data['PRS_Avg'], final_data['TEM_Avg'], dewpoint)  # 计算整个序列的湿球温度
        result39 = float(wbt.mean())
        result39 = round(result39, 1)

    except:
        result39 = np.nan

    # 40.极端最高气温及对应的湿球温度 (使用日数据)
    '''
    取建站以来极端最高气温（℃），该气温出现时间对应的日平均湿球温度（自动观测站无湿球温度观测时需插补订正）。
    '''
    try:
        max_tem_idx = df_daily['TEM_Max'].idxmax()
        sample_data = df_daily.loc[max_tem_idx, ['TEM_Avg', 'PRS_Avg', 'RHU_Avg']]
        dewpoint = calc_dewpoint_temperature_with_rh(sample_data['TEM_Avg'], sample_data['RHU_Avg'])  # 计算露点
        wbt = calc_wet_bulb_temperature([sample_data['PRS_Avg']], [sample_data['TEM_Avg']], dewpoint)  # 计算整个序列的湿球温度
        result40 = float(wbt)
        result40 = round(result40, 1)

    except:
        result40 = np.nan

    # 41.极端最低气温及对应的湿球温度 (使用日数据)
    '''
    取建站以来极端最低气温（℃），该气温出现时间对应的湿球温度（会因为结冰而缺测，可用插补值补充）。
    '''
    try:
        min_tem_idx = df_daily['TEM_Min'].idxmin()
        sample_data = df_daily.loc[min_tem_idx, ['TEM_Avg', 'PRS_Avg', 'RHU_Avg']]
        dewpoint = calc_dewpoint_temperature_with_rh(sample_data['TEM_Avg'], sample_data['RHU_Avg'])  # 计算露点
        wbt = calc_wet_bulb_temperature([sample_data['PRS_Avg']], [sample_data['TEM_Avg']], dewpoint)  # 计算整个序列的湿球温度
        result41 = float(wbt)
        result41 = round(result41, 1)

    except:
        result41 = np.nan

    # 42.最热月平均气温 (使用月数据)
    '''
    取历年最热月及月平均气温（℃），计算最热月的月平均气温平均值即为最热月平均气温
    '''
    try:
        sample_data = df_monthly['TEM_Avg'].to_frame()
        tem_year = sample_data.resample('1A', closed='right', label='right').max()
        result42 = float(tem_year.mean().values[0])
        result42 = round(result42, 1)

    except:
        result42 = np.nan

    # 汇总结果
    result_dict = edict()
    result_dict.result1 = result1
    result_dict.result2 = result2
    result_dict.result3 = result3
    result_dict.result4 = result4
    result_dict.result5 = result5
    result_dict.result6 = result6
    result_dict.result7 = result7
    result_dict.result8 = result8
    result_dict.result9 = result9
    result_dict.result10 = result10
    result_dict.result11 = result11
    result_dict.result12 = result12
    result_dict.result13 = result13
    result_dict.result14 = result14
    result_dict.result15 = result15
    result_dict.result16 = result16
    result_dict.result17 = result17
    result_dict.result18 = result18
    result_dict.result19 = result19
    result_dict.result20 = result20
    result_dict.result21 = result21
    result_dict.result22 = result22
    result_dict.result23 = result23
    result_dict.result24 = result24
    result_dict.result25 = result25
    result_dict.result26 = result26
    result_dict.result27 = result27
    result_dict.result28 = result28
    result_dict.result29 = result29
    result_dict.result30 = result30
    result_dict.result31 = result31
    result_dict.result32 = result32
    result_dict.result33 = result33
    result_dict.result34 = result34
    result_dict.result35 = result35
    result_dict.result36 = result36
    result_dict.result37 = result37
    result_dict.result38 = result38
    result_dict.result39 = result39
    result_dict.result40 = result40
    result_dict.result41 = result41
    result_dict.result42 = result42

    name_list = [
        '冬季采暖室外计算温度(℃)', '冬季通风室外计算温度(℃)', '冬季空气调节室外计算温度(℃)', '冬季空气调节室外计算相对湿度（%）', 
        '夏季空气调节室外计算干球温度(℃)', '夏季空气调节室外计算湿球温度(℃)', '夏季通风室外计算温度(℃)', '夏季通风室外计算相对湿度（%）', 
        '夏季空气调节室外计算日平均温度(℃)', '夏季室外平均风速(m/s)', '夏季最多风向', '夏季最多风向的频率(%)', '夏季室外最多风向的平均风速(m/s)',
        '冬季室外平均风速(m/s)', '冬季最多风向', '冬季最多风向的频率(%)', '冬季室外最多风向的平均风速(m/s)', '年最多风向', '年最多风向的频率(%)', 
        '冬季日照百分率(%)', '最大冻土深度(cm)', '冬季室外大气压力(hPa)', '夏季室外大气压力(hPa)', '日平均温度≤+5℃的天数', '日平均温度≤+5℃的起止日期', 
        '平均温度≤+5℃期间内的平均温度(℃)', '日平均温度≤+8℃的天数', '日平均温度≤+8℃的起止日期',
        '平均温度≤+8℃期间内的平均温度(℃)', '极端最高气温(℃)', '极端最低气温(℃)', '历年极端最高气温平均值(℃)', 
        '历年极端最低气温平均值(℃)', '累年最低日平均温度(℃)', '累年最热月平均相对湿度(%)', 
        '夏季室外计算平均日较差(℃)', '设计计算用供暖期天数(d)', '夏季最热3个月干球温度(℃)', '夏季最热3个月湿球温度(℃)', '极端最高气温及对应的湿球温度(℃)', '极端最低气温及对应的湿球温度(℃)',
        '最热月平均气温(℃)']
    
    info_list = ['应采用累年平均每年不保证5d的日平均温度','应采用历年最冷月月平均温度的平均值','应采用累年平均每年不保证1d的日平均温度',
                 '应采用历年最冷月月平均相对湿度的平均值','应采用累年平均每年不保证50h的干球温度','应采用累年平均每年不保证50h的湿球温度',
                 '应采用历年最热月14时平均温度的平均值','应采用历年最热月14时平均相对湿度的平均值','应采用累年平均每年不保证5天的日平均温度','应采用累年最热3个月各月平均风速的平均值',
                 '应采用累年最热3个月的最多风向','应采用累年最热3个月的最多风向的平均频率','应采用累年最热3个月最多风向(静风除外)的各月平均风速的平均值','应采用累年最冷3个月各月平均风速的平均值',
                 '应采用累年最冷3个月的最多风向','应采用累年最冷3个月的最多风向的平均频率','应采用累年最冷3个月最多风向(静风除外)的各月平均风速的平均值','应采用累年最多风向','应采用累年最多风向的平均频率',
                 '','','应采用累年最冷3个月各月平均大气压力的平均值','应采用累年最热3个月各月平均大气压力的平均值','应按累年日平均温度稳定低于或等于供暖室外临界温度的总日数确定',
                 '','','应按累年日平均温度稳定低于或等于供暖室外临界温度的总日数确定','','',
                 '应采用累年极端最高气温','应采用累年极端最低气温','应采用历年极端最高气温的平均值','应采用历年极端最低气温的平均值',
                 '应采用累年日平均温度中的最低值','应采用累年月平均温度最高的月份的平均相对湿度','','','','','','','']
    type_list = ['室外计算温、湿度']*9 + ['风向、风速及频率']*10 + ['日照、冻土']*2 + ['大气压力']*2 + ['设计计算用供暖期天数及其平均温度']*6 + ['极端参数']*6 + ['其他']*7

    df = pd.DataFrame(result_dict, index=[0]).T
    df.columns = ['参数']
    df['项目'] = name_list
    df['说明'] = info_list
    df['类别'] = type_list
    df = df[['类别','项目','参数','说明']]
    df = df.reset_index(drop=True)

    return df, df_hourly, result9, result36


def calc_summer_tem_and_enthalpy(df_hourly, result9, result36):
    '''
    计算夏季空调室外逐时温度，以及夏季空调室外逐时焓值
    夏季空调需要result9和result33
    注意，相对湿度为小数形式
    '''
    num_years = len(df_hourly.index.year.unique())

    # 1.夏季空调室外计算逐时温度
    beta = np.array([-0.26, -0.35, -0.38, -0.42, -0.45, -0.47, -0.41, -0.28, -0.12, 0.03, 0.16, 0.29, 0.40, 0.48, 0.52, 0.51, 0.43, 0.39, 0.28, 0.14, 0.00, -0.10, -0.17, -0.23]).reshape(-1, 1)  # 0-23时对应的数值
    t_sh = result9 + beta * result36
    t_sh = pd.DataFrame(t_sh, columns=['夏季空调室外计算逐时温度(°C)'])
    t_sh.insert(loc=0, column='小时', value=range(0, 24))
    t_sh = t_sh.round(1)

    # 2.夏季空调室外逐时计算焓值
    tem = df_hourly['TEM'].values
    tem_k = tem + 273.15
    lg_pb1 = -7.90298 * (373.16 / tem_k - 1) + 5.02808 * np.log10(373.16 / tem_k) - 1.3816e-7 * (np.power(10, 11.344 * (1 - tem_k / 373.16)) - 1) + 8.1328e-3 * (np.power(10, -3.49149 * (373.16 / tem_k - 1))) + np.log10(1013.246)
    pb1 = 10**(lg_pb1)
    lg_pb2 = -9.09718 * (273.16 / tem_k - 1) - 3.56654 * np.log10(273.16 / tem_k) + 0.876793 * (1 - tem_k / 273.16) + np.log10(6.1071)
    pb2 = 10**(lg_pb2)
    pb = np.where(tem_k > 273.15, pb1, pb2)
    d = (622 * df_hourly['RHU'] * pb) / (df_hourly['PRS'] - df_hourly['RHU'] * pb)
    h = 1.01 * df_hourly['TEM'] + 0.001 * d * (2500 + 1.84 * df_hourly['TEM'])

    h = h.to_frame()
    h.columns = ['焓值']

    enthalpy = []
    for i in range(0, 24):
        hour_i = h[h.index.hour == i]
        hour_i_summer = hour_i.sort_values(by='焓值', ascending=False)
        hour_i_summer.reset_index(inplace=True)
        enthalpy.append(hour_i_summer.loc[7 * num_years, '焓值'].round(1))

    enthalpy = pd.DataFrame(enthalpy, columns=['夏季空调室外逐时计算焓值(kJ/kg)'])
    enthalpy.insert(loc=0, column='小时', value=range(0, 24))
    enthalpy = enthalpy.round(1)

    return t_sh, enthalpy


if __name__ == '__main__':
    houly_df = pd.read_csv(cfg.FILES.QH_DATA_HOUR)
    daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    monthly_df = pd.read_csv(cfg.FILES.QH_DATA_MONTH, low_memory=False)
    
    houly_df = houly_df[houly_df['Station_Id_C']==52866]
    houly_df['Datetime'] = pd.to_datetime(houly_df['Datetime'])
    houly_df.set_index('Datetime', inplace=True)
    houly_df = houly_df[(houly_df.index.year >= 2010) & (houly_df.index.year <= 2022)]
    post_hourly_df = hourly_data_processing(houly_df, '2010,2022')
    post_hourly_df['RHU'] = post_hourly_df['RHU'] / 100

    daily_df = daily_df[daily_df['Station_Id_C']==52866]    
    daily_df['Datetime'] = pd.to_datetime(daily_df['Datetime'])
    daily_df.set_index('Datetime', inplace=True)
    daily_df = daily_df[(daily_df.index.year >= 2010) & (daily_df.index.year <= 2022)]
    post_daily_df = daily_data_processing(daily_df, '2010,2022')
    post_daily_df['RHU_Avg'] = post_daily_df['RHU_Avg'] / 100
    
    monthly_df = monthly_df[monthly_df['Station_Id_C']==52866]
    monthly_df['Datetime'] = pd.to_datetime(monthly_df['Datetime'])
    monthly_df.set_index('Datetime', inplace=True)
    monthly_df = monthly_df[(monthly_df.index.year >= 2010) & (monthly_df.index.year <= 2022)]
    post_monthly_df = monthly_data_processing(monthly_df, '2010,2022')
    post_monthly_df['RHU_Avg'] = post_monthly_df['RHU_Avg'] / 100
    
    df_dict, df_hourly, result9, result36 = calc_heating_and_ventilation(post_monthly_df, post_daily_df, post_hourly_df)
    t_sh, enthalpy = calc_summer_tem_and_enthalpy(df_hourly, result9, result36)