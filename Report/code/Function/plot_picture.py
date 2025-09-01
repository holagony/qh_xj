# -*- coding: utf-8 -*-
"""
Created on Thu Oct 31 16:38:31 2024

@author: EDY
"""

import numpy as np
import matplotlib.pyplot as plt
import os
from adjustText import adjust_text


def plot_picture(df, namex, namey, namelable, unit, namepng, num1, num2, data_dir):
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

    # 求R2
    R = np.corrcoef(valid_gstperatures, slope * valid_years + intercept)
    R2 = R[0, 1]**2

    # 绘图
    plt.figure(figsize=(9, 4))
    # 只绘制有效数据，确保数据点和刻度对应
    plt.plot(valid_years, valid_gstperatures, color='black', marker='o', markersize=5, linestyle='-', markerfacecolor='black', markeredgecolor='black', markeredgewidth=0, label='年平均')
    plt.plot(valid_years, [valid_gstperatures.mean()] * len(valid_years), color='black', linestyle='--', label='平均值')
    # 绘制线性拟合线，覆盖整个有效数据范围
    x_fit = np.array([valid_years.min(), valid_years.max()])
    y_fit = slope * x_fit + intercept
    plt.plot(x_fit, y_fit, color='red', linestyle='--', label='线性')

    # 最高和最低温度点（基于有效数据）
    # max_temp_idx = np.argmax(valid_gstperatures.values)
    # min_temp_idx = np.argmin(valid_gstperatures.values)
    # max_year = valid_years.iloc[max_temp_idx]
    # max_temp = valid_gstperatures.iloc[max_temp_idx]
    # min_year = valid_years.iloc[min_temp_idx]
    # min_temp = valid_gstperatures.iloc[min_temp_idx]
    # plt.scatter(max_year, max_temp, color='red', s=25, alpha=1, zorder=5, edgecolors='none')
    # plt.scatter(min_year, min_temp, color='red', s=25, alpha=1, zorder=5, edgecolors='none')

    # 设置坐标轴刻度朝内，取消网格
    plt.tick_params(axis='both', direction='in')
    plt.xlabel('年')
    plt.ylabel(namelable)
    year_min = valid_years.min()
    year_max = valid_years.max()
    # 生成约10个刻度
    num_ticks = 10
    step = max(1, int((year_max - year_min) / (num_ticks - 1)))
    xtick_years = np.arange(year_min, year_max + 1, step)
    plt.xticks(xtick_years)
    plt.xlim(np.min(valid_years), np.max(valid_years))
    # if num1 != 100:
    #     plt.ylim(valid_gstperatures.min() - num1, valid_gstperatures.max() + num2)
    y_min, y_max = valid_gstperatures.min(), valid_gstperatures.max()
    y_range = y_max - y_min
    margin = y_range * 0.05 if y_range > 0 else 0.1
    plt.ylim(y_min - margin, y_max + margin)
    # plt.legend()

    # 创建文本标注
    texts = []
    # texts.append(plt.text(max_year, max_temp, f'最高，{max_year}年，{max_temp}{unit}', color='red', ha='center', va='bottom'))
    # texts.append(plt.text(min_year, min_temp - num2 / 4, f'最低，{min_year}年，{min_temp}{unit}', color='red', ha='center', va='top'))

    # 选择一个相对空旷的区域放置文本
    text_x = year_min + (year_max - year_min) * 0.2 
    text_y = y_min + (y_max - y_min) * 0.8  
    
    if intercept >= 0:
        equation_text = f'y={slope:.2f}x+{intercept:.2f}\nR$^2$={R2:.3f}'
    else:
        equation_text = f'y={slope:.2f}x{intercept:.2f}\nR$^2$={R2:.3f}'
    
    text_obj = plt.text(text_x, text_y, equation_text, fontsize=9)

    # 生成避障点 - 更全面的覆盖
    # 1. 数据点
    points_x = valid_years.values
    points_y = valid_gstperatures.values
    
    # 2. 生成所有连线上的密集点
    line_points_x = []
    line_points_y = []
    
    # 原始数据连线
    for i in range(len(valid_years) - 1):
        x_dense = np.linspace(valid_years.iloc[i], valid_years.iloc[i+1], 20)
        y_dense = np.interp(x_dense, 
                           [valid_years.iloc[i], valid_years.iloc[i+1]], 
                           [valid_gstperatures.iloc[i], valid_gstperatures.iloc[i+1]])
        line_points_x.extend(x_dense)
        line_points_y.extend(y_dense)
    
    # 平均值线
    mean_x = np.linspace(year_min, year_max, 50)
    mean_y = np.full_like(mean_x, valid_gstperatures.mean())
    line_points_x.extend(mean_x)
    line_points_y.extend(mean_y)
    
    # 拟合线
    fit_x = np.linspace(year_min, year_max, 50)
    fit_y = slope * fit_x + intercept
    line_points_x.extend(fit_x)
    line_points_y.extend(fit_y)
    
    # 合并所有避障点
    all_obstacle_x = np.concatenate([points_x, line_points_x])
    all_obstacle_y = np.concatenate([points_y, line_points_y])

    # 使用adjust_text进行避障
    adjust_text(
        [text_obj],
        x=all_obstacle_x,
        y=all_obstacle_y,
        expand_text=(1.5, 1.5),
        expand_points=(2.0, 2.0),
        force_text=(0.5, 0.5),
        force_points=(0.5, 0.5),
        only_move={'points': 'xy', 'text': 'xy'}
    )

    
    # 网格
    plt.grid(axis='y', linestyle='--', alpha=0.4)
    plt.grid(axis='x', linestyle='--', alpha=0.4)

    # 保存图表
    plt.legend(loc='best')
    max_gst_picture_hournum = os.path.join(data_dir, namepng)
    plt.savefig(max_gst_picture_hournum, bbox_inches='tight', dpi=200)
    plt.clf()
    plt.close('all')

    return max_gst_picture_hournum


