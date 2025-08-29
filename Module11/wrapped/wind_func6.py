import os
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.pyplot import MultipleLocator
from scipy.stats import weibull_min
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Module11.wrapped.wind_dataloader import read_wind_tower

matplotlib.use('agg')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
    
def wind_stats6(data_dict):
    '''
    全风速段湍流强度
    风廓线
    阵风系数
    '''
    result = edict()

    for sta, sub_dict in data_dict.items():
        ws_df = sub_dict['ws_10'].filter(like='m_hour_ws')

        
    return result


if __name__ == '__main__':
    # ws_df = sub_dict['ws_10'].filter(like='m_hour_ws')
    # # 1.湍流强度(全风速段和15m/s风速)
    # tur = np.std(ws_df,ddof=1).values/ws_df.mean().values
    # tur = tur.reshape(1,-1).round(3)
    # tur15 = np.std(ws_df,ddof=1).values/15
    # tur15 = tur15.reshape(1,-1).round(3)
    # tur_concat = np.concatenate((tur,tur15),axis=0)
    # tur_concat = pd.DataFrame(tur_concat,columns=[col.split('_')[0] for col in ws_df.columns])
    # tur_concat.insert(loc=0, column='类型', value=['全风速段','15m/s'])
    
    # # 2.逐月湍流强度变化
    # tur_monthly = ws_df.resample('1M').apply(lambda x: (np.std(x,ddof=1)/x.mean()).round(3))
    # tur_monthly.columns = [col.split('_')[0] for col in tur_monthly.columns]
    # tur_monthly.insert(loc=0, column='时间', value=tur_monthly.index.strftime('%Y-%m'))
    # tur_monthly.reset_index(drop=True, inplace=True)
    
    # # 3.湍流强度日变化
    # tur_accum = []
    # for i in range(0, 24):
    #     hour_i_mean = ws_df[ws_df.index.hour == i]
    #     hour_i_mean = (np.std(hour_i_mean,ddof=1).values/hour_i_mean.mean()).round(3)
    #     tur_accum.append(hour_i_mean)

    # tur_accum = pd.DataFrame(tur_accum).T
    # tur_accum.columns = [str(i) + '时' for i in range(24)]
    # tur_accum.insert(loc=0, column='高度', value=[idx.split('_')[0] for idx in tur_accum.index])
    # tur_accum.reset_index(drop=True, inplace=True)
    
    # # 4.各风速区间的湍流强度
    # ws_bins = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]  # 划分的风速等级
    # ws_bins_cols = [str(ws_bins[i - 1]) + '-' + str(ws_bins[i]) for i in range(1, len(ws_bins))]  # 生成的列名
    
    # tur_hist = []
    # for i, col in enumerate(ws_df.columns):
    #     tmp = ws_df[col].to_frame()
    #     tmp['bin'] = pd.cut(tmp[col],ws_bins)
    #     tmp_res = tmp.groupby('bin').apply(lambda x: np.std(x[col],ddof=1)/x[col].mean())
    #     tur_hist.append(tmp_res)
        
    # tur_hist = pd.DataFrame(tur_hist).round(3)
    # tur_hist.columns = ws_bins_cols
    # tur_hist.insert(loc=0, column='高度', value=[col.split('_')[0] for col in ws_df.columns])
    heights = ['unknown0', '10m', '30m', '60m', 'unknown1']
    df_all = read_wind_tower(heights)
    
    for sta, sub_dict in df_all.items():
        ws_df = sub_dict['ws_10'].filter(like='m_hour_ws')
        


            
            
            