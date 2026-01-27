# -*- coding: utf-8 -*-
"""
Created on Mon Sep  1 16:20:04 2025

@author: hx
"""

import numpy as np
import pandas as pd
import probscale
import matplotlib
import matplotlib.pyplot as plt
from scipy import stats
import Utils.distribution_fitting as fitting
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_processing import monthly_data_processing
from Utils.pearson3 import pearson_type3
from matplotlib import font_manager

font = font_manager.FontProperties(fname=cfg.FILES.FONT)
matplotlib.use('agg')


class calc_return_period_days:
    '''
    重现期最大积雪深度及雪压计算
    20250829 增加冻土重现期计算
    '''


    def __init__(self, df_sequence, return_years, fitting_method, img_path, element):
        self.df_sequence = df_sequence
        self.return_years = return_years  # 重现期列表 list
        self.fitting_method = fitting_method  # 拟合方法列表 list
        self.img_path = img_path
        self.element = element
        self.name = dict()
        self.name['PRE_Time_2020']='暴雨日数'
        self.name['Snow_Days']='降雪日数'
        self.name['GSS_Days']='积雪日数'
        self.name['Hail_Days']='冰雹日数'
        self.name['FlDu_Days']='浮尘日数'
        self.name['FlSa_Days']='扬沙日数'
        self.name['SaSt_Days']='沙尘暴日数'
        self.name['Thund_Days']='雷暴日数'

    def calc_return_period_values(self, data_in, periods):
        '''
        计算参证站不同重现期的数值
        '''
        params_dict = edict()  # 参数字典
        max_values_dict = edict()  # 重现期结果列表
        ks_values = edict()  # KS检验结果dict
        # p3_base = edict()

        if 'Gumbel' in self.fitting_method:
            loc, scale = fitting.estimate_parameters_gumbel(data_in,method='MOM')  # 根据现有数据计算该分布的参数
            max_values = fitting.get_max_values_gumbel(periods, loc, scale)  # 根据参数和重现期列表计算对应的最大值
            sample_gumbel = stats.gumbel_r.rvs(loc, scale, 200)
            _, ks_result = fitting.kolmogorov_smirnov_test(sample_gumbel, data_in)  # KS检验

            params_dict['Gumbel'] = [loc, scale]
            max_values_dict['Gumbel_max_vals'] = max_values.round(3).tolist()
            ks_values['Gumbel_ks'] = ks_result

        if 'P3' in self.fitting_method:
            skew, loc, scale = fitting.estimate_parameters_pearson3(data_in, method='normal')
            max_values = fitting.get_max_values_pearson3(periods, 0, skew, loc, scale)
            sample_p3 = stats.pearson3.rvs(skew, loc, scale, 200)
            _, ks_result = fitting.kolmogorov_smirnov_test(sample_p3, data_in)

            params_dict['P3'] = [skew, loc, scale]
            max_values_dict['P3_max_vals'] = max_values.round(3).tolist()
            ks_values['P3_ks'] = ks_result

            # 2023新增P3调参
            # p3_result = pearson_type3(element_name='Snow_Depth', data=data_in, rp=self.return_years, img_path=self.img_path, mode=1, sv_ratio=0, ex_fitting=True, manual_cs_cv=None)
            # p3_base = p3_result

        return params_dict, max_values_dict, ks_values  #, p3_base

    def get_fig_ax(self):
        fig, ax = plt.subplots(figsize=(7, 5))
        return fig, ax

    def plot_result(self, fig, ax, data_in, sample_x, sample_y, y_axis_name, method_name, ks_val):
        '''
        画重现期拟合曲线图，x轴为概率坐标
        '''
        # plt.rcParams['font.sans-serif'] = 'SimHei'
        plt.rcParams['axes.unicode_minus'] = False
        new_y_axis_name = y_axis_name + ' (cm)'
    
        ax.grid(True)
        ax.set_xlabel('KS-test: ' + str(ks_val.round(5)) + '   频率P(%)', fontproperties=font)
        ax.set_ylabel(new_y_axis_name, fontproperties=font)
        ax.set_xscale('prob')
        plt.xticks(size=7)
    
        data_in = np.sort(data_in)[::-1]
        empi_prob = (np.arange(len(data_in)) + 1) / (len(data_in) + 1) * 100
    
        # 设置x轴范围
        ax.set_xlim(0.1, 99.5)
        
        # 根据数据类型和实际数据范围动态设置y轴范围
        data_min = np.min(data_in)
        data_max = np.max(data_in)
        
        if self.element == 'snow':
            # 积雪深度：考虑删除0值后的数据范围，但保持一定的显示范围
            y_min = 0  # 积雪深度从0开始显示
            y_max = max(30, data_max * 1.2)  # 至少30cm，或数据最大值的1.2倍
        elif self.element == 'frs':
            # 冻土深度：根据实际数据范围设置
            y_min = max(0, data_min * 0.9)  # 稍微低于最小值
            y_max = data_max * 1.2  # 数据最大值的1.2倍
        else:
            # 默认情况
            y_min = max(0, data_min * 0.9)
            y_max = data_max * 1.2
        
        ax.set_ylim(y_min, y_max)
    
        ax.scatter(empi_prob, data_in, marker='o', s=8, c='red', edgecolors='k', label='经验概率数据点')
        ax.plot(sample_x, sample_y, '--', lw=1, label=method_name + '分布拟合曲线')
        ax.legend(prop=font)
    
        save_path = self.img_path + '/{}_{}.png'.format(y_axis_name, method_name)
        plt.savefig(save_path, dpi=200, format='png', bbox_inches='tight')
    
        # 关闭图框
        plt.cla()
        return save_path

    def run_days(self):
        '''
        forward流程 冻土
        '''
        fig, ax = self.get_fig_ax()
    
        # Step0 结果字典创建/数据处理
        result_dict = edict()
        result_dict.return_years = self.return_years
    
        frs_data = self.df_sequence[self.element].round(3)
        frs_data = frs_data.dropna()

        frs_data_save = frs_data.to_frame().copy()
        frs_data_save.insert(loc=0, column='year', value=frs_data_save.index.year)
        frs_data_save.columns = ['年份',f'{self.name[self.element]}']
        frs_data_save.reset_index(drop=True, inplace=True)
        result_dict.data = frs_data_save.to_dict(orient='records')
            
        # Step2 删除0值（与频率转换保持一致）
        frs_data_filtered = frs_data[frs_data > 0]
        if frs_data_filtered.shape[0] < 10:
            raise Exception('删除0值后有效样本小于10个，不能进行后续重现期计算')
    
        # Step3 重现期计算（使用过滤后的数据）
        if self.fitting_method is not None:
            result_dict.main_return_result = edict()
            params_dict, max_values_dict, ks_values = self.calc_return_period_values(frs_data_filtered, self.return_years)
            result_dict.main_return_result['max_values'] = max_values_dict
            result_dict.main_return_result['distribution_params'] = params_dict

        # Step5 重现期画图（使用过滤后的数据）
        result_dict.img_save_path = edict()
        keys = list(params_dict.keys())
        x = np.linspace(0.01, 100, 1000) # 对应图片频率 (%) 从左到右，1/(x/100)转化为年
    
        if 'Gumbel' in keys:
            y = fitting.get_max_values_gumbel(1/(x/100), params_dict['Gumbel'][0], params_dict['Gumbel'][1])
            save_path = self.plot_result(fig, ax, frs_data_filtered, x, y, f'年{self.name[self.element]}', 'Gumbel', ks_values['Gumbel_ks'])
            result_dict.img_save_path['Gumbel_plot'] = save_path
    
        if 'P3' in keys:
            y = fitting.get_max_values_pearson3(1/(x/100), 0, params_dict['P3'][0], params_dict['P3'][1], params_dict['P3'][2])
            save_path = self.plot_result(fig, ax, frs_data_filtered, x, y, f'年{self.name[self.element]}', 'Pearson3', ks_values['P3_ks'])
            result_dict.img_save_path['P3_plot'] = save_path
    
        # 关闭图框
        plt.cla()
        plt.close('all')

        return result_dict