def plot_picture_2(x, y, dic, namelabel, namedic1, namedic2, namepng, num1, num2, data_dir):

    fig, ax = plt.subplots(figsize=(10, 6))
    # 确保y是数值类型数组，处理非数值数据
    y = np.asarray(y, dtype=float)
    # 根据数值大小进行颜色渐变
    y_min, y_max = np.nanmin(y), np.nanmax(y)
    if y_max == y_min:  # 避免除零错误
        y_normalized = np.zeros_like(y)
    else:
        y_normalized = (y - y_min) / (y_max - y_min)  # 将数值标准化到0-1之间
    colors = plt.cm.Blues(0.4 + y_normalized * 0.4)  # 数值越大颜色越深

    # 在ax上绘制柱状图
    rects1 = ax.bar(x, y, width=0.4, color=colors, edgecolor='white', linewidth=0.8)
    ax.grid(axis='y', linestyle='--', alpha=0.3, color='gray')
    ax.grid(axis='x', linestyle='--', alpha=0.3, color='gray')
    ax.set_xlabel('月')
    ax.set_ylabel(namelabel)
    ax.set_xticks(x)
    if namedic1 == 1:
        labels = ax.get_xticklabels()
        ax.set_xticklabels(labels, rotation=90)

    # if num1 != 100:
    #     ax.set_ylim(dic[namedic1] - num1, dic[namedic2] + num2)

    y_min, y_max = np.min(dic[namedic1]), np.min(dic[namedic2])
    y_range = y_max - y_min
    margin = y_range * 0.05 if y_range > 0 else 0.1
    ax.set_ylim(y_min - margin, y_max + margin)

    ax.bar_label(rects1, padding=3)  # 更加简单好用的api

    # 保存图形
    average_gst_picture_month = os.path.join(data_dir, namepng)
    plt.savefig(average_gst_picture_month, bbox_inches='tight', dpi=200)

    # 清除图形，关闭所有打开的窗口
    plt.clf()
    plt.close('all')

    return average_gst_picture_month
