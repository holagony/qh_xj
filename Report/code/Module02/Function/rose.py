# -*- coding: utf-8 -*-
"""
Created on Fri Aug  4 15:48:08 2023

@author: EDY
"""

import numpy as np
import pandas as pd
import os
import matplotlib.pyplot as plt
#-------设置支持中文----------------------#
import matplotlib as mpl
mpl.rcParams['font.sans-serif'] = ['SimHei']   #设置简黑字体
mpl.rcParams['axes.unicode_minus'] = False
#-------自定义坐标轴刻度格式----------------#
from matplotlib.ticker import FuncFormatter

def rose_picture(data1,title,title1,path_out):
    # data1 = pd.DataFrame(basic_wind_freq.iloc[12,1:17])
    a=np.array(data1.iloc[-1,0])
    b=np.array(data1.iloc[0:15,0]).T
    c=np.append(a,b)
    
    data = pd.DataFrame(columns='N NNE NE ENE E ESE SE SSE S SSW SW WSW W WNW NW NNW'.split())
    
    
    N = 16 # 风速分布为16个方向
    theta = np.linspace(0, 2*np.pi, N, endpoint=False) # 获取16个方向的角度值
    width = np.pi / N  # 绘制扇型的宽度，可以自行调整
    labels = list(data.columns) # 自定义坐标标签为 N ， NSN， ……
    # 开始绘图
    plt.figure(figsize=(4,4))
    ax = plt.subplot(111, projection='polar')
    ax.bar(theta,c, width=width, bottom=0.0,  tick_label=labels)
    ax.set_theta_zero_location('N')#设置正北
    ax.set_theta_direction(-1)#改变显示的角度顺序
    plt.title(title)
    save_path = os.path.join(path_out,title1 + '.png')
    plt.savefig(save_path, dpi=200, bbox_inches='tight')
    plt.clf()
    plt.close('all')
    # plt.legend(loc=4, bbox_to_anchor=(1.15, -0.07)) # 将label显示出来， 并调整位置
    # plt.show()

