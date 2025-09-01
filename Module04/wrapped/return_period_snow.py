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


class calc_return_period_snow:
    '''
    重现期最大积雪深度及雪压计算
    20250829 增加冻土重现期计算
    '''

    def __init__(self, df_sequence, return_years, CI, fitting_method, img_path, element):
        self.df_sequence = df_sequence
        self.return_years = return_years  # 重现期列表 list
        self.CI = CI
        self.fitting_method = fitting_method  # 拟合方法列表 list
        self.img_path = img_path
        self.element = element

    def calc_snow_pressure(self, max_vals_in):
        '''
        使用重现期积雪深度数据计算雪压
        '''
        snow_prs_dict = {}
        keys = list(max_vals_in.keys())

        for key in keys:
            max_vals = np.array(max_vals_in[key])
            snow_pressure = max_vals * 1e-2 * 0.15 * 9.8  # kN/m**2
            snow_pressure = snow_pressure.round(3)
            snow_prs_dict[key] = snow_pressure.tolist()

        return snow_prs_dict

    def frequency_conversion(self):
        '''
        频率转换
        '''
        n = len(self.df_sequence)
        k = len(self.df_sequence[self.df_sequence['Snow_Depth_Max'] > 0])
        convert_freq = (1 / np.array(self.return_years)) * (n + 1) / (k + 1)
        convert_periods = 1 / convert_freq
        convert_periods = convert_periods.tolist()

        return convert_periods

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

    def calc_confidence_interval(self, data_in, periods):
        '''
        计算参证站重现期的置信区间
        '''
        ci_result = []
        ci_num = 500

        # 置信水平对应的百分位区间 array shape(n,2)
        ci_array = []
        for ci in self.CI:
            bar = (100 - ci) / 2
            left = 100 - ci - bar
            right = ci + bar
            ci_array.append([left, right])

        ci_array = np.array(ci_array) / 100

        if 'Gumbel' in self.fitting_method:
            for i in range(ci_num):
                bootstrap = data_in.sample(n=len(data_in) - 5, replace=True, random_state=i)
                loc, scale = fitting.estimate_parameters_gumbel(bootstrap, method='MOM')
                max_values = fitting.get_max_values_gumbel(periods, loc, scale)  # numpy array
                max_values = max_values.reshape(1, -1)

                if i == 0:
                    all_max_values = max_values
                else:
                    all_max_values = np.concatenate((all_max_values, max_values), axis=0)  # shape(1000,5) 每行是一个重现期结果, 每列是相应的重现期

            # data = np.random.randint(0,500,size=20).reshape(4,5)
            # result = np.quantile(data, CI_array, axis=0) # CI_array:(3,2), result:(3,2,5) 3代表不同区间, 2行代表计算出来的上下限数值, 5列对应不同重现期
            gumbel_ci = np.quantile(all_max_values, ci_array, axis=0)
            gumbel_ci = gumbel_ci.transpose(2, 0, 1)
            gumbel_ci = gumbel_ci.reshape(-1, 2)
            ci_result.append(gumbel_ci)

        if 'P3' in self.fitting_method:
            for i1 in range(ci_num):
                bootstrap = data_in.sample(n=len(data_in) - 5, replace=True, random_state=i1)
                skew, loc, scale = fitting.estimate_parameters_pearson3(bootstrap, method='normal')
                max_values = fitting.get_max_values_pearson3(periods, 0, skew, loc, scale)
                max_values = max_values.reshape(1, -1)

                if i1 == 0:
                    all_max_values = max_values
                else:
                    all_max_values = np.concatenate((all_max_values, max_values), axis=0)  # shape(1000,5) 每行是一个重现期结果, 每列是相应的重现期

            p3_ci = np.quantile(all_max_values, ci_array, axis=0)
            p3_ci = p3_ci.transpose(2, 0, 1)
            p3_ci = p3_ci.reshape(-1, 2)
            ci_result.append(p3_ci)

        # 所有分布的结果拼接
        ci_result = np.array(ci_result)
        ci_result = ci_result.transpose(1, 0, 2)
        ci_result = ci_result.reshape(-1, 2 * len(self.fitting_method))
        ci_result = ci_result.round(3)

        # ci_result转成dataframe
        interval = self.CI
        index = pd.MultiIndex.from_product([self.return_years, interval], names=['重现期(a)', '置信水平(%)'])
        columns = []
        
        for col in self.fitting_method:
            if col == 'Gumbel':
                columns.append('下限（耿贝尔）')
                columns.append('上限（耿贝尔）')
            else:
                columns.append('下限(皮尔逊Ⅲ型)')
                columns.append('上限(皮尔逊Ⅲ型)')
                
        ci_result = pd.DataFrame(ci_result, columns=columns, index=index).reset_index()

        return ci_result

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

    def run_snow(self):
        '''
        forward流程
        '''
        fig, ax = self.get_fig_ax()
    
        # Step0 结果字典创建/数据处理
        result_dict = edict()
        result_dict.return_years = self.return_years
    
        snow_data = self.df_sequence['Snow_Depth_Max'].round(3)
        snow_data = snow_data.dropna()
        
        if snow_data.shape[0] < 10:
            raise Exception('该参证站日数据存在缺测，转换后得到有效历年样本小于10个，不能进行后续重现期计算')
        
        snow_data_save = snow_data.to_frame().copy()
        snow_data_save.insert(loc=0, column='year', value=snow_data_save.index.year)
        snow_data_save.columns = ['年份','最大积雪深度(cm)']
        snow_data_save.reset_index(drop=True, inplace=True)
        result_dict.data = snow_data_save.to_dict(orient='records')
    
        # Step1 频率转换
        convert_periods = self.frequency_conversion()
        
        # Step2 删除0值（与频率转换保持一致）
        snow_data_filtered = snow_data[snow_data > 0]
        
        if snow_data_filtered.shape[0] < 10:
            raise Exception('删除0值后有效样本小于10个，不能进行后续重现期计算')
    
        # Step3 重现期计算（使用过滤后的数据）
        if self.fitting_method is not None:
            result_dict.main_return_result = edict()
            params_dict, max_values_dict, ks_values = self.calc_return_period_values(snow_data_filtered, convert_periods)
            result_dict.main_return_result['max_values'] = max_values_dict
            result_dict.main_return_result['distribution_params'] = params_dict
    
            # 雪压计算
            snow_prs_dict = self.calc_snow_pressure(max_values_dict)
            result_dict.main_return_result['max_values_snow_prs'] = snow_prs_dict
    
        # Step4 重现期的置信区间计算（使用过滤后的数据）
        if self.CI is not None and len(self.CI) != 0:
            ci_result = self.calc_confidence_interval(snow_data_filtered, convert_periods)
            result_dict.confidence_interval = ci_result.to_dict(orient='records')
    
        # Step5 重现期画图（使用过滤后的数据）
        result_dict.img_save_path = edict()
        keys = list(params_dict.keys())
        x = np.linspace(0.01, 100, 1000) # 对应图片频率 (%) 从左到右，1/(x/100)转化为年
    
        if 'Gumbel' in keys:
            y = fitting.get_max_values_gumbel(1/(x/100), params_dict['Gumbel'][0], params_dict['Gumbel'][1])
            save_path = self.plot_result(fig, ax, snow_data_filtered, x, y, '积雪深度', 'Gumbel', ks_values['Gumbel_ks'])
            result_dict.img_save_path['Gumbel_plot'] = save_path
    
        if 'P3' in keys:
            y = fitting.get_max_values_pearson3(1/(x/100), 0, params_dict['P3'][0], params_dict['P3'][1], params_dict['P3'][2])
            save_path = self.plot_result(fig, ax, snow_data_filtered, x, y, '积雪深度', 'Pearson3', ks_values['P3_ks'])
            result_dict.img_save_path['P3_plot'] = save_path
    
        # 关闭图框
        plt.cla()
        plt.close('all')

        return result_dict
    
    def run_frs(self):
        '''
        forward流程 冻土
        '''
        fig, ax = self.get_fig_ax()
    
        # Step0 结果字典创建/数据处理
        result_dict = edict()
        result_dict.return_years = self.return_years
    
        frs_data = self.df_sequence['FRS_Depth_Max'].round(3)
        frs_data = frs_data.dropna()
        
        if frs_data.shape[0] < 10:
            raise Exception('该参证站日数据存在缺测，转换后得到有效历年样本小于10个，不能进行后续重现期计算')
        
        frs_data_save = frs_data.to_frame().copy()
        frs_data_save.insert(loc=0, column='year', value=frs_data_save.index.year)
        frs_data_save.columns = ['年份','最大冻土深度(cm)']
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
    
            # 雪压计算
            frs_prs_dict = self.calc_snow_pressure(max_values_dict)
            result_dict.main_return_result['max_values_frs_prs'] = frs_prs_dict
    
        # Step4 重现期的置信区间计算（使用过滤后的数据）
        if self.CI is not None and len(self.CI) != 0:
            ci_result = self.calc_confidence_interval(frs_data_filtered, self.return_years)
            result_dict.confidence_interval = ci_result.to_dict(orient='records')
    
        # Step5 重现期画图（使用过滤后的数据）
        result_dict.img_save_path = edict()
        keys = list(params_dict.keys())
        x = np.linspace(0.01, 100, 1000) # 对应图片频率 (%) 从左到右，1/(x/100)转化为年
    
        if 'Gumbel' in keys:
            y = fitting.get_max_values_gumbel(1/(x/100), params_dict['Gumbel'][0], params_dict['Gumbel'][1])
            save_path = self.plot_result(fig, ax, frs_data_filtered, x, y, '冻土深度', 'Gumbel', ks_values['Gumbel_ks'])
            result_dict.img_save_path['Gumbel_plot'] = save_path
    
        if 'P3' in keys:
            y = fitting.get_max_values_pearson3(1/(x/100), 0, params_dict['P3'][0], params_dict['P3'][1], params_dict['P3'][2])
            save_path = self.plot_result(fig, ax, frs_data_filtered, x, y, '冻土深度', 'Pearson3', ks_values['P3_ks'])
            result_dict.img_save_path['P3_plot'] = save_path
    
        # 关闭图框
        plt.cla()
        plt.close('all')

        return result_dict


