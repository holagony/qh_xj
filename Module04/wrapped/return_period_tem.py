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
from Module01.wrapped.correlation_analysis import linear_regression
from Utils.pearson3 import pearson_type3
from Utils.get_local_data import get_local_data
from matplotlib import font_manager
font = font_manager.FontProperties(fname=cfg.FILES.FONT)
matplotlib.use('agg')

class calc_return_period_tem:
    '''
    重现期极端最高温度/极端最低温度/月温度计算
    df_sequence: 参证站日数据要素数据，用于计算极端最高/最低气温/基本气温
    return_years: 重现期年份 list
    CI: 置信水平 list
    fitting_method: 重现期计算方法 list
    element_name: 计算的要素中文名 list
    '''

    def __init__(self, df_sequence, return_years, CI, fitting_method, element_name, img_path, sub_df, from_database, max_threshold, min_threshold, intercept):
        self.df_sequence = df_sequence
        self.return_years = return_years
        self.CI = CI
        self.fitting_method = fitting_method
        self.element_name = element_name
        self.img_path = img_path
        self.sub_df = sub_df
        self.from_database = from_database
        self.intercept = intercept
        self.max_threshold = max_threshold
        self.min_threshold = min_threshold
        
        if self.max_threshold == None:
            self.max_threshold = 0
        if self.min_threshold == None:
            self.min_threshold = 50

    def calc_correlation(self, main_df, sub_df):
        '''
        参证站和厂址站的相关性分析，以及厂址站重现期
        '''
        if self.from_database == 1:
            sub_df.columns = ['最高气温', '最低气温']
            sub_tem_max = sub_df['最高气温'].resample('1D', closed='right', label='right').max().to_frame()
            sub_tem_min = sub_df['最低气温'].resample('1D', closed='right', label='right').min().to_frame()
        elif self.from_database == 0:
            sub_tem_max = sub_df['TEM_Max'].to_frame()
            sub_tem_max.columns = ['最高气温']
            sub_tem_min = sub_df['TEM_Min'].to_frame()
            sub_tem_min.columns = ['最低气温']

        sub_tem_max = sub_tem_max[sub_tem_max > self.max_threshold]
        sub_tem_min = sub_tem_min[sub_tem_min < self.min_threshold]

        # 参证站温度日数据
        main_tem_max = main_df['TEM_Max'].to_frame()
        main_tem_min = main_df['TEM_Min'].to_frame()

        # 参证站数据和厂址站数据合并，并删除时间不对应的行
        concat_tem_max = pd.concat([main_tem_max, sub_tem_max], axis=1)
        concat_tem_max = concat_tem_max.dropna(how='any')

        concat_tem_min = pd.concat([main_tem_min, sub_tem_min], axis=1)
        concat_tem_min = concat_tem_min.dropna(how='any')

        if len(concat_tem_max) < 200:  # 没有数据的情况
            params_max = np.nan
            data_points_max = np.nan

        elif len(concat_tem_max) >= 200:
            w1, b1, r_square1 = linear_regression(concat_tem_max['TEM_Max'], concat_tem_max['最高气温'], intercept=self.intercept)
            w1 = round(w1,3)
            b1 = round(b1,3)
            r_square1 = round(r_square1,5)
            params_max = [w1, b1, r_square1]
            concat_tem_max = concat_tem_max.sample(n=200)
            data_points_max = concat_tem_max.values.tolist()

        if len(concat_tem_min) < 200:  # 没有数据的情况
            params_min = np.nan
            data_points_min = np.nan

        elif len(concat_tem_min) >= 200:
            w2, b2, r_square2 = linear_regression(concat_tem_min['TEM_Min'], concat_tem_min['最低气温'], intercept=self.intercept)
            w2 = round(w2,3)
            b2 = round(b2,3)
            r_square2 = round(r_square2,5)
            params_min = [w2, b2, r_square2]
            concat_tem_min = concat_tem_min.sample(n=200)
            data_points_min = concat_tem_min.values.tolist()

        return params_max, data_points_max, params_min, data_points_min

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
                x0 = data_in.max() + 5
                data_in_tmp = x0 - data_in # 极小值序列转换为极大值序列
                loc, scale = fitting.estimate_parameters_gumbel(data_in_tmp,method='MOM')
                max_values = fitting.get_max_values_gumbel(self.return_years, loc, scale)
                max_values = x0 - max_values # 还原后的极小值重现期对应的数值
                sample_gumbel = stats.gumbel_r.rvs(loc, scale, 200)
                _, ks_result = fitting.kolmogorov_smirnov_test(sample_gumbel, data_in_tmp)  # KS检验
                
            params_dict['Gumbel'] = [loc, scale]
            max_values_dict['耿贝尔'] = max_values.round(1).tolist()
            ks_values['Gumbel_ks'] = ks_result

        if 'P3' in self.fitting_method: # p3最小用chatgpt提供的镜像方法
            skew, loc, scale = fitting.estimate_parameters_pearson3(data_in, method='normal')
            max_values = fitting.get_max_values_pearson3(self.return_years, 0, skew, loc, scale)

            if (ele_name == 'ex_tem_min') or (ele_name == 'base_tem_min'):
                max_values = 2*loc - max_values # 根据对称，还原后的极小值重现期对应的数值

            sample_p3 = stats.pearson3.rvs(skew, loc, scale, 200)
            _, ks_result = fitting.kolmogorov_smirnov_test(sample_p3, data_in)
            params_dict['P3'] = [skew, loc, scale]
            max_values_dict['皮尔逊Ⅲ型'] = max_values.round(1).tolist()
            ks_values['P3_ks'] = ks_result

            # 新增P3调参 收集初始矩法参数
            # p3_result = pearson_type3(element_name=ele_name, 
            #                           data=data_in, 
            #                           rp=self.return_years,
            #                           img_path=self.img_path, 
            #                           mode=1, sv_ratio=0, ex_fitting=True, manual_cs_cv=None)
            # p3_base = p3_result

        return params_dict, max_values_dict, ks_values#, p3_base

    def calc_confidence_interval(self, data_in, ele_name):
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
            all_max_values = []
            for i0 in range(ci_num):
                bootstrap = data_in.sample(n=len(data_in)-5, replace=True, random_state=i0)

                if ele_name == 'ex_tem_max':
                    loc, scale = fitting.estimate_parameters_gumbel(bootstrap, method='MOM')
                    max_values = fitting.get_max_values_gumbel(self.return_years, loc, scale)  # numpy array
                    max_values = max_values.reshape(1, -1)

                elif ele_name == 'ex_tem_min':
                    x0 = bootstrap.max() + 5
                    bootstrap = x0 - bootstrap # 极小值序列转换为极大值序列
                    loc, scale = fitting.estimate_parameters_gumbel(bootstrap, method='MOM')
                    max_values = fitting.get_max_values_gumbel(self.return_years, loc, scale)
                    max_values = x0 - max_values # 还原后的极小值重现期对应的数值
                    max_values = max_values.reshape(1, -1)

                all_max_values.append(max_values)

            all_max_values = np.concatenate(all_max_values, axis=0)  # shape(1000,5) 每行是一个重现期结果, 每列是相应的重现期
            gumbel_ci = np.quantile(all_max_values, ci_array, axis=0)
            gumbel_ci = gumbel_ci.transpose(2, 0, 1)
            gumbel_ci = gumbel_ci.reshape(-1, 2)
            ci_result.append(gumbel_ci)

        if 'P3' in self.fitting_method:
            all_max_values = []
            for i1 in range(ci_num):
                bootstrap = data_in.sample(n=len(data_in)-5, replace=True, random_state=i1)

                if ele_name == 'ex_tem_max':
                    skew, loc, scale = fitting.estimate_parameters_pearson3(bootstrap, method='normal')
                    max_values = fitting.get_max_values_pearson3(self.return_years, 0, skew, loc, scale)
                    max_values = max_values.reshape(1, -1)

                elif ele_name == 'ex_tem_min':
                    skew, loc, scale = fitting.estimate_parameters_pearson3(bootstrap, method='normal')
                    max_values = fitting.get_max_values_pearson3(self.return_years, 0, skew, loc, scale)
                    max_values = 2*loc - max_values
                    max_values = max_values.reshape(1, -1)

                all_max_values.append(max_values)

            all_max_values = np.concatenate(all_max_values, axis=0)  # shape(1000,5) 每行是一个重现期结果, 每列是相应的重现期
            p3_ci = np.quantile(all_max_values, ci_array, axis=0)
            p3_ci = p3_ci.transpose(2, 0, 1)
            p3_ci = p3_ci.reshape(-1, 2)
            ci_result.append(p3_ci)

        # 所有分布的结果拼接
        ci_result = np.array(ci_result)
        ci_result = ci_result.transpose(1, 0, 2)

        if (ele_name == 'ex_tem_min') and ('Frechet' in self.fitting_method):
            num = len(self.fitting_method)-1
            ci_result = ci_result.reshape(-1, 2 * num)
        else:
            ci_result = ci_result.reshape(-1, 2 * len(self.fitting_method))
            
        ci_result = ci_result.round(1)

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
        # fig, ax = plt.subplots(figsize=(7, 5))

        if y_axis_name == '极端最高气温':
            new_y_axis_name = y_axis_name + ' (°C)'
            data_in = np.sort(data_in)[::-1]
            ax.set_ylim(20, 40)

        elif y_axis_name == '基本气温(最高)':
            new_y_axis_name = y_axis_name + ' (°C)'
            data_in = np.sort(data_in)[::-1]
            ax.set_ylim(20, 40)

        elif (y_axis_name == '极端最低气温') or (y_axis_name == '基本气温(最低)'):
            new_y_axis_name = y_axis_name + ' (°C)'
            data_in = np.sort(data_in)  # 从小到大排序
            ax.invert_yaxis()

        ax.grid(True)
        ax.set_xlabel('KS-test: ' + str(ks_val.round(5)) + '   频率P(%)', fontproperties=font)
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
        result_dict.extra_station = edict()

        if 'ex_tem_max' in self.element_name:
            max_tem_seq = self.df_sequence['TEM_Max'].resample('1A', closed='right', label='right').max()
            max_tem_seq = max_tem_seq.round(1)

            year_vals = max_tem_seq.dropna()
            if year_vals.shape[0] < 15:
                raise Exception('该参证站日数据存在缺测，转换后得到有效历年样本小于15个，不能进行后续重现期计算')

            max_tem_seq_save = max_tem_seq.to_frame().copy()
            max_tem_seq_save.insert(loc=0, column='year', value=max_tem_seq_save.index.year)
            max_tem_seq_save.columns = ['年份','极端最高气温(°C)']
            max_tem_seq_save.reset_index(drop=True, inplace=True)
            result_dict.max_tem = edict()
            result_dict.max_tem.data = max_tem_seq_save.to_dict(orient='records')

            # 重现期计算
            if self.fitting_method is not None:
                params_dict, max_values_dict, ks_values = self.calc_return_period_values(year_vals, 'ex_tem_max')
                result_dict.max_tem.return_result = edict()
                result_dict.max_tem.return_result['max_values'] = max_values_dict
                result_dict.max_tem.return_result['distribution_params'] = params_dict
                # result_dict.max_tem['p3_base'] = p3_base

            # 置信区间
            if self.CI is not None and len(self.CI) != 0:
                ci_result = self.calc_confidence_interval(year_vals, 'ex_tem_max')
                result_dict.max_tem.confidence_interval = ci_result.to_dict(orient='records')

            # 厂址站相关分析 重现期转换
            if self.sub_df is not None and len(self.sub_df) != 0:
                result_dict.extra_station.max_tem = edict()
                params_max, data_points_max, _, _ = self.calc_correlation(self.df_sequence, self.sub_df)

                if params_max is np.nan:
                    result_dict.extra_station.max_tem['max_values'] = np.nan
                    result_dict.extra_station.max_tem['params'] = np.nan
                    result_dict.extra_station.max_tem['data'] = np.nan
                    result_dict.extra_station.max_tem['msg'] = '筛选后没有数据，无法计算厂址站相关系数和重现期结果'

                else:
                    sub_max_vals = edict()
                    for key in list(max_values_dict.keys()):
                        max_vals = np.array(max_values_dict[key]) * params_max[0] + params_max[1]
                        sub_max_vals[key] = max_vals.round(1).tolist()

                    result_dict.extra_station.max_tem['max_values'] = sub_max_vals
                    result_dict.extra_station.max_tem['params'] = params_max
                    result_dict.extra_station.max_tem['data'] = data_points_max

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

            year_vals = min_tem_seq.dropna()
            if year_vals.shape[0] < 15:
                raise Exception('该参证站日数据存在缺测，转换后得到有效历年样本小于15个，不能进行后续重现期计算')

            min_tem_seq_save = min_tem_seq.to_frame().copy()
            min_tem_seq_save.insert(loc=0, column='year', value=min_tem_seq_save.index.year)
            min_tem_seq_save.columns = ['年份','极端最低气温(°C)']
            min_tem_seq_save.reset_index(drop=True, inplace=True)
            result_dict.min_tem = edict()
            result_dict.min_tem.data = min_tem_seq_save.to_dict(orient='records')
            
            # 重现期计算
            if self.fitting_method is not None:
                params_dict, max_values_dict, ks_values = self.calc_return_period_values(year_vals, 'ex_tem_min')
                result_dict.min_tem.return_result = edict()
                result_dict.min_tem.return_result['max_values'] = max_values_dict
                result_dict.min_tem.return_result['distribution_params'] = params_dict
                # result_dict.min_tem['p3_base'] = p3_base

            # 置信区间
            if self.CI is not None and len(self.CI) != 0:
                ci_result = self.calc_confidence_interval(year_vals, 'ex_tem_min')
                result_dict.min_tem.confidence_interval = ci_result.to_dict(orient='records')

            # 厂址站相关分析 重现期转换
            if self.sub_df is not None and len(self.sub_df) != 0:
                result_dict.extra_station.min_tem = edict()
                _, _, params_min, data_points_min = self.calc_correlation(self.df_sequence, self.sub_df)

                if params_min is np.nan:
                    result_dict.extra_station.min_tem['max_values'] = np.nan
                    result_dict.extra_station.min_tem['params'] = np.nan
                    result_dict.extra_station.min_tem['data'] = np.nan
                    result_dict.extra_station.min_tem['msg'] = '设定阈值过大，导致筛选后没有数据，无法计算厂址站相关系数和重现期结果'

                else:
                    sub_max_vals = edict()
                    for key in list(max_values_dict.keys()):
                        max_vals = np.array(max_values_dict[key]) * params_min[0] + params_min[1]
                        sub_max_vals[key] = max_vals.round(1).tolist()

                    result_dict.extra_station.min_tem['max_values'] = sub_max_vals
                    result_dict.extra_station.min_tem['params'] = params_min
                    result_dict.extra_station.min_tem['data'] = data_points_min

            # 画图
            result_dict.min_tem.img_save_path = edict()
            keys = list(params_dict.keys())
            x = np.linspace(0.01, 100, 1000)
            x0 = min_tem_seq.max() + 5 # 5度

            if 'Gumbel' in keys:
                y = x0 - fitting.get_max_values_gumbel(100/x, params_dict['Gumbel'][0], params_dict['Gumbel'][1])
                save_path = self.plot_result(fig, ax, min_tem_seq, x, y, '极端最低气温', 'Gumbel', ks_values['Gumbel_ks'])
                result_dict.min_tem.img_save_path['Gumbel_plot'] = save_path

            if 'P3' in keys:
                y = fitting.get_max_values_pearson3(100/x, 0, params_dict['P3'][0], params_dict['P3'][1], params_dict['P3'][2])
                loc = params_dict['P3'][1]
                y = 2*loc - y
                save_path = self.plot_result(fig, ax, min_tem_seq, x, y, '极端最低气温', 'Pearson3', ks_values['P3_ks'])
                result_dict.min_tem.img_save_path['P3_plot'] = save_path

        if 'base_tem_max' in self.element_name:  # 不算置信区间 不画图
            # 先找最高温度月
            df_monthly = self.df_sequence['TEM_Max'].resample('1M', closed='right', label='right').mean().to_frame()
            time_idx = self.df_sequence.groupby([self.df_sequence.index.year])['TEM_Max'].idxmax().dt.strftime("%Y-%m").tolist()
                    
            # 提取历年最高温度月，对应的月平均最高气温数据
            for i in range(len(time_idx)):
                data = df_monthly.loc[time_idx[i]]  # 每年最低气温的月份的所有日数据

                if i == 0:
                    base_tem_max = data
                else:
                    base_tem_max = pd.concat([base_tem_max, data], axis=0)

            base_tem_max = base_tem_max.round(1)
            base_tem_max.insert(loc=0, column='日期', value=base_tem_max.index.strftime("%Y-%m"))
            base_tem_max.reset_index(drop=True, inplace=True)

            year_vals = base_tem_max.dropna()
            if year_vals.shape[0] < 15:
                raise Exception('该参证站日数据存在缺测，转换后得到有效历年样本小于15个，不能进行后续重现期计算')

            base_tem_max_save = base_tem_max.copy()
            base_tem_max_save.columns = ['年月','基本最高气温(°C)']
            result_dict.base_tem_max = edict()
            result_dict.base_tem_max.data = base_tem_max_save.to_dict(orient='records')
            
            # 重现期计算
            base_tem_max_vals = base_tem_max['TEM_Max'].round(1)
            if self.fitting_method is not None:
                params_dict, max_values_dict, ks_values = self.calc_return_period_values(base_tem_max_vals, 'base_tem_max')
                result_dict.base_tem_max.return_result = edict()
                result_dict.base_tem_max.return_result['max_values'] = max_values_dict
                result_dict.base_tem_max.return_result['distribution_params'] = params_dict
                # result_dict.base_tem_max['p3_base'] = p3_base

        if 'base_tem_min' in self.element_name:
            # 先找最低温度月
            df_monthly = self.df_sequence['TEM_Min'].resample('1M', closed='right', label='right').mean().to_frame()
            time_idx = self.df_sequence.groupby([self.df_sequence.index.year])['TEM_Min'].idxmin().dt.strftime("%Y-%m").tolist()

            # 提取历年最高温度月，对应的月平均最高气温数据
            for i in range(len(time_idx)):
                data = df_monthly.loc[time_idx[i]]  # 每年最低气温的月份的所有日数据

                if i == 0:
                    base_tem_min = data
                else:
                    base_tem_min = pd.concat([base_tem_min, data], axis=0)

            base_tem_min = base_tem_min.round(1)
            base_tem_min.insert(loc=0, column='日期', value=base_tem_min.index.strftime("%Y-%m"))
            base_tem_min.reset_index(drop=True, inplace=True)

            year_vals = base_tem_max.dropna()
            if year_vals.shape[0] < 15:
                raise Exception('该参证站日数据存在缺测，转换后得到有效历年样本小于15个，不能进行后续重现期计算')

            base_tem_min_save = base_tem_min.copy()
            base_tem_min_save.columns = ['年月','基本最低气温(°C)']
            result_dict.base_tem_min = edict()
            result_dict.base_tem_min.data = base_tem_min_save.to_dict(orient='records')
            
            # 重现期计算
            base_tem_min_vals = base_tem_min['TEM_Min'].round(1)
            if self.fitting_method is not None:
                params_dict, max_values_dict, ks_values = self.calc_return_period_values(base_tem_min_vals, 'base_tem_min')
                result_dict.base_tem_min.return_result = edict()
                result_dict.base_tem_min.return_result['max_values'] = max_values_dict
                result_dict.base_tem_min.return_result['distribution_params'] = params_dict
                # result_dict.base_tem_min['p3_base'] = p3_base

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