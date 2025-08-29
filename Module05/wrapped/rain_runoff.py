import simplejson
import numpy as np
import pandas as pd
from scipy import interpolate
from Utils.get_local_data import get_local_data
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
import matplotlib.pyplot as plt
from matplotlib.pyplot import MultipleLocator
from Utils.data_processing import daily_data_processing
import matplotlib
matplotlib.use('agg')


def rain_runoff_stats(df_daily, save_path):
    '''
    雨水年径流总量控制率与设计降雨深度
    使用降水日数据，不用进行缺失值处理
    
    输出：
    pre 用于画图
    pre_points 原型表1
    table 原型表2，同时用于画图
    '''
    # 1.生成原始排序后的数据 (降水事件和对应降水量)
    pre = df_daily['PRE_Time_2020'].to_frame().dropna()
    pre = pre[pre['PRE_Time_2020'] > 2]
    pre = pre[pre['PRE_Time_2020'] < 999]
    pre.columns = ['降水量(mm)']

    pre = pre.sort_values(by='降水量(mm)', ascending=True)
    pre.insert(loc=0, column='降水事件', value=range(len(pre)))
    pre.reset_index(drop=True, inplace=True)

    points = list(range(100, len(pre), 100))  # 每隔100个降雨事件
    pre_points = pre.loc[points, :]
    pre_points.reset_index(drop=True, inplace=True)
    pre_points = pre_points.round(1)

    # 2.雨水年径流总量控制率与设计降雨深度
    all_alpha = []
    H = pre['降水量(mm)'].max() * np.array(list(range(1, 1000))) * 0.001

    for h in H:
        closest = pre.iloc[(pre['降水量(mm)'] - h).abs().argsort(), :]
        num_pre = closest[closest['降水量(mm)'] > h].iloc[0, 0]  # 确定降水事件的次数断点
        c1 = pre.loc[pre['降水事件'] < num_pre, '降水量(mm)'].sum()
        c2 = (len(pre) - num_pre) * h
        alpha = (c1 + c2) / pre['降水量(mm)'].sum()
        all_alpha.append(alpha)

    all_alpha = np.array(all_alpha)  # 有可能不是递增的，后续插值作为x，需要保持递增
    data = np.concatenate((all_alpha.reshape(-1, 1), H.reshape(-1, 1)), axis=1)
    data = pd.DataFrame(data)
    data.sort_values(by=[0], ascending=[True], inplace=True)

    # 插值得到1%-100%
    interp = interpolate.CubicSpline(data[0], data[1])
    alpha_prob = np.arange(0.01, 1.01, 0.01).round(2).reshape(-1, 1)
    h_result = interp(alpha_prob).round(1)

    table = np.concatenate((alpha_prob*100, h_result), axis=1)
    table = pd.DataFrame(table, columns=['年径流总量控制率(%)', '设计降雨量(mm)'])
    table['年径流总量控制率(%)'] = table['年径流总量控制率(%)'].astype(int)
    
    points = table[table.index.isin([9, 19, 29, 39, 49, 59, 69, 79, 84, 89])]
    points['names'] = points['设计降雨量(mm)'].map(str) + ', ' + points['年径流总量控制率(%)'].map(str) + '%'
    
    # 画图
    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.grid(True)
    ax.xaxis.set_major_locator(MultipleLocator(5))
    ax.yaxis.set_major_locator(MultipleLocator(10))
    ax.set_xlabel('设计降雨量（mm）', fontsize=14)
    ax.set_ylabel('年径流总量控制率（%）', fontsize=14)
    ax.plot(table['设计降雨量(mm)'], table['年径流总量控制率(%)'], color='blue')
    ax.scatter(points['设计降雨量(mm)'], points['年径流总量控制率(%)'], marker='s', s=50)

    for i, j, k in list(zip(points['设计降雨量(mm)'].values, points['年径流总量控制率(%)'].values, points['names'].values)):
        ax.text(i + 6, j - 2, k, fontsize=12)

    save_path1 = save_path + '/result.png'
    plt.savefig(save_path1, dpi=300, bbox_inches='tight')
    plt.cla()
    plt.close('all')
    
    # 表格拆分
    # table1 = table[0:25].reset_index(drop=True)
    # table2 = table[25:50].reset_index(drop=True)
    # table3 = table[50:75].reset_index(drop=True)
    # table4 = table[75:100].reset_index(drop=True)
    # table = pd.concat([table1,table2,table3,table4],axis=1)
    
    return pre, pre_points, table, save_path1


if __name__ == '__main__':
    daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + 'PRE_Time_2020').split(',')
    years = '1960,2019'
    sta_ids = '56067'
    daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')
    path = r'C:/Users/MJY/Desktop/result'
    pre, pre_points, table, save_path1 = rain_runoff_stats(daily_df, path)