if __name__ == '__main__':
    monthly_df = pd.read_csv(cfg.FILES.QH_DATA_MONTH, low_memory=False)
    monthly_df = monthly_df[['Station_Name','Station_Id_C','Lon','Lat','Datetime','Snow_Depth_Max', 'FRS_Depth_Max']]
    post_monthly_df = monthly_data_processing(monthly_df, '1990,2023')
    post_monthly_df = post_monthly_df[post_monthly_df['Station_Id_C']=='56067']
    post_monthly_df = post_monthly_df[post_monthly_df.index.year>=1990]
    post_monthly_df = post_monthly_df[post_monthly_df.index.year<=2023]
    df_sequence = post_monthly_df.resample('1A').max()
    
    # path = r'C:/Users/MJY/Desktop/Ckextreme(1).xlsx'
    # df_sequence = pd.read_excel(path)
    # df_sequence.columns = ['Datetime','TEM_Max','TEM_Min','PRE_Time_2020','WIN_S_Max','Snow_Depth_Max','WIN_S_Inst_Max']
    # df_sequence['Datetime'] = df_sequence['Datetime'].map(str)
    # df_sequence['Datetime'] = pd.to_datetime(df_sequence['Datetime'],format='%Y')
    # df_sequence.set_index('Datetime',inplace=True)
    
    element = 'snow'
    return_years = [2, 3, 5, 10, 20, 30, 50, 100]
    CI = None
    fitting_method = ['Gumbel', 'P3']
    img_path = r'C:/Users/mjynj/Desktop/result'
    snow = calc_return_period_snow(df_sequence, return_years, CI, fitting_method, img_path, element)
    snow_result = snow.run_snow()
