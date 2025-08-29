import functools
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_processing import daily_data_processing


def mann_kendall_mutation_test(df):
    '''
    MK突变点检验
    https://mp.weixin.qq.com/s/heonnS2lfEQSPz3Cnc0zvg
    https://mp.weixin.qq.com/s/GmUckn3SKfAmoXCVeJ7Iaw
    '''
    in_seq = df['要素值'].values
    n = in_seq.shape[0]
    NUMI = np.arange(2, n)
    E = NUMI * (NUMI - 1) / 4
    VAR = NUMI * (NUMI - 1) * (2 * NUMI + 5) / 72
    Ri = [(in_seq[i] > in_seq[1:i]).sum() for i in NUMI]
    Sk = np.cumsum(Ri)
    UFk = np.pad((Sk - E) / np.sqrt(VAR), (2, 0))
    Bk = np.cumsum([(in_seq[i] > in_seq[i:-1]).sum() for i in -(NUMI + 1)])
    UBk = np.pad((-(Bk - E) / np.sqrt(VAR)), (2, 0))[::-1]

    # 找出交叉点 (突变位置)
    point_idx = []
    diff = UFk - UBk
    for k in range(1, n):
        if diff[k - 1] * diff[k] < 0:
            point_idx.append(k)

    mutation_year = df.loc[point_idx, '年份'].tolist()
    if len(mutation_year) == 0:
        mutation_year = None

    df_out = df.copy()
    df_out['UFk'] = UFk.round(5)
    df_out['UBk'] = UBk.round(5)
    df_out.drop(columns='要素值', inplace=True)

    return df_out, mutation_year

# 画图
# path = r'C:/Users/MJY/Desktop/data.xlsx'
# df_mean = pd.read_excel(path,sheet_name='mean')
# df1 = df_mean[['iyear','祁连山区']]
# df1.columns = ['年份','要素值']
# df2 = df_mean[['iyear','阿尼玛卿']]
# df2.columns = ['年份','要素值']
# df3 = df_mean[['iyear','各拉丹东']]
# df3.columns = ['年份','要素值']

# df_max = pd.read_excel(path,sheet_name='max')
# df4 = df_max[['iyear','祁连山区']]
# df4.columns = ['年份','要素值']
# df5 = df_max[['iyear','阿尼玛卿']]
# df5.columns = ['年份','要素值']
# df6 = df_max[['iyear','各拉丹东']]
# df6.columns = ['年份','要素值']

# df_min = pd.read_excel(path,sheet_name='min')
# df7 = df_min[['iyear','祁连山区']]
# df7.columns = ['年份','要素值']
# df8 = df_min[['iyear','阿尼玛卿']]
# df8.columns = ['年份','要素值']
# df9 = df_min[['iyear','各拉丹东']]
# df9.columns = ['年份','要素值']

# df_out, mutation_year = mann_kendall_mutation_test(df3)

# # 画图
# plt.figure(figsize=(8, 6), dpi=200)
# plt.plot(range(62), df_out['UFk'],  label='UF', color='blue', marker='s',markersize=4)
# plt.plot(range(62), df_out['UBk'], label='UB', color='red', linestyle='--', marker='o',markersize=4)
# ax1 = plt.gca()
# ax1.set_ylabel('统计量',fontname='MicroSoft YaHei', fontsize=10)
# ax1.set_xlabel('年份',fontname='MicroSoft YaHei', fontsize=10)
# plt.xlim(-1,62)             # 设置x轴、y轴范围
# # plt.ylim(-3,5)

# # 添加辅助线
# x_lim = plt.xlim()
# # 添加显著水平线和y=0
# plt.plot(x_lim,[-1.96,-1.96],':',color='green',label='0.05显著性水平')
# plt.plot(x_lim, [0,0],'-',color='black')
# plt.plot(x_lim,[1.96,1.96],':',color='green')
# plt.xticks(list(range(0,62,3)),labels=df_out['年份'][::3], rotation=45)

