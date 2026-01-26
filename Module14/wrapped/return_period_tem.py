import numpy as np
import pandas as pd
import probscale
import matplotlib
import matplotlib.pyplot as plt
from scipy import stats
import Utils.distribution_fitting as fitting
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_processing import daily_data_processing
from Utils.get_local_data import get_local_data
from matplotlib import font_manager
font = font_manager.FontProperties(fname=cfg.FILES.FONT)
matplotlib.use('agg')

class calc_return_period_tem:

    def __init__(self, df_sequence, return_years, fitting_method, img_path):
        self.df_sequence = df_sequence
        self.return_years = return_years
        self.fitting_method = fitting_method
        self.img_path = img_path
        self.element_name = ['ex_tem_max', 'ex_tem_min']

    def calc_return_period_values(self, data_in, ele_name):
        '''
        计算不同重现期的最大数值
        '''
        params_dict = edict()  # 参数字典
        max_values_dict = edict()  # 重现期结果列表
        ks_values = edict()  # KS检验结果dict

        if 'Gumbel' in self.fitting_method:
            if (ele_name == 'ex_tem_max') or (ele_name == 'base_tem_max'):
                loc, scale = fitting.estimate_parameters_gumbel(data_in,method='MOM')  # 根据现有数据计算该分布的参数
                max_values = fitting.get_max_values_gumbel(self.return_years, loc, scale)
                sample_gumbel = stats.gumbel_r.rvs(loc, scale, 200)
                _, ks_result = fitting.kolmogorov_smirnov_test(sample_gumbel, data_in)  # KS检验

            elif (ele_name == 'ex_tem_min') or (ele_name == 'base_tem_min'):
                # x0 = data_in.max() + 5
                # data_in_tmp = x0 - data_in # 极小值序列转换为极大值序列
                # loc, scale = fitting.estimate_parameters_gumbel(data_in_tmp,method='MOM')
                # max_values = fitting.get_max_values_gumbel(self.return_years, loc, scale)
                # max_values = x0 - max_values # 还原后的极小值重现期对应的数值
                # sample_gumbel = stats.gumbel_r.rvs(loc, scale, 200)
                # _, ks_result = fitting.kolmogorov_smirnov_test(sample_gumbel, data_in_tmp)  # KS检验
                
                # 改进的极小值Gumbel分布处理
                # 使用Gumbel极小值分布（Gumbel Type III）
                data_in_neg = -data_in  # 将极小值转换为极大值
                loc, scale = fitting.estimate_parameters_gumbel(data_in_neg, method='MOM')
                max_values_neg = fitting.get_max_values_gumbel(self.return_years, loc, scale)
                max_values = -max_values_neg  # 转换回极小值
                
                # KS检验使用原始数据和对应的极小值分布
                sample_gumbel_min = -stats.gumbel_r.rvs(loc, scale, 200)
                _, ks_result = fitting.kolmogorov_smirnov_test(sample_gumbel_min, data_in)
                
            params_dict['Gumbel'] = [loc, scale]
            max_values_dict['耿贝尔'] = max_values.round(1).tolist()
            ks_values['Gumbel_ks'] = ks_result

        if 'P3' in self.fitting_method:
            if (ele_name == 'ex_tem_max') or (ele_name == 'base_tem_max'):
                # 极大值直接使用Pearson3分布
                skew, loc, scale = fitting.estimate_parameters_pearson3(data_in, method='normal')
                max_values = fitting.get_max_values_pearson3(self.return_years, 0, skew, loc, scale)
                sample_p3 = stats.pearson3.rvs(skew, loc, scale, 200)
                _, ks_result = fitting.kolmogorov_smirnov_test(sample_p3, data_in)
                
            elif (ele_name == 'ex_tem_min') or (ele_name == 'base_tem_min'):
                # 改进的极小值Pearson3分布处理
                # 方法1：使用负值转换
                data_in_neg = -data_in
                skew, loc, scale = fitting.estimate_parameters_pearson3(data_in_neg, method='normal')
                max_values_neg = fitting.get_max_values_pearson3(self.return_years, 0, skew, loc, scale)
                max_values = -max_values_neg
                
                # KS检验
                sample_p3_min = -stats.pearson3.rvs(skew, loc, scale, 200)
                _, ks_result = fitting.kolmogorov_smirnov_test(sample_p3_min, data_in)

            params_dict['P3'] = [skew, loc, scale]
            max_values_dict['皮尔逊Ⅲ型'] = max_values.round(1).tolist()
            ks_values['P3_ks'] = ks_result

        return params_dict, max_values_dict, ks_values

    def get_fig_ax(self):
        fig, ax = plt.subplots(figsize=(7, 5))
        return fig, ax
    
    def plot_result(self, fig, ax, data_in, sample_x, sample_y, y_axis_name, method_name, ks_val):
        '''
        画重现期拟合曲线图，x轴为概率坐标
        '''
        # plt.rcParams['font.sans-serif'] = 'SimHei'
        plt.rcParams['axes.unicode_minus'] = False
        # fig, ax = plt.subplots(figsize=(7, 5))

        # 计算数据范围，用于自动设置y轴范围
        # 过滤掉NaN和Inf值
        data_in_clean = data_in[np.isfinite(data_in)]
        sample_y_clean = sample_y[np.isfinite(sample_y)]
        
        if len(data_in_clean) == 0 or len(sample_y_clean) == 0:
            # 如果没有有效数据，使用默认范围
            data_min, data_max = -50, 50
            margin = 5
        else:
            combined_data = np.concatenate([data_in_clean, sample_y_clean])
            data_min = np.min(combined_data)
            data_max = np.max(combined_data)
            data_range = data_max - data_min
            
            # 如果数据范围太小或为0，设置最小边距
            if data_range <= 1e-10:
                margin = max(abs(data_min), abs(data_max), 1) * 0.1
            else:
                margin = data_range * 0.1  # 10%的边距
        
        # 确保y轴范围值是有限的
        y_min = data_min - margin
        y_max = data_max + margin
        
        # 最后检查，确保没有NaN或Inf
        if not (np.isfinite(y_min) and np.isfinite(y_max)):
            y_min, y_max = -50, 50
        
        if y_axis_name == '极端最高气温':
            new_y_axis_name = y_axis_name + ' (°C)'
            data_in = np.sort(data_in)[::-1]
            # 自动适应y轴范围
            ax.set_ylim(y_min, y_max)

        elif y_axis_name == '基本气温(最高)':
            new_y_axis_name = y_axis_name + ' (°C)'
            data_in = np.sort(data_in)[::-1]
            # 自动适应y轴范围
            ax.set_ylim(y_min, y_max)

        elif (y_axis_name == '极端最低气温') or (y_axis_name == '基本气温(最低)'):
            new_y_axis_name = y_axis_name + ' (°C)'
            data_in = np.sort(data_in)  # 从小到大排序
            ax.invert_yaxis()
            # 自动适应y轴范围（注意反转轴的顺序）
            ax.set_ylim(y_max, y_min)

        ax.grid(True)
        ax.set_xlabel('KS-test: ' + str(ks_val.round(3)) + '   频率P(%)', fontproperties=font)
        ax.set_ylabel(new_y_axis_name, fontproperties=font)
        ax.set_xscale('prob')
        plt.xticks(size=7)

        empi_prob = (np.arange(len(data_in)) + 1) / (len(data_in) + 1) * 100
        ax.set_xlim(0.1, 99.5)

        ax.scatter(empi_prob, data_in, marker='o', s=8, c='red', edgecolors='k', label='经验概率数据点')
        ax.plot(sample_x, sample_y, '--', lw=1, label=method_name + '分布拟合曲线')
        ax.legend(prop=font)

        save_path = self.img_path + '/{}_{}.png'.format(y_axis_name, method_name)
        plt.savefig(save_path, dpi=200, format='png', bbox_inches='tight')

        # 关闭图框
        plt.cla()

        return save_path

    def run(self):
        '''
        forward流程
        '''
        fig, ax = self.get_fig_ax()
        result_dict = edict()
        result_dict.return_years = self.return_years

        if 'ex_tem_max' in self.element_name:
            max_tem_seq = self.df_sequence['TEM_Max'].resample('1A', closed='right', label='right').max()
            max_tem_seq = max_tem_seq.round(1)

            max_tem_seq_save = max_tem_seq.to_frame().copy()
            max_tem_seq_save.insert(loc=0, column='year', value=max_tem_seq_save.index.year)
            max_tem_seq_save.columns = ['年份','极端最高气温(°C)']
            max_tem_seq_save.reset_index(drop=True, inplace=True)
            result_dict.max_tem = edict()
            result_dict.max_tem.data = max_tem_seq_save.to_dict(orient='records')

            # 重现期计算
            year_vals = max_tem_seq.dropna()
            if self.fitting_method is not None:
                params_dict, max_values_dict, ks_values = self.calc_return_period_values(year_vals, 'ex_tem_max')
                result_dict.max_tem.return_result = edict()
                result_dict.max_tem.return_result['max_values'] = max_values_dict
                result_dict.max_tem.return_result['distribution_params'] = params_dict
                # result_dict.max_tem['p3_base'] = p3_base

            # 画图
            result_dict.max_tem.img_save_path = edict()
            keys = list(params_dict.keys())
            x = np.linspace(0.01, 100, 1000)

            if 'Gumbel' in keys:
                y = fitting.get_max_values_gumbel(100 / x, params_dict['Gumbel'][0], params_dict['Gumbel'][1])
                save_path = self.plot_result(fig, ax, max_tem_seq, x, y, '极端最高气温', 'Gumbel', ks_values['Gumbel_ks'])
                result_dict.max_tem.img_save_path['Gumbel_plot'] = save_path

            if 'P3' in keys:
                y = fitting.get_max_values_pearson3(100 / x, 0, params_dict['P3'][0], params_dict['P3'][1], params_dict['P3'][2])
                save_path = self.plot_result(fig, ax, max_tem_seq, x, y, '极端最高气温', 'Pearson3', ks_values['P3_ks'])
                result_dict.max_tem.img_save_path['P3_plot'] = save_path

        if 'ex_tem_min' in self.element_name:
            min_tem_seq = self.df_sequence['TEM_Min'].resample('1A', closed='right', label='right').min()
            min_tem_seq = min_tem_seq.round(1)

            min_tem_seq_save = min_tem_seq.to_frame().copy()
            min_tem_seq_save.insert(loc=0, column='year', value=min_tem_seq_save.index.year)
            min_tem_seq_save.columns = ['年份','极端最低气温(°C)']
            min_tem_seq_save.reset_index(drop=True, inplace=True)
            result_dict.min_tem = edict()
            result_dict.min_tem.data = min_tem_seq_save.to_dict(orient='records')
            
            # 重现期计算
            year_vals = min_tem_seq.dropna()
            if self.fitting_method is not None:
                params_dict, max_values_dict, ks_values = self.calc_return_period_values(year_vals, 'ex_tem_min')
                result_dict.min_tem.return_result = edict()
                result_dict.min_tem.return_result['max_values'] = max_values_dict
                result_dict.min_tem.return_result['distribution_params'] = params_dict
                # result_dict.min_tem['p3_base'] = p3_base

            # 画图 - 改进的绘图逻辑
            result_dict.min_tem.img_save_path = edict()
            keys = list(params_dict.keys())
            x = np.linspace(0.01, 100, 1000)

            if 'Gumbel' in keys:
                # 改进的Gumbel极小值绘图
                y_neg = fitting.get_max_values_gumbel(100/x, params_dict['Gumbel'][0], params_dict['Gumbel'][1])
                y = -y_neg  # 转换回极小值
                save_path = self.plot_result(fig, ax, min_tem_seq, x, y, '极端最低气温', 'Gumbel', ks_values['Gumbel_ks'])
                result_dict.min_tem.img_save_path['Gumbel_plot'] = save_path

            if 'P3' in keys:
                # 改进的P3极小值绘图
                y_neg = fitting.get_max_values_pearson3(100/x, 0, params_dict['P3'][0], params_dict['P3'][1], params_dict['P3'][2])
                y = -y_neg  # 转换回极小值
                save_path = self.plot_result(fig, ax, min_tem_seq, x, y, '极端最低气温', 'Pearson3', ks_values['P3_ks'])
                result_dict.min_tem.img_save_path['P3_plot'] = save_path

        # 关闭图框
        plt.cla()
        plt.close('all')

        return result_dict


