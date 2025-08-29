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


def get_cdf_for_continuous_variable(data):
    '''
    对连续变量数据计算cdf，使用kde估计
    '''
    data = np.array(data)
    data_sort = np.sort(data)
    kde = stats.gaussian_kde(data_sort)
    cdf = np.vectorize(lambda x: kde.integrate_box_1d(-np.inf, x))
    data_cdf = cdf(data_sort)
    data_pdf = kde.evaluate(data_sort)
    return data_sort, data_cdf, data_pdf


def get_cdf_for_discrete_variable(data):
    '''
    对离散变量数据计算cdf
    '''
    data = np.array(data)
    data_sort = np.sort(data)
    data_cdf = []

    for val in data_sort:
        cum_val = sum([i for i in data if i <= val]) / sum(data)
        data_cdf.append(cum_val)

    data_cdf = np.array(data_cdf)

    return data_sort, data_cdf


# elements = [1.5, 2.2, 3.8]
# probabilities = [0.2, 0.5, 0.3]
# tt = np.random.choice(elements, 100, p=probabilities)
# data_cdf, data_sort = get_cdf_for_discrete_variable(tt)

# # 方法2
# n=len(tem)
# data = pd.Series(tem)
# fre = data.value_counts()
# fre_sort = fre.sort_index(axis=0, ascending=True)
# fre_df = fre_sort.reset_index()

# fre_df[0] = fre_df[0]/n #将频数转换成概率
# fre_df.columns = ['tem','Fre']
# fre_df['cumsum'] = np.cumsum(fre_df['Fre'])

# X = fre_df['cumsum'].values
# Y = fre_df['tem'].values
# new_x = np.arange(0.01,1.01,0.01) #定义差值点

# ipo1=spi.splrep(X,Y,k=3)
# iy11=spi.splev(new_x,ipo1)
# plt.plot(iy11,new_x)

# ######or####### 直接调用stats.relfreq
# res = stats.relfreq(final_data['日平均气温'], numbins=50)
# pdf_value = res.frequency
# cdf_value = np.cumsum(res.frequency)

# # 绘图
# x = res.lowerlimit + np.linspace(0, res.binsize*res.frequency.size, res.frequency.size)
# plt.plot(x, cdf_value)

# new_x = np.arange(0.01,1.01,0.01)
# ipo = interpolate.interp1d(cdf_value, x)
# result = ipo(new_x)
# plt.plot(result, new_x)


