import json
import pickle
import numpy as np
import pandas as pd
import probscale
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import font_manager
import scipy.stats as stats
from scipy.optimize import curve_fit
from scipy.stats import pearson3, gumbel_r, expon
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict

matplotlib.use('agg')
font = font_manager.FontProperties(fname=cfg.FILES.FONT)


class rain_fitting:
    '''
    P3/Gumbel的矩法实现，附带P3调参
    计算单个历时的重现期
    '''
    def __init__(self, during_time, data, img_path, mode, sv_ratio=0, ex_fitting=True, manual_cs=None, manual_cv=None):
        '''
        during_time: 降水历时5min~1440min
        data:降水历时对应的年最大值序列
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
        self.during_time = during_time
        self.data = np.sort(data)[::-1] # 降序排序输入数组
        self.n = len(data)
        self.empi_prob = (np.arange(self.n)+1)/(self.n+1)*100 # 经验概率
        self.expectation = np.mean(self.data) # 期望
        
        self.img_path = img_path
        self.mode = mode
        self.sv_ratio = sv_ratio
        self.ex_fitting = ex_fitting
        self.manual_cs = manual_cs
        self.manual_cv = manual_cv
        
        mode_dict = {'A':'Gumbel矩法结果',
                     'B':'P3矩法结果',
                     'C':'P3自动调参结果',
                     'D':'P3手动调参结果',
                     'E':'P3矩法加自动调参结果',
                     'F':'P3矩法加人工调参结果',
                     'G':'指数分布结果'}
        self.mode_dict = mode_dict
    
    
    def expon_params(self):
        '''
        指数分布
        '''
        self.expon_loc, self.expon_scale = expon.fit(self.data)
        
        # 计算误差
        y_pred = expon.ppf(1-self.empi_prob/100, loc=self.expon_loc, scale=self.expon_scale)
        rmse = np.sqrt(mean_squared_error(self.data, y_pred))
        mae = mean_absolute_error(self.data, y_pred)        
        error = (mae/np.mean(self.data))*100 # 相对误差
        
        # 保存结果
        expon_dict = {'expon_loc': round(self.expon_loc,3), 
                      'expon_scale': round(self.expon_scale,3), 
                      'rmse': round(rmse,5), 
                      'mae': round(mae,5), 
                      'rel_error': round(error,2)}
        
        return expon_dict
    
        
    def gumbel_params_mom(self):
        '''
        耿贝尔分布矩法估计参数
        '''
        self.gumbel_scale = np.sqrt(6)/np.pi * np.std(self.data)
        self.gumbel_loc = np.mean(self.data) - np.euler_gamma*self.gumbel_scale
        
        # wiki
        a = self.gumbel_scale # 对应公式里面的beta 
        b = self.gumbel_loc # 对应公式里面的mu

        
        # 计算误差
        y_pred = gumbel_r.ppf(1-self.empi_prob/100, loc=self.gumbel_loc, scale=self.gumbel_scale)
        rmse = np.sqrt(mean_squared_error(self.data, y_pred))
        mae = mean_absolute_error(self.data, y_pred)        
        error = (mae/np.mean(self.data))*100 # 相对误差
        
        # 保存结果
        gumbel_dict = {'a': round(a,3), 
                       'b': round(b,3), 
                       'loc': round(self.gumbel_loc,3),
                       'scale': round(self.gumbel_scale,3),
                       'rmse': round(rmse,5), 
                       'mae': round(mae,5), 
                       'rel_error': round(error,2)}
        
        return gumbel_dict
        
        
    def p3_params_mom(self):
        '''
        矩法自动估计P3分布参数 (调参前运行)
        '''
        self.modulus_ratio = self.data/self.expectation # 模比系数
        self.coeff_of_var = np.sqrt(np.sum((self.modulus_ratio-1)**2)/(self.n-1)) # 变差系数
        self.coeff_of_skew = stats.skew(self.data, bias=False) # 偏态系数
        
        # 计算误差
        y_pred = (pearson3.ppf(1-self.empi_prob/100, self.coeff_of_skew)*self.coeff_of_var+1)*self.expectation
        rmse = np.sqrt(mean_squared_error(self.data, y_pred))
        mae = mean_absolute_error(self.data, y_pred)        
        error = (mae/np.mean(self.data))*100 # 相对误差
        
        # 保存结果
        p3_dict = {'ex': round(self.expectation,3), 
                   'cs': round(np.abs(self.coeff_of_skew),3), 
                   'cv': round(self.coeff_of_var,3), 
                   'cs/cv': round(np.abs(self.coeff_of_skew)/self.coeff_of_var,3),
                   'rmse': round(rmse,5),
                   'mae': round(mae,5), 
                   'rel_error': round(error,2)}
        
        return p3_dict
    
    
    def p3_params_automatic_fine_tune(self):
        '''
        P3最小二乘法自动调参，首先要有原始的Ex/Cs/Cv
        '''
        if self.sv_ratio == 0:
            if self.ex_fitting:
                def p3(prob, ex, cv, cs): 
                    return (pearson3.ppf(1-prob/100,cs)*cv+1)*ex

                [self.fit_EX, self.fit_CV, self.fit_CS], pcov = curve_fit(p3, self.empi_prob, self.data, [self.expectation, self.coeff_of_var, self.coeff_of_skew])

            else:
                def p3(prob, cv, cs): 
                    return (pearson3.ppf(1-prob/100,cs)*cv+1)*self.expectation

                [self.fit_CV, self.fit_CS], pcov = curve_fit(p3, self.empi_prob, self.data, [self.coeff_of_var, self.coeff_of_skew])
                self.fit_EX = self.expectation

        else:
            if self.ex_fitting:
                def p3(prob, ex, cv): 
                    return (pearson3.ppf(1-prob/100,cv*self.sv_ratio)*cv+1)*ex

                [self.fit_EX, self.fit_CV], pcov = curve_fit(p3, self.empi_prob, self.data, [self.expectation, self.coeff_of_var])

            else:
                def p3(prob, cv): 
                    return (pearson3.ppf(1-prob/100,cv*self.sv_ratio)*cv+1)*self.expectation

                [self.fit_CV], pcov = curve_fit(p3, self.empi_prob, self.data, [self.coeff_of_var])
                self.fit_EX = self.expectation

            self.fit_CS = self.fit_CV * self.sv_ratio

        # 自动适线后的误差
        y_pred = (pearson3.ppf(1-self.empi_prob/100, self.fit_CS)*self.fit_CV+1)*self.fit_EX
        rmse = np.sqrt(mean_squared_error(self.data, y_pred))
        mae = mean_absolute_error(self.data, y_pred)        
        error = (mae/np.mean(self.data))*100 # 相对误差
        
        # 保存结果
        p3_dict = {'ex': round(self.fit_EX,3), 
                   'cs': round(self.fit_CS,3), 
                   'cv': round(self.fit_CV,3), 
                   'cs/cv': round(self.fit_CS/self.fit_CV,3),
                   'rmse': round(rmse,5),
                   'mae': round(mae,5), 
                   'rel_error': round(error,2)}
        
        return p3_dict
    
    
    def p3_params_manual_fine_tune(self):
        '''
        P3手动调参，分别输入Cs/Cv，一般在暴雨公式汇中，Cs/Cv=3.5
        '''
        y_pred = (pearson3.ppf(1-self.empi_prob/100, self.manual_cs)*self.manual_cv+1)*self.expectation
        rmse = np.sqrt(mean_squared_error(self.data, y_pred))
        mae = mean_absolute_error(self.data, y_pred)        
        error = (mae/np.mean(self.data))*100 # 相对误差
        
        # 保存结果
        p3_dict = {'ex': round(self.expectation,3), 
                   'cs': round(self.manual_cs,3), 
                   'cv': round(self.manual_cv,3), 
                   'cs/cv': round(self.manual_cs/self.manual_cv,3),
                   'rmse': round(rmse,5),
                   'mae': round(mae,5), 
                   'rel_error': round(error,2)}
        
        return p3_dict

    
    def get_fig_ax(self):
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.set_xlabel('频率 (%)', fontproperties=font)        
        ax.set_ylabel('雨强 (mm/min)', fontproperties=font)
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
        plt.yticks(size=7)
        
        # plot
        ax.scatter(self.empi_prob, self.data, marker='o', s=8, c='red', edgecolors='k', label=self.during_time+'历时-样本序列经验概率点') # 绘制经验概率
        sample_x = np.linspace(0.01, 99.5, 1000)
        
        if self.mode == 0:
            name = self.mode_dict['A']
            # theo_y = self.gumbel_loc-np.log(-np.log(1-sample_x/100))*self.gumbel_scale
            theo_y = gumbel_r.ppf(1-sample_x/100, loc=self.gumbel_loc, scale=self.gumbel_scale)
            ax.plot(sample_x, theo_y, '--', lw=1, label='Gumbel矩法概率曲线')
            
        elif self.mode == 1:
            name = self.mode_dict['B']
            theo_y = (pearson3.ppf(1-sample_x/100, self.coeff_of_skew)*self.coeff_of_var+1)*self.expectation
            ax.plot(sample_x, theo_y, '--', lw=1, label='P3矩法概率曲线')
        
        elif self.mode == 2:
            name = self.mode_dict['C']
            theo_y = (pearson3.ppf(1-sample_x/100, self.fit_CS)*self.fit_CV+1)*self.fit_EX
        
            if self.sv_ratio == 3.5:
                lab = 'P3适线后概率曲线(Cs/Cv=3.5)'
            else:
                lab = 'P3适线后概率曲线'
            
            ax.plot(sample_x, theo_y, '--', lw=1, label=lab)
                
        elif self.mode == 3:
            name = self.mode_dict['D']
            theo_y = (pearson3.ppf(1-sample_x/100, self.manual_cs)*self.manual_cv+1)*self.expectation
            ax.plot(sample_x, theo_y, '--', lw=1, label='P3人工适线后概率曲线')
            
        elif self.mode == 4:
            name = self.mode_dict['E']
            theo_y = (pearson3.ppf(1-sample_x/100, self.coeff_of_skew)*self.coeff_of_var+1)*self.expectation
            ax.plot(sample_x, theo_y, '--', lw=1, label='P3矩法概率曲线')
            
            if self.sv_ratio == 3.5:
                lab = 'P3适线后概率曲线(Cs/Cv=3.5)'
            else:
                lab = 'P3适线后概率曲线'
            
            theoY = (pearson3.ppf(1-sample_x/100, self.fit_CS)*self.fit_CV+1)*self.fit_EX
            ax.plot(sample_x, theoY, lw=1, label=lab)

        elif self.mode == 5:
            name = self.mode_dict['F']
            theo_y = (pearson3.ppf(1-sample_x/100, self.coeff_of_skew)*self.coeff_of_var+1)*self.expectation
            ax.plot(sample_x, theo_y, '--', lw=1, label='P3矩法概率曲线')
            
            theoY = (pearson3.ppf(1-sample_x/100, self.manual_cs)*self.manual_cv+1)*self.expectation
            ax.plot(sample_x, theoY, lw=1, label='P3人工适线后概率曲线')
        
        elif self.mode == 6:
            name = self.mode_dict['G']
            # theo_y = self.gumbel_loc-np.log(-np.log(1-sample_x/100))*self.gumbel_scale
            theo_y = expon.ppf(1-sample_x/100, loc=self.expon_loc, scale=self.expon_scale)
            ax.plot(sample_x, theo_y, '--', lw=1, label='指数分布概率曲线')
        
        ax.legend(prop=font)
        save_path = self.img_path+'/{}_{}.png'.format(name, self.during_time)
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
        years = np.array([2,3,5,10,20,30,50,100])
        prob = 1/years
        
        if self.mode == 0:
            return_vals = gumbel_r.ppf(1-prob, loc=self.gumbel_loc, scale=self.gumbel_scale)
            
        elif self.mode == 1:
            return_vals = (pearson3.ppf(1-prob, self.coeff_of_skew)*self.coeff_of_var+1)*self.expectation
        
        elif self.mode == 2:
            return_vals = (pearson3.ppf(1-prob, self.fit_CS)*self.fit_CV+1)*self.fit_EX
            
        elif self.mode == 3:
            return_vals = (pearson3.ppf(1-prob, self.manual_cs)*self.manual_cv+1)*self.expectation
            
        elif self.mode == 4:
            return_vals = (pearson3.ppf(1-prob, self.fit_CS)*self.fit_CV+1)*self.fit_EX
            
        elif self.mode == 5:
            return_vals = (pearson3.ppf(1-prob, self.manual_cs)*self.manual_cv+1)*self.expectation
        
        elif self.mode == 6: # 指数分布
            return_vals = expon.ppf(1-prob, loc=self.expon_loc, scale=self.expon_scale)

        return_vals = return_vals.round(5)
        
        return return_vals
    
    
    def run(self):
        '''
        主流程
        '''
        if self.mode == 0:
            distr_dict = self.gumbel_params_mom() # Gumbel拟合参数和误差
        
        elif self.mode == 1:
            distr_dict = self.p3_params_mom() # P3矩法拟合参数和误差

        elif self.mode == 2:
            distr_dict = self.p3_params_mom() # 先跑一遍这个生成P3矩法的参数
            distr_dict = self.p3_params_automatic_fine_tune() # P3最小二乘拟合参数和误差
            
        elif self.mode == 3:
            distr_dict = self.p3_params_manual_fine_tune() # P3人工调参的参数和误差
            
        elif self.mode == 4:
            distr_dict = self.p3_params_mom() # 先跑一遍这个生成P3矩法的参数
            distr_dict = self.p3_params_automatic_fine_tune() # P3最小二乘拟合参数和误差
            
        elif self.mode == 5:
            distr_dict = self.p3_params_mom() # 先跑一遍这个生成P3矩法的参数
            distr_dict = self.p3_params_manual_fine_tune()
        
        elif self.mode == 6: # 指数分布
            distr_dict = self.expon_params()
        
        fig, ax = self.get_fig_ax()
        save_path = self.plot_fig(fig, ax)
        plt.close('all')
        return_vals = self.prob_to_value()
        
        return distr_dict, save_path, return_vals


def plot_all_in_one(rain_intensity, result_dict, img_path, mode):
    '''
    所有历时数据画在一张图上
    rain_intensity 降水强度历时变化表
    result_dict 输出字典
    mode 模式，几个函数都统一
    img_path 图像保存路径
    '''
    # 预设画图参数
    # plt.rcParams['font.sans-serif'] = 'SimHei'
    plt.rcParams['axes.unicode_minus'] = False

    fig, ax = plt.subplots(figsize=(18, 10))
    # font = {'size': 15}
    ax.set_xlabel('频率 (%)', fontproperties=font)        
    ax.set_ylabel('雨强 (mm/min)', fontproperties=font)
    ax.set_xscale('prob')
    ax.set_xlim(0.01, 99.5)
    ax.set_ylim(0, 6)
    ax.grid(True)
    plt.xticks(size=5)
    
    # 改一下刻度字号
    for size in ax.get_xticklabels():
        size.set_fontsize('10')
    
    for size in ax.get_yticklabels():
        size.set_fontsize('10')
        
    n = rain_intensity.shape[0]
    empi_prob = (np.arange(n)+1)/(n+1)*100
    sample_x = np.linspace(0.01, 99.5, 1000)
    
    # 循环读取数据画图
    during_times = list(result_dict.keys())[1:] # 0-180 [1:12]
    for during_time in during_times:
        distr_dict = result_dict[during_time]['distribution_info']
        
        data = rain_intensity.loc[:,during_time].values
        data_sort = np.sort(data)[::-1]
        ax.scatter(empi_prob, data_sort, marker='o', s=1)

        if mode == 0:
            theo_y = gumbel_r.ppf(1-sample_x/100, loc=distr_dict['loc'], scale=distr_dict['scale'])
            ax.plot(sample_x, theo_y, '-', lw=0.8, label=during_time)
        
        elif mode == 6:
            theo_y = expon.ppf(1-sample_x/100, loc=distr_dict['expon_loc'], scale=distr_dict['expon_scale'])
            ax.plot(sample_x, theo_y, '-', lw=0.8, label=during_time)
            
        else:
            theo_y = (pearson3.ppf(1-sample_x/100, distr_dict['cs'])*distr_dict['cv']+1)*distr_dict['ex']
            ax.plot(sample_x, theo_y, '-', lw=0.8, label=during_time)
    
    ax.legend(prop=font)    
    save_path = img_path+'/mode{}_all_line.png'.format(str(mode))
    plt.savefig(save_path, dpi=200, format='png', bbox_inches='tight')

    # 关闭图框
    plt.cla()
    plt.close('all')
    
    return save_path
 

def step3_run(data_flag, img_path, mode, sv_ratio=3.5, ex_fitting=True, manual_cs_cv=None, step2_csv=None):
    '''
    对应接口3-1流程，默认参数计算，在这个情况下，mode应该选0/1
    对应接口3-2流程，自动/手动调参计算，在这个情况下，mode应该选2/3/4/5，并根据情况传sv_ratio/ex_fitting/manual_cs/manual_cv参数
        data_flag: 0短历时 1长历时
        img_path: 画图保存路径
    
    mode: 画图和计算重现期模式，对应数值0/1/2/3/4/5
        0--对应耿贝尔法计算，Gumbel矩法结果画图，Gumbel矩法参数计算重现期
        1--对应P3矩法计算(不调参)，P3矩法结果画图，P3矩法参数计算重现期
        2--对应P3自动调参计算(最小二乘)，P3自动调参结果画图，P3自动调参参数计算重现期
        3--对应P3手动调参计算，P3手动调参结果画图，P3手动调参参数计算重现期
        4--对应P3自动调参计算(最小二乘)，矩法加自动调参结果画一张图，P3自动调参参数计算重现期
        5--对应P3手动调参计算，P3矩法加手动调参结果画一张图，P3手动调参参数计算重现期
        6--指数分布
        
    sv_ratio: 默认值0，Cs和Cv的比值系数，(mode=2/4的时候用到)
              值等于0的时候，Cs/Cv不固定比例，Cs正常参与适线(自动/手动)运算；
              值不等于0的时候，Cs不参与适线运算，Cs=sv_ratio*Cv
              
    ex_fitting: 默认值True，P3最小二乘调参时是否调整Ex，一般默认选择调整 (mode=2/4的时候用到)
    manual_cs_cv: 对于每个历时，手动输入的Cs和Cv值，字典形式 (mode=3/5的时候用到)
    step2_csv: 步骤2输出的每年不同历时的最大一个的序列csv路径
    '''
    result = edict()
    
    # 读取数据
    duration_data = pd.read_csv(step2_csv)
    pre_data=duration_data.copy()
    data_year = duration_data['year'].values
    duration_data.drop(['Unnamed: 0'], axis=1, inplace=True)
    duration_data.drop(['year'], axis=1, inplace=True)

    if data_flag == 0: # 短历时
        duration = np.array([5,10,15,20,30,45,60,90,120,150,180])
        pre = duration_data.iloc[:,0:11].values
        pre_data=pre_data.iloc[:,0:13]
    else:
        duration = np.array([5,10,15,20,30,45,60,90,120,150,180,240,360,720,1440])
        pre = duration_data.values
    
    rain_intensity = (pre/duration).round(3)
    rain_intensity = pd.DataFrame(rain_intensity,columns=[str(dur)+'min' for dur in duration])

    # 添加雨强表格
    # rain_intensity_table = rain_intensity.copy()
    # rain_intensity_table.insert(loc=0, column='year', value=data_year)
    # if rain_intensity_table.iloc[0,0] == rain_intensity_table.iloc[1,0]:
    #     rain_intensity_table['year'] = np.arange(rain_intensity_table.shape[0])
    # result['rain_intensity'] = rain_intensity_table.to_dict(orient='records')

    # 计算流程，输出结果字典
    for i,during_time in enumerate(rain_intensity.columns):
        result[during_time] = edict()
        data = rain_intensity.loc[:,during_time].values
        
        if isinstance(manual_cs_cv, dict):
            manual_cs = manual_cs_cv[during_time][0]
            manual_cv = manual_cs_cv[during_time][1]
        else:
            manual_cs = None
            manual_cv = None

        fitting = rain_fitting(during_time, data, img_path, mode, sv_ratio, ex_fitting, manual_cs, manual_cv)
        distr_dict, save_path, return_vals = fitting.run()
        # print(distr_dict)
        # print()
        
        result[during_time]['distribution_info'] = distr_dict
        result[during_time]['img_save_path'] = save_path
        # result[during_time]['max_values'] = return_vals.tolist()
        
        # 重现期总表，用于暴雨公式计算 
        # 表格每一行是一个重现期，每一列是一个历时
        if i == 0:
            table = return_vals.reshape(-1,1)
        else:
            table = np.concatenate((table,return_vals.reshape(-1,1)),axis=1)
    
    # all in one画图并保存图片路径
    all_in_one = plot_all_in_one(rain_intensity, result, img_path, mode)
    result['all_in_one'] = all_in_one

    # p-i-t纯数字，用于拟合暴雨强度公式
    result['return_table'] = table.tolist()

    # p-i-t表格，用于展示
    table_df = pd.DataFrame(table.round(3), columns=[str(dur)+'min' for dur in duration])
    table_df.insert(loc=0, column='重现期(a)', value=[2,3,5,10,20,30,50,100])
    result['pit_table'] = table_df.to_dict(orient='records')

    return result,pre_data


if __name__ == '__main__':
    data_flag = 0 # 短历时--0 长历时--1
    img_path = r'C:/Users/MJY/Desktop/result'
    mode = 6 # 频率曲线方法 可用：gumbel--0 p3--2 指数--6
    step2_csv = r'C:/Users/MJY/Desktop/result/single_sample.csv' # 年最大值/年多样本

    result,pre_data = step3_run(data_flag=data_flag, img_path=img_path, mode=mode, step2_csv=step2_csv)
    table = result.return_table