if __name__ == '__main__':
    years = '1980,2020'
    sta_ids = '52866,52745'
    day_eles = ('Station_Id_C,Station_Name,Lat,Lon,Datetime,Year,Mon,Day,' + 'TEM_Max,TEM_Min').split(',')
    daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')
    df_sequence = daily_df[daily_df['Station_Id_C']=='52866']
    sub_df = daily_df[daily_df['Station_Id_C']=='52745']
    
    # path = r'C:/Users/MJY/Desktop/Ckextreme(1).xlsx'
    # df_sequence = pd.read_excel(path)
    # df_sequence.columns = ['Datetime','TEM_Max','TEM_Min','PRE_Time_2020','WIN_S_Max','Snow_Depth_Max','WIN_S_Inst_Max']
    # df_sequence['Datetime'] = df_sequence['Datetime'].map(str)
    # df_sequence['Datetime'] = pd.to_datetime(df_sequence['Datetime'],format='%Y')
    # df_sequence.set_index('Datetime',inplace=True)
    # sub_df = df_sequence
    
    return_years = [2,3,5,10,20,30,50,100]
    CI = None
    fitting_method = ['Gumbel', 'P3']
    element_name = ['ex_tem_max', 'ex_tem_min', 'base_tem_max', 'base_tem_min']
    img_path = r'C:/Users/MJY/Desktop/result'
    from_database = 0
    max_threshold = 0
    min_threshold = 0
    intercept = True
    ccc = calc_return_period_tem(df_sequence, return_years, CI, fitting_method, element_name, img_path, sub_df, from_database, max_threshold, min_threshold, intercept)
    tem_result = ccc.run()
    
    # Gumbel画直线代码
    # min_tem_seq = day_data['TEM_Min'].resample('1A', closed='right', label='right').min()
    # min_tem_seq = min_tem_seq.round(1)
    # min_tem_seq.index = min_tem_seq.index.strftime('%Y')
    
    # skew, loc, scale = fitting.estimate_parameters_pearson3(min_tem_seq, method='normal')  # 根据现有数据计算该分布的参数
    # max_values = fitting.get_max_values_pearson3(return_years, 0, skew, loc, scale)
    # print(max_values)
    
    # max_values = 2*loc-max_values
    # print(max_values)
    
    # # plot
    # x = np.linspace(0.01, 100, 1000)
    # x = 1-1/(100/x)
    # x = np.log(-np.log(x))
    # y = mu-beta*x
    
    # # y = fitting.get_max_values_gumbel(100/x, mu, beta)
    # # y = 2*loc-y
    
    # def get_fig_ax():
    #     fig, ax = plt.subplots(figsize=(7, 5))
    #     return fig, ax
    
    # def plot_result(fig, ax, data_in, sample_x, sample_y, y_axis_name, method_name):
    #     '''
    #     画重现期拟合曲线图，x轴为概率坐标
    #     '''
    #     # plt.rcParams['font.sans-serif'] = 'SimHei'
    #     plt.rcParams['axes.unicode_minus'] = False
    #     # fig, ax = plt.subplots(figsize=(7, 5))

    #     if y_axis_name == '极端最高气温':
    #         new_y_axis_name = y_axis_name + ' (°C)'
    #         data_in = np.sort(data_in)[::-1]
    #         ax.set_ylim(30, 50)

    #     elif y_axis_name == '基本气温(最高)':
    #         new_y_axis_name = y_axis_name + ' (°C)'
    #         data_in = np.sort(data_in)[::-1]
    #         ax.set_ylim(20, 40)

    #     elif (y_axis_name == '极端最低气温') or (y_axis_name == '基本气温(最低)'):
    #         new_y_axis_name = y_axis_name + ' (mm)'
    #         data_in = np.sort(data_in)  # 从小到大排序
    #         ax.invert_yaxis()

    #     ax.grid(True)
    #     ax.set_xlabel('log(-log(p/100))', fontproperties=font)
    #     ax.set_ylabel(new_y_axis_name, fontproperties=font)
    #     # ax.set_xscale('log')
    #     plt.xticks(size=7)

    #     empi_prob = (data_in-mu)/(-beta)
                
    #     # ax.set_xlim(0.1, 99.5)
    #     ax.scatter(empi_prob, data_in, marker='o', s=8, c='red', edgecolors='k', label='经验概率数据点')
    #     ax.plot(sample_x, sample_y, '--', lw=1, label=method_name + '分布拟合曲线')

    #     ax.legend(prop=font)
    #     plt.savefig(r'C:\Users\MJY\Desktop\1.png', dpi=200, format='png', bbox_inches='tight')
        
    # fig, ax = get_fig_ax()
    # plot_result(fig, ax, min_tem_seq, x, y, '极端最高气温', 'gumbel')
