# -*- coding: utf-8 -*-
"""
Created on Sun Aug 31 15:03:14 2025

@author: mjynj
"""
import numpy as np
import pandas as pd
import os
import glob


sta_id = 'XJ001'
lon = 120
lat = 25


paths = r'C:/Users/mjynj/Desktop/ws'
total_path = glob.glob(os.path.join(paths, '*.xls'))
df_all = []
for path in total_path:
    df = pd.read_excel(path, header=2)
    df = df.iloc[3:,:-4]
    df_all.append(df)
        
df_trans = pd.concat(df_all, axis=0)
df_trans['时间'] = pd.to_datetime(df_trans['时间'], format='%Y-%m-%d %H:%M')
df_trans.set_index('时间', inplace=True)

df_trans['datetime'] = df_trans.index
df_trans = pd.melt(df_trans, id_vars=['datetime'], var_name='高度层', value_name='数值')
df_trans = df_trans.set_index(['datetime', '数值'])['高度层'].str.split('层', expand=True).reset_index()
df_trans = df_trans.set_index(['datetime', 0, 1]).unstack()
df_trans.columns = df_trans.columns.droplevel(0)
df_trans = df_trans.rename_axis(columns=None).reset_index()
df_trans.columns = ['datetime', '高度层', '10分风向', '10分风速']

# 将中文数字转换为阿拉伯数字
def chinese_to_number(text):
    chinese_num_map = {'第一': 1, '第二': 2, '第三': 3, '第四': 4, '第五': 5,
                       '第六': 6, '第七': 7, '第八': 8, '第九': 9, '第十': 10,
                       '第十一': 11, '第十二': 12, '第十三': 13, '第十四': 14, '第十五': 15}
    return chinese_num_map[text]


df_trans['高度层'] = df_trans['高度层'].apply(chinese_to_number)
df_trans['station_id'] = sta_id
df_trans['lon'] = lon
df_trans['lat'] = lat
df_trans['对应高度'] = np.nan
df_trans['datetime'] = df_trans['datetime'].dt.strftime('%Y%m%d%H%M%S')
df_trans['2分风向'] = np.nan
df_trans['2分风速'] = np.nan
df_trans['最大风向'] = np.nan
df_trans['最大风速'] = np.nan
df_trans['极大风向'] = np.nan
df_trans['极大风速'] = np.nan
df_trans['瞬时风向'] = np.nan
df_trans['瞬时风速'] = np.nan

df_trans = df_trans[['station_id', 'lon', 'lat', 'datetime', '高度层', '对应高度', '10分风向', '10分风速', '2分风向', '2分风速', '最大风向', '最大风速', '极大风向', '极大风速', '瞬时风向', '瞬时风速']]