# # 设置图例
# legend = plt.legend(bbox_to_anchor=(0.3, 0.2))
# legend.get_frame().set_facecolor('white')  # 设置背景颜色为白色
# legend.get_frame().set_edgecolor('black')  # 设置边框颜色为黑色
# for text in legend.get_texts():
#     text.set_fontsize(12)  # 设置字体大小
#     text.set_fontfamily('MicroSoft YaHei')  # 设置字体名称

# plt.savefig("C:/Users/MJY/Desktop/result/1.png", dpi=300, bbox_inches='tight')
# plt.show()


def slide_t_test(df, step, p=0.05):
    '''
    Slide-T检验
    '''
    in_seq = df['要素值'].values
    n = in_seq.shape[0]
    t = np.zeros(n)
    t1 = np.empty(n)
    n1 = step
    n2 = step
    n11 = 1 / n1
    n22 = 1 / n2
    m = np.sqrt(n11 + n22)
    for i in range(step, n - step - 1):
        x1_mean = np.mean(in_seq[i - step:i])
        x2_mean = np.mean(in_seq[i:i + step])
        s1 = np.mean(in_seq[i - step:i])
        s2 = np.mean(in_seq[i:i + step])
        s = np.sqrt((n1 * s1 + n2 * s2) / (n1 + n2 - 2))
        t[i - step] = (x2_mean - x1_mean) / (s * m)
        t1 = np.roll(t, step - 1)
        t1[:step] = np.nan
        t1[n - step + 1:] = np.nan

    v = step + step - 2  # 自由度v
    tab = pd.read_csv(cfg.FILES.T_DISTR_TABLE, header=0, encoding='gbk')
    threshold = tab['P' + str(p)][tab['自由度'] == v].values

    t_abs = np.abs(t1)
    point_idx = []
    for i in range(len(t_abs)):
        if t_abs[i] > threshold:
            point_idx.append(i)

    mutation_year = df.loc[point_idx, '年份'].tolist()
    if len(mutation_year) == 0:
        mutation_year = None

    df_out = df.copy()
    df_out['滑动T检验统计值'] = t1.round(5)
    df_out.drop(columns='要素值', inplace=True)

    return df_out, mutation_year


# def slide_t_test(df, step, p=0.05):
#     '''
#     Slide-T检验
#     https://mp.weixin.qq.com/s/HCLZrtFo8Tp7Xe_KEwvcrQ
#     '''
#     in_seq = df['要素值'].values
#     n = in_seq.shape[0]

#     n1 = step
#     n2 = step
#     v = step + step - 2  # 自由度v
#     tab = pd.read_csv(cfg.FILES.T_DISTR_TABLE, header=0, encoding='gbk')
#     ttest = tab['P' + str(p)][tab['自由度'] == v].values

#     t = []
#     for i in range(0, n-step-step+1):
#         x1 = in_seq[i:i+step]
#         x2 = in_seq[i+step:i+step+step]
#         meanx1 = np.mean(x1)
#         meanx2 = np.mean(x2)
#         a = meanx1-meanx2
#         b = (n1+n2)/(n1*n2)
#         varx1 = np.var(x1)
#         varx2 = np.var(x2)
#         c = (n1*varx1+n2*varx2)/(n1+n2-2)
#         t1 = a/np.sqrt(c*b)
#         t = np.append(t,t1)

#     t_abs = np.abs(t)
#     point_idx = []

#     for i in range(len(t_abs)):
#         if t_abs[i] > ttest:
#             point_idx.append(i)

#     mutation_year = df.loc[point_idx, '年份'].tolist()
#     df_out = df.copy()
#     df_out.loc['t统计量'] = t.round(5)
#     df_out.drop(columns='要素值',inplace=True)

#     return df_out, mutation_year


