import json
import pickle
import pprint
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import probscale
import scipy.stats as stats
from scipy.optimize import curve_fit
from scipy.stats import pearson3, gumbel_r
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.config import cfg

from matplotlib import font_manager

font = font_manager.FontProperties(fname=cfg.FILES.FONT)
matplotlib.use('agg')


class rain_fitting():
    '''
    P3/Gumbel的矩法实现，附带P3调参
    计算单个历时的重现期
    '''

    def __init__(self, element_name, data, rp, img_path, mode, sv_ratio=0, ex_fitting=True, manual_cs=None, manual_cv=None):
        '''
        data: 降水历时对应的年最大值序列
        img_path: 画图保存路径
        mode: 画图和计算重现期模式，对应数值0/1/2/3/4/5
            0--对应耿贝尔法计算，Gumbel矩法结果画图，Gumbel矩法参数计算重现期
            1--对应P3矩法计算(不调参)，P3矩法结果画图，P3矩法参数计算重现期
            2--对应P3自动调参计算(最小二乘)，P3自动调参结果画图，P3自动调参参数计算重现期
            3--对应P3手动调参计算，P3手动调参结果画图，P3手动调参参数计算重现期
            4--对应P3自动调参计算(最小二乘)，矩法加自动调参结果画一张图，P3自动调参参数计算重现期
            5--对应P3手动调参计算，P3矩法加手动调参结果画一张图，P3手动调参参数计算重现期
            
        sv_ratio: 默认值0，Cs和Cv的比值系数，
                  值等于0的时候，Cs/Cv不固定比例，Cs正常参与适线(自动/手动)运算；
                  值不等于0的时候，Cs不参与适线运算，Cs=sv_ratio*Cv (mode=2的时候用到)
                  
        ex_fitting: 默认值True，P3最小二乘调参时是否调整Ex，一般默认选择调整 (mode=2的时候用到)
        manual_cs: P3手动调参时输入的Cs (mode=3的时候用到)
        manual_cv: P3手动调参是输入的Cv (mode=3的时候用到)
        '''
        self.rp = rp
        self.element_name = element_name
        self.data = np.sort(data)[::-1]  # 降序排序输入数组
        self.n = len(data)
        self.empi_prob = (np.arange(self.n) + 1) / (self.n + 1) * 100  # 经验概率
        self.expectation = np.mean(self.data)  # 期望

        self.img_path = img_path
        self.mode = mode
        self.sv_ratio = sv_ratio
        self.ex_fitting = ex_fitting
        self.manual_cs = manual_cs
        self.manual_cv = manual_cv

        mode_dict = {'B': 'P3矩法结果', 'E': 'P3自动调参', 'F': 'P3人工调参'}
        self.mode_dict = mode_dict

    def p3_params_mom(self):
        '''
        矩法自动估计P3分布参数 (调参前运行)
        '''
        self.modulus_ratio = self.data / self.expectation  # 模比系数
        self.coeff_of_var = np.sqrt(np.sum((self.modulus_ratio - 1)**2) / (self.n - 1))  # 变差系数
        self.coeff_of_skew = stats.skew(self.data, bias=False)  # 偏态系数

        # 计算误差
        y_pred = (pearson3.ppf(1 - self.empi_prob / 100, self.coeff_of_skew) * self.coeff_of_var + 1) * self.expectation
        rmse = np.sqrt(mean_squared_error(self.data, y_pred))
        mae = mean_absolute_error(self.data, y_pred)
        error = (mae / np.mean(self.data)) * 100  # 相对误差

        # 保存结果
        p3_dict = {
            'ex': round(self.expectation, 3),
            'cs': round(np.abs(self.coeff_of_skew), 3),
            'cv': round(self.coeff_of_var, 3),
            'cs/cv': round(np.abs(self.coeff_of_skew) / self.coeff_of_var, 3),
            'rmse': round(rmse, 5),
            'mae': round(mae, 5),
            'rel_error': round(error, 2)
        }

        self.cs_val = str(int(p3_dict['cs'] * 1000)) + 'e-3'
        self.cv_val = str(int(p3_dict['cv'] * 1000)) + 'e-3'

        return p3_dict

    def p3_params_automatic_fine_tune(self):
        '''
        P3最小二乘法自动调参，首先要有原始的Ex/Cs/Cv
        '''
        if self.sv_ratio == 0:
            if self.ex_fitting:

                def p3(prob, ex, cv, cs):
                    return (pearson3.ppf(1 - prob / 100, cs) * cv + 1) * ex

                [self.fit_EX, self.fit_CV, self.fit_CS], pcov = curve_fit(p3, self.empi_prob, self.data, [self.expectation, self.coeff_of_var, self.coeff_of_skew])

            else:

                def p3(prob, cv, cs):
                    return (pearson3.ppf(1 - prob / 100, cs) * cv + 1) * self.expectation

                [self.fit_CV, self.fit_CS], pcov = curve_fit(p3, self.empi_prob, self.data, [self.coeff_of_var, self.coeff_of_skew])
                self.fit_EX = self.expectation

        else:
            if self.ex_fitting:

                def p3(prob, ex, cv):
                    return (pearson3.ppf(1 - prob / 100, cv * self.sv_ratio) * cv + 1) * ex

                [self.fit_EX, self.fit_CV], pcov = curve_fit(p3, self.empi_prob, self.data, [self.expectation, self.coeff_of_var])

            else:

                def p3(prob, cv):
                    return (pearson3.ppf(1 - prob / 100, cv * self.sv_ratio) * cv + 1) * self.expectation

                [self.fit_CV], pcov = curve_fit(p3, self.empi_prob, self.data, [self.coeff_of_var])
                self.fit_EX = self.expectation

            self.fit_CS = self.fit_CV * self.sv_ratio

        # 自动适线后的误差
        y_pred = (pearson3.ppf(1 - self.empi_prob / 100, self.fit_CS) * self.fit_CV + 1) * self.fit_EX
        rmse = np.sqrt(mean_squared_error(self.data, y_pred))
        mae = mean_absolute_error(self.data, y_pred)
        error = (mae / np.mean(self.data)) * 100  # 相对误差

        # 保存结果
        p3_dict = {'ex': round(self.fit_EX, 3), 'cs': round(self.fit_CS, 3), 'cv': round(self.fit_CV, 3), 'cs/cv': round(self.fit_CS / self.fit_CV, 3), 'rmse': round(rmse, 5), 'mae': round(mae, 5), 'rel_error': round(error, 2)}

        self.cs_val = str(int(p3_dict['cs'] * 1000)) + 'e-3'
        self.cv_val = str(int(p3_dict['cv'] * 1000)) + 'e-3'

        return p3_dict

    def p3_params_manual_fine_tune(self):
        '''
        P3手动调参
        '''
        y_pred = (pearson3.ppf(1 - self.empi_prob / 100, self.manual_cs) * self.manual_cv + 1) * self.expectation
        rmse = np.sqrt(mean_squared_error(self.data, y_pred))
        mae = mean_absolute_error(self.data, y_pred)
        error = (mae / np.mean(self.data)) * 100  # 相对误差

        # 保存结果
        p3_dict = {'ex': round(self.expectation, 3), 'cs': round(self.manual_cs, 3), 'cv': round(self.manual_cv, 3), 'cs/cv': round(self.manual_cs / self.manual_cv, 3), 'rmse': round(rmse, 5), 'mae': round(mae, 5), 'rel_error': round(error, 2)}

        self.cs_val = str(int(p3_dict['cs'] * 1000)) + 'e-3'
        self.cv_val = str(int(p3_dict['cv'] * 1000)) + 'e-3'

        return p3_dict

    def get_fig_ax(self):
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.set_xlabel('频率 (%)', fontproperties=font)
        # ax.set_ylabel('雨强 (mm/min)', fontproperties=font)
        ax.set_xscale('prob')
        ax.set_xlim(0.01, 99.5)
        ax.grid(True)
        return fig, ax

    def plot_fig(self, fig, ax):
        '''
        绘制图形
        '''
        # plt.rcParams['font.sans-serif'] = 'SimHei'
        plt.rcParams['axes.unicode_minus'] = False
        plt.xticks(size=5)

        # plot
        ax.scatter(self.empi_prob, self.data, marker='o', s=8, c='red', edgecolors='k', label=self.element_name + '-年最大值序列经验概率点')  # 绘制经验概率
        sample_x = np.linspace(0.01, 99.5, 1000)

        if self.mode == 1:
            name = self.mode_dict['B']
            theo_y = (pearson3.ppf(1 - sample_x / 100, self.coeff_of_skew) * self.coeff_of_var + 1) * self.expectation
            ax.plot(sample_x, theo_y, '--', lw=1, label='P3矩法估计参数概率曲线')

        elif self.mode == 4:
            name = self.mode_dict['E']
            theo_y = (pearson3.ppf(1 - sample_x / 100, self.coeff_of_skew) * self.coeff_of_var + 1) * self.expectation
            ax.plot(sample_x, theo_y, '--', lw=1, label='P3矩法估计参数概率曲线')

            theoY = (pearson3.ppf(1 - sample_x / 100, self.fit_CS) * self.fit_CV + 1) * self.fit_EX
            ax.plot(sample_x, theoY, lw=1, label='P3最小二乘适线后概率曲线')

        elif self.mode == 5:
            name = self.mode_dict['F']
            theo_y = (pearson3.ppf(1 - sample_x / 100, self.coeff_of_skew) * self.coeff_of_var + 1) * self.expectation
            ax.plot(sample_x, theo_y, '--', lw=1, label='P3矩法估计参数概率曲线')

            theoY = (pearson3.ppf(1 - sample_x / 100, self.manual_cs) * self.manual_cv + 1) * self.expectation
            ax.plot(sample_x, theoY, lw=1, label='P3人工适线后概率曲线')

        ax.legend(prop=font)
        save_path = self.img_path + '/{}_{}_cs{}_cv{}.png'.format(name, self.element_name, self.cs_val, self.cv_val)
        plt.savefig(save_path, dpi=200, format='png', bbox_inches='tight')

        # 关闭图框
        # plt.cla()
        # plt.close('all')
        plt.cla()

        return save_path

    def prob_to_value(self):
        '''
        由设计频率转换设计值 
        重现期转极值
        '''
        years = np.array(self.rp)
        prob = 1 / years

        if self.mode == 1:
            return_vals = (pearson3.ppf(1 - prob, self.coeff_of_skew) * self.coeff_of_var + 1) * self.expectation

        elif self.mode == 4:
            return_vals = (pearson3.ppf(1 - prob, self.fit_CS) * self.fit_CV + 1) * self.fit_EX

        elif self.mode == 5:
            return_vals = (pearson3.ppf(1 - prob, self.manual_cs) * self.manual_cv + 1) * self.expectation

        return_vals = return_vals.round(3)

        return return_vals

    def run(self):
        '''
        主流程
        '''
        if self.mode == 1:
            distr_dict = self.p3_params_mom()  # P3矩法拟合参数和误差
            save_path = None

        elif self.mode == 4:
            distr_dict = self.p3_params_mom()  # 先跑一遍这个生成P3矩法的参数
            distr_dict = self.p3_params_automatic_fine_tune()  # P3最小二乘拟合参数和误差
            fig, ax = self.get_fig_ax()
            save_path = self.plot_fig(fig, ax)
            plt.close('all')

        elif self.mode == 5:
            distr_dict = self.p3_params_mom()  # 先跑一遍这个生成P3矩法的参数
            distr_dict = self.p3_params_manual_fine_tune()
            fig, ax = self.get_fig_ax()
            save_path = self.plot_fig(fig, ax)
            plt.close('all')

        return_vals = self.prob_to_value()

        return distr_dict, save_path, return_vals


