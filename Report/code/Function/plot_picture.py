# -*- coding: utf-8 -*-
"""
Created on Thu Oct 31 16:38:31 2024

@author: EDY
"""

import numpy as np
import matplotlib.pyplot as plt
import os

def plot_picture(df, namex,namey,namelable,unit,namepng,num1,num2,data_dir):
    """
    绘制和保存地面温度趋势图。

    参数:
    df (DataFrame): 包含年份和月平均最高地面温度的数据。
    data_dir (str): 保存图表的目录。

    返回:
    str: 保存的图表文件路径。
    """
    # 数据筛选
    mask = ~np.isnan(df[namey])
    valid_years = df[namex][mask].astype(int)
    valid_gstperatures = df[namey][mask].astype(float)

    # 线性拟合
    slope, intercept = np.polyfit(valid_years, valid_gstperatures, 1)

    # 绘图
    plt.figure(figsize=(9, 4))
    plt.plot(df[namex], df[namey], color='black', marker='o', markersize=5, linestyle='-', label='年平均')
    plt.plot(df[namex], [df[namey].mean()] * len(df[namex]), color='black', linestyle='--', label='平均值')
    plt.plot(valid_years, slope * valid_years + intercept, color='red', linestyle='--', label='线性')

    # 最高和最低温度点
    max_temp_index = df[namey].idxmax()
    min_temp_index = df[namey].idxmin()
    max_year = df.loc[max_temp_index, namex]
    max_temp = df.loc[max_temp_index, namey]
    min_year = df.loc[min_temp_index, namex]
    min_temp = df.loc[min_temp_index, namey]
    plt.scatter(max_year, max_temp, color='red', s=50, alpha=1)
    plt.scatter(min_year, min_temp, color='red', s=50, alpha=1)
    plt.annotate(f'最高，{max_year}年，{max_temp}{unit}', (max_year, max_temp), textcoords="offset points", xytext=(0, 10), ha='center', color='red')
    plt.annotate(f'最低，{min_year}年，{min_temp}{unit}', (min_year, min_temp), textcoords="offset points", xytext=(0, -20), ha='center', color='red')

    # 标注和保存
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.grid(axis='x', linestyle='--', alpha=0.7)
    plt.xlabel('年')
    plt.ylabel(namelable)
    total_points = len(df[namex])
    step = max(1, total_points // 8)  # 确保步长至少为1
    plt.xticks(df[namex][::step])
    plt.xlim(np.min(df[namex]), np.max(df[namex]))
    if num1!=100:
        plt.ylim(df[namey].min() - num1, df[namey].max() + num2)
    plt.legend()

    # 保存图表
    max_gst_picture_hournum = os.path.join(data_dir, namepng)
    plt.savefig(max_gst_picture_hournum, bbox_inches='tight', dpi=200)
    plt.clf()
    plt.close('all')

    return max_gst_picture_hournum

def plot_picture_2(x,y,dic,namelabel,namedic1,namedic2,namepng,num1,num2,data_dir):
    

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = plt.cm.Greys(np.linspace(0.3, 0.7, len(x)))
    
    # 在ax上绘制柱状图
    rects1=ax.bar(x, y, width=0.4, color=colors)
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.grid(axis='x', linestyle='--', alpha=0.7)
    ax.set_xlabel('月')
    ax.set_ylabel(namelabel)
    ax.set_xticks(x)
    if namedic1 ==1:
        labels = ax.get_xticklabels()
        ax.set_xticklabels(labels, rotation=90)

    if num1!=100:
        ax.set_ylim(dic[namedic1]-num1, dic[namedic2]+num2)
    ax.bar_label(rects1, padding=3)  # 更加简单好用的api

    # 保存图形
    average_gst_picture_month = os.path.join(data_dir, namepng)
    plt.savefig(average_gst_picture_month, bbox_inches='tight', dpi=200)
    
    # 清除图形，关闭所有打开的窗口
    plt.clf()
    plt.close('all')
    
    return average_gst_picture_month