def time_analysis(df_day, elements, method, station_ids, seq_len):
    '''
    包含MK和滑动T，另外一种输出个格式
    '''
    # 生成elements对应的中文列表
    replace_dict = {'PRS_Avg': '平均气压', 
                    'PRS_Max': '最高气压', 
                    'PRS_Min': '最低气压', 
                    'TEM_Avg': '平均气温', 
                    'TEM_Min': '最低气温', 
                    'TEM_Max': '最高气温', 
                    'RHU_Avg': '平均湿度', 
                    'PRE_Time_2020': '降水量', 
                    'WIN_S_2mi_Avg': '平均风速', 
                    'WIN_S_Max': '最大风速'}

    # 判断[2000, 2001, 2002]是否是连续年
    def is_serial(arr):
        if arr is None or len(arr) == 0:
            return False
        return functools.reduce(lambda x, y: (x + 1 == y if isinstance(x, int) else x[0] and x[1] + 1 == y, y), arr)[0]

    all_result = edict()
    for ids in station_ids:
        all_result[ids] = edict()
        data = df_day[df_day['Station_Id_C'] == ids]

        for ele in elements:
            ele_ch = replace_dict[ele]
            all_result[ids][ele_ch] = edict()
            data_tmp = data[ele].to_frame()

            if ele in ['TEM_Avg', 'PRS_Avg', 'RHU_Avg', 'WIN_S_2mi_Avg']:
                data_tmp = data_tmp.resample('1A').mean().round(1)
            elif ele in ['TEM_Max', 'PRS_Max', 'WIN_S_Max']:
                data_tmp = data_tmp.resample('1A').max().round(1)
            elif ele in ['TEM_Min', 'PRS_Min']:
                data_tmp = data_tmp.resample('1A').min().round(1)
            elif ele == 'PRE_Time_2020':
                data_tmp = data_tmp.resample('1A').sum().round(1)

            data_tmp = data_tmp.interpolate(method='linear', limit=5, limit_area='inside')  # 先线性插值 limit-要填充的连续NaN的最大数量
            data_tmp.dropna(how='any', inplace=True)  # 删除没有插到值的nan

            # 判断dropna后的年份是否连续+1，如果不连续，就不能进行突变检验
            year_list = list(data_tmp.index.year.unique())
            if (is_serial(year_list) == True) and (len(data_tmp) !=0):
                data_tmp.insert(loc=0, column='year', value=data_tmp.index.year)
                data_tmp.columns = ['年份', '要素值']
                data_tmp.reset_index(drop=True, inplace=True)
                all_result[ids][ele_ch]['data'] = data_tmp.to_dict(orient='records')

                if 'mk' in method:
                    result_out, mutation_year = mann_kendall_mutation_test(data_tmp)
                    all_result[ids][ele_ch]['mk_result'] = result_out.to_dict(orient='records')
                    all_result[ids][ele_ch]['mutation_year_mk'] = mutation_year

                if 'slide_t' in method:
                    result_out, mutation_year = slide_t_test(data_tmp, seq_len, p=0.05)
                    all_result[ids][ele_ch]['t_result'] = result_out.to_dict(orient='records')
                    all_result[ids][ele_ch]['mutation_year_t'] = mutation_year

    return all_result


if __name__ == '__main__':

    elements = ["PRS_Avg","PRS_Max","PRS_Min","TEM_Avg","TEM_Max","TEM_Min","RHU_Avg","PRE_Time_2020","WIN_S_2mi_Avg","WIN_S_Max"]
    daily_elements = ','.join(elements)
    day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements).split(',')
    sta_ids = ["52866","52818","52853","52955","51886"]
    sta_ids_int = [52866,52818,52853,52955,51886]
    method = ['mk', 'slide_t']
    seq_len = 5
    daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    daily_df = daily_df.loc[daily_df['Station_Id_C'].isin(sta_ids_int), day_eles]
    daily_df = daily_data_processing(daily_df)
    all_result = time_analysis(daily_df, elements, method, sta_ids, seq_len)