def pearson_type3(element_name, data, rp, img_path, mode, sv_ratio=3.5, ex_fitting=True, manual_cs_cv=None):
    '''
    img_path: 画图保存路径
    mode: 画图和计算重现期模式，对应数值0/1/2/3/4/5
        1--对应P3矩法计算(不调参)，P3矩法结果画图，P3矩法参数计算重现期
        4--对应P3自动调参计算(最小二乘)，矩法加自动调参结果画一张图，P3自动调参参数计算重现期
        5--对应P3手动调参计算，P3矩法加手动调参结果画一张图，P3手动调参参数计算重现期
        
    sv_ratio: 默认值0，Cs和Cv的比值系数，(mode=2/4的时候用到)
              值等于0的时候，Cs/Cv不固定比例，Cs正常参与适线(自动/手动)运算；
              值不等于0的时候，Cs不参与适线运算，Cs=sv_ratio*Cv
    ex_fitting: 默认值True，P3最小二乘调参时是否调整Ex，一般默认选择调整 (mode=4的时候用到)
    manual_cs_cv: 对于每个历时，手动输入的Cs和Cv值，字典形式 (mode=5的时候用到)
    '''
    # 数据读取
    data = data.values

    # 计算流程，输出结果字典
    result = edict()

    if isinstance(manual_cs_cv, list):
        manual_cs = manual_cs_cv[0]
        manual_cv = manual_cs_cv[1]
    else:
        manual_cs = None
        manual_cv = None

    # 计算
    fitting = rain_fitting(element_name, data, rp, img_path, mode, sv_ratio, ex_fitting, manual_cs, manual_cv)
    distr_dict, save_path, return_vals = fitting.run()

    result['distribution_info'] = distr_dict
    result['img_save_path'] = save_path
    result['max_values'] = return_vals.tolist()

    return result