def calc_water_supply(input_df):
    '''
    给排水参数计算 使用日数据
    '''
    ######################################################
    # 1.夏季最热三个月累积频率为10%/5%/1%的日平均气温
    '''
    取夏季最热三个月累积频率为10%/5%/1%日平均气温及时间，
    同时可得到该时间对应的湿球温度及与其相对应的干球温度、气压、相对湿度
    先算10%的平均气温，然后找到和真实数据最邻近的时间，然后获得该时间的温度/气压/湿度，最后计算相应湿球温度
    '''
    sample_data = input_df[['TEM_Avg', 'PRS_Avg', 'RHU_Avg']]
    hot_month = sample_data['TEM_Avg'].resample('1M', closed='right', label='right').mean()

    hot_three_yearly = hot_month.groupby(hot_month.index.year).nlargest(3)  # 每年最高温度的三个月
    month_idx = hot_three_yearly.index.levels[1].strftime("%Y-%m").tolist()

    # 提取的最热三个月数据
    for i in range(len(month_idx)):
        data = sample_data.loc[month_idx[i]]

        if i == 0:
            final_data = data
        else:
            final_data = pd.concat([final_data, data], axis=0)

    # 气温CDF估计、插值
    tem_res = stats.relfreq(final_data['TEM_Avg'], numbins=50)
    tem_cdf = np.cumsum(tem_res.frequency)
    tem_data = tem_res.lowerlimit + np.linspace(0, tem_res.binsize * tem_res.frequency.size, tem_res.frequency.size)
    tem_prob = np.arange(0.01, 1.01, 0.01).reshape(-1, 1)
    interp = interpolate.interp1d(tem_cdf, tem_data, fill_value='extrapolate')
    tem_result = interp(tem_prob)

    # 找到累积频率气温对应的时间和真实数据
    freq_list = [9, 4, 0]  # 10%/5%/1%
    result_summer = []

    for freq in freq_list:
        freq_tem = float(tem_result[freq])
        df_sort = final_data.iloc[(final_data['TEM_Avg'] - freq_tem).abs().argsort(), :]
        closest_value = df_sort.iloc[0, 0]
        selected_df = final_data[final_data['TEM_Avg'] == closest_value]  # 与累积频率气温最邻近的真实气温df，并包含对应的气压和湿度

        # 计算湿球温度
        dewpoint = calc_dewpoint_temperature_with_rh(selected_df['TEM_Avg'], selected_df['RHU_Avg'])
        wbt = calc_wet_bulb_temperature(selected_df['PRS_Avg'], selected_df['TEM_Avg'], dewpoint)

        # 生成结果
        selected_df_cp = selected_df.copy()
        selected_df_cp['湿球温度'] = wbt
        selected_df_cp[str(freq + 1) + '%累积频率温度'] = freq_tem
        selected_df_cp['日期'] = selected_df_cp.index.strftime("%Y-%m-%d")
        selected_df_cp = selected_df_cp.reset_index(drop=True)
        result_summer.append(selected_df_cp)

    ######################################################
    # 2.冬季最冷三个月累积频率为99%日平均气温
    '''
    取冬季最冷三个月累积频率为99%日平均气温及时间，
    同时可得到该时间对应的湿球温度及与其相对应的干球温度、气压、相对湿度。
    '''
    sample_data = input_df[['TEM_Avg', 'PRS_Avg', 'RHU_Avg']]
    cold_month = sample_data['TEM_Avg'].resample('1M', closed='right', label='right').mean()

    cold_three_yearly = cold_month.groupby(cold_month.index.year).nsmallest(3)  # 每年最冷温度的三个月
    month_idx = cold_three_yearly.index.levels[1].strftime("%Y-%m").tolist()

    # 提取的最冷三个月数据
    for i in range(len(month_idx)):
        data = sample_data.loc[month_idx[i]]

        if i == 0:
            final_data = data
        else:
            final_data = pd.concat([final_data, data], axis=0)

    # 气温CDF估计、插值
    tem_res = stats.relfreq(final_data['TEM_Avg'], numbins=50)
    tem_cdf = np.cumsum(tem_res.frequency)
    tem_data = tem_res.lowerlimit + np.linspace(0, tem_res.binsize * tem_res.frequency.size, tem_res.frequency.size)
    tem_prob = np.arange(0.01, 1.01, 0.01).reshape(-1, 1)
    interp = interpolate.interp1d(tem_cdf, tem_data, fill_value='extrapolate')
    tem_result = interp(tem_prob)

    # 找到累积频率气温对应的时间和真实数据
    freq_tem = float(tem_result[98])

    df_sort = final_data.iloc[(final_data['TEM_Avg'] - freq_tem).abs().argsort(), :]
    closest_value = df_sort.iloc[0, 0]
    selected_df = final_data[final_data['TEM_Avg'] == closest_value]  # 与累积频率气温最邻近的真实气温df，并包含对应的气压和湿度

    # 计算湿球温度
    dewpoint = calc_dewpoint_temperature_with_rh(selected_df['TEM_Avg'], selected_df['RHU_Avg'])
    wbt = calc_wet_bulb_temperature(selected_df['PRS_Avg'], selected_df['TEM_Avg'], dewpoint)
    result_winter = selected_df.copy()
    result_winter['湿球温度'] = wbt
    result_winter['99%累积频率温度'] = freq_tem
    result_winter['日期'] = result_winter.index.strftime("%Y-%m-%d")
    result_winter = result_winter.reset_index(drop=True)

    # 3.历年最热三月/最冷三月 气温/气压/湿度
    sample_data = input_df[['TEM_Avg', 'PRS_Avg', 'RHU_Avg']]
    sample_data_month = sample_data['TEM_Avg'].resample('1M', closed='right', label='right').mean()

    hot_three_yearly = sample_data_month.groupby(sample_data_month.index.year).nlargest(3)
    hot_month_idx = hot_three_yearly.index.levels[1].strftime("%Y-%m").tolist()

    cold_three_yearly = sample_data_month.groupby(sample_data_month.index.year).nsmallest(3)
    cold_month_idx = cold_three_yearly.index.levels[1].strftime("%Y-%m").tolist()

    # 提取的最热/最冷三个月数据
    for i in range(len(hot_three_yearly)):
        hot_data = sample_data.loc[hot_month_idx[i]]
        cold_data = sample_data.loc[cold_month_idx[i]]

        if i == 0:
            hot_data_all = hot_data
            cold_data_all = cold_data

        else:
            hot_data_all = pd.concat([hot_data_all, hot_data], axis=0)
            cold_data_all = pd.concat([cold_data_all, cold_data], axis=0)

    hot_data_all['date'] = hot_data_all.index.strftime("%Y-%m-%d").tolist()
    hot_data_all = hot_data_all[['date', 'TEM_Avg', 'PRS_Avg', 'RHU_Avg']]
    hot_data_all.reset_index(drop=True, inplace=True)

    cold_data_all['date'] = cold_data_all.index.strftime("%Y-%m-%d").tolist()
    cold_data_all = cold_data_all[['date', 'TEM_Avg', 'PRS_Avg', 'RHU_Avg']]
    cold_data_all.reset_index(drop=True, inplace=True)

    ######################################################
    # 最终计算结果生成
    result_dict = edict()
    result_dict.result1 = result_summer[0].round(1).to_dict(orient='records')
    result_dict.result2 = result_summer[1].round(1).to_dict(orient='records')
    result_dict.result3 = result_summer[2].round(1).to_dict(orient='records')
    result_dict.result4 = result_winter.round(1).to_dict(orient='records')
    result_dict.result5 = hot_data_all.round(1).to_dict(orient='records')
    result_dict.result6 = cold_data_all.round(1).to_dict(orient='records')

    result_dict.note = [
        'result1-夏季最热三个月累积频率为10%日平均气温，及对应时间/真实气温/气压/湿度/湿球温度', 
        'result2-夏季最热三个月累积频率为5%日平均气温，及对应时间/真实气温/气压/湿度/湿球温度', 
        'result3-夏季最热三个月累积频率为1%日平均气温，及对应时间/真实气温/气压/湿度/湿球温度', 
        'result4-冬季最冷三个月累积频率为99%日平均气温，及对应时间/真实气温/气压/湿度/湿球温度', 
        'result5-历年最热三个月温度气压湿度',
        'result6-历年最冷三个月温度气压湿度']

    return result_dict


if __name__ == '__main__':

    daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    post_daily_df = daily_data_processing(daily_df)
    post_daily_df = post_daily_df[post_daily_df['Station_Id_C']=='52853']
    post_daily_df = post_daily_df[post_daily_df.index.year>=1994]
    df_day = post_daily_df[post_daily_df.index.year<=2023]
    df_day['RHU_Avg'] = df_day['RHU_Avg'] / 100
    df_day.dropna(inplace=True)
    
    result = calc_water_supply(df_day)
