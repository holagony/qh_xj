import numpy as np
import pandas as pd
import probscale
import matplotlib
import matplotlib.pyplot as plt
from scipy import stats
import metpy.calc as mcalc
from metpy.units import units
import Utils.distribution_fitting as fitting
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_processing import daily_data_processing
from Utils.pearson3 import pearson_type3
from Module01.wrapped.correlation_analysis import linear_regression
from matplotlib import font_manager
font = font_manager.FontProperties(fname=cfg.FILES.FONT)
matplotlib.use('agg')


class calc_return_period_wind:
    '''
    重现期最大风速及风压计算
    df_sequence: 输入日数据要素序列 dataframe
    relocation_year: 迁站订正年份 list
    height_revision_year: 参证站的高度订正年份 list
    measure_height: 参证站的高度订正年份对应的测风高度 list
    profile_index_main: 参证站的高度订正年份对应的风廓线指数 list
    return_years: 重现期年份 list
    CI: 置信水平 list
    fitting_method: 重现期计算方法 list
    element_name: 计算的要素中文名 str
    '''

    def __init__(self, df_sequence, relocation_year, height_revision_year, measure_height, profile_index_main, 
                 return_years, CI, fitting_method, img_path, from_database, sub_df, threshold, intercept):

        self.main_sequence = df_sequence
        self.relocation_year = relocation_year
        self.height_revision_year = height_revision_year
        self.measure_height = measure_height
        self.profile_index_main = profile_index_main
        self.return_years = return_years
        self.CI = CI
        self.fitting_method = fitting_method
        self.img_path = img_path
        self.from_database = from_database
        self.sub_df = sub_df
        self.intercept = intercept
        self.threshold = threshold

        if self.threshold == None:
            self.threshold = 0

    def wind_consistency_revision(self, data_in):
        '''
        迁站订正
        '''
        data_section = []
        mean_list = []

        for i, time in enumerate(self.relocation_year):
            if i == 0:
                data = data_in[data_in.index[0]:str(time - 1)]
                data_section.append(data)
                mean_val = data.mean()
                mean_list.append(mean_val)

            elif i > 0 and time != self.relocation_year[-1]:
                data = data_in[str(self.relocation_year[i - 1]):str(self.relocation_year[i] - 1)]
                data_section.append(data)
                mean_val = data.mean()
                mean_list.append(mean_val)

            if time == self.relocation_year[-1]:
                data = data_in[str(self.relocation_year[i - 1]):data_in.index[-1]]
                data_section.append(data)
                mean_val = data.mean()
                mean_list.append(mean_val)

        length = [len(section) for section in data_section]
        idx = length.index(max(length))
        weights = mean_list[idx] / np.array(mean_list)

        data_out = [(weights[j] * data_section[j]).round(3) for j in range(len(data_section))]
        data_out = pd.concat(data_out)
        data_out = data_out.round(3)

        return data_out

    def wind_height_revision(self, data_in):
        '''
        高度订正
        '''
        zipped_info = zip(self.height_revision_year, self.measure_height, self.profile_index_main)

        for info in zipped_info:
            year = str(info[0])
            if year in data_in.index:
                v_z = data_in[year]
                z = info[1]
                alpha = info[2]
                new_wind_s = v_z * (np.power((10 / z), alpha))
                data_in[year] = new_wind_s

        data_out = data_in.copy()
        data_out = data_out.round(3)

        return data_out
    
    def calc_correlation(self, main_df, sub_df):
        '''
        参证站和厂址站的相关性分析，以及厂址站重现期
        '''
        if self.from_database == 1:
            pass
        elif self.from_database == 0:
            sub_win_daily = sub_df['WIN_S_Max'].to_frame()
            sub_win_daily.columns = ['最大风速']
        
        sub_win_daily = sub_win_daily[sub_win_daily > self.threshold]
        
        # 参证站降水日数据
        main_win = main_df['WIN_S_Max'].to_frame()
        main_win = main_win[main_win > self.threshold]

        # 参证站数据和厂址站数据合并，并删除时间不对应的行
        concat_win = pd.concat([main_win, sub_win_daily], axis=1)
        concat_win = concat_win.dropna(how='any')

        if len(concat_win) < 200:  # 没有数据的情况
            params = np.nan
            data_points = np.nan
        else:
            # 计算线性回归参数
            w, b, r_square = linear_regression(concat_win['WIN_S_Max'], concat_win['最大风速'], intercept=self.intercept)
            w = round(w,3)
            b = round(b,3)
            r_square = round(r_square,5)
            params = [w, b, r_square]
            concat_win = concat_win.round(3)
            concat_win = concat_win.sample(n=200)
            data_points = concat_win.values.tolist()

        return params, data_points
    
    def calc_return_period_values(self, data_in):
        '''
        计算参证站不同重现期的数值
        '''
        params_dict = edict()  # 参数字典
        max_values_dict = edict()  # 重现期结果列表
        ks_values = edict()  # KS检验结果dict
        # p3_base = edict()

        if 'Gumbel' in self.fitting_method:
            loc, scale = fitting.estimate_parameters_gumbel(data_in, method='MOM')  # 根据现有数据计算该分布的参数
            max_values = fitting.get_max_values_gumbel(self.return_years, loc, scale)  # 根据参数和重现期列表计算对应的最大值
            sample_gumbel = stats.gumbel_r.rvs(loc, scale, 200)
            _, ks_result = fitting.kolmogorov_smirnov_test(sample_gumbel, data_in)  # KS检验

            params_dict['Gumbel'] = [loc, scale]
            max_values_dict['耿贝尔'] = max_values.round(3).tolist()
            ks_values['Gumbel_ks'] = ks_result

        if 'P3' in self.fitting_method:
            skew, loc, scale = fitting.estimate_parameters_pearson3(data_in, method='normal')
            max_values = fitting.get_max_values_pearson3(self.return_years, 0, skew, loc, scale)
            sample_p3 = stats.pearson3.rvs(skew, loc, scale, 200)
            _, ks_result = fitting.kolmogorov_smirnov_test(sample_p3, data_in)

            params_dict['P3'] = [skew, loc, scale]
            max_values_dict['皮尔逊Ⅲ型'] = max_values.round(3).tolist()
            ks_values['P3_ks'] = ks_result

            # 2023新增P3调参
            # p3_result = pearson_type3(element_name='Wind', 
            #                           data=data_in, 
            #                           rp=self.return_years,
            #                           img_path=None, 
            #                           mode=1, sv_ratio=0, ex_fitting=True, manual_cs_cv=None)
            # p3_base = p3_result

        return params_dict, max_values_dict, ks_values#, p3_base

    def calc_confidence_interval(self, data_in):
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
                max_values = fitting.get_max_values_gumbel(self.return_years, loc, scale)  # numpy array
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
                max_values = fitting.get_max_values_pearson3(self.return_years, 0, skew, loc, scale)
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
        index = pd.MultiIndex.from_product([self.return_years, interval], names=['重现期(年)', '置信水平(%)'])
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
        new_y_axis_name = y_axis_name + ' (m/s)'
        
        if y_axis_name == '最大风速':
            ax.set_ylim(5, 40)
        else:
            ax.set_ylim(15, 40)
            
        ax.grid(True)
        ax.set_xlabel('KS-test: ' + str(ks_val.round(5)) + '   频率P(%)', fontproperties=font)
        ax.set_ylabel(new_y_axis_name, fontproperties=font)
        ax.set_xscale('prob')
        plt.xticks(size=7)

        data_in = np.sort(data_in)[::-1]
        empi_prob = (np.arange(len(data_in)) + 1) / (len(data_in) + 1) * 100
        ax.set_xlim(0.1, 99.5)

        ax.scatter(empi_prob, data_in, marker='o', s=8, c='red', edgecolors='k', label='经验概率数据点')
        ax.plot(sample_x, sample_y, '--', lw=1, label=method_name + '分布拟合曲线')
        ax.legend(prop=font)

        save_path = self.img_path + '/{}_{}.png'.format(y_axis_name, method_name)
        plt.savefig(save_path, dpi=300, format='png', bbox_inches='tight')
        plt.cla()

        return save_path

    def run(self):
        '''
        forward流程
        '''
        fig, ax = self.get_fig_ax()

        # Step0 结果字典创建/数据处理
        main_wind_seq = self.main_sequence['WIN_S_Max'].resample('1A', closed='right', label='right').max()  # 参证站的日风速数据转化为年数据
        main_wind_seq = main_wind_seq.round(3).dropna()
        year_vals_save = main_wind_seq.to_frame().copy()
        year_vals_save.insert(loc=0, column='year', value=year_vals_save.index.year)
        year_vals_save.columns = ['年份','最大风速(m/s)']
        year_vals_save.reset_index(drop=True, inplace=True)

        # 增加极大风速序列保存
        main_wind_seq_i = self.main_sequence['WIN_S_Inst_Max'].resample('1A', closed='right', label='right').max()  # 参证站的日风速数据转化为年数据
        main_wind_seq_i = main_wind_seq_i.round(3).dropna()
        year_vals_i_save = main_wind_seq_i.to_frame().copy()
        year_vals_i_save.insert(loc=0, column='year', value=year_vals_i_save.index.year)
        year_vals_i_save.columns = ['年份','极大风速(m/s)']
        year_vals_i_save.reset_index(drop=True, inplace=True)

        # 创建字典
        result_dict = edict()
        result_dict.extra_station = edict()
        # result_dict.time_range = main_wind_seq.index.tolist()
        result_dict.return_years = self.return_years
        result_dict.wind_data = year_vals_save.to_dict(orient='records')
        result_dict.wind_data_i = year_vals_i_save.to_dict(orient='records')

        # Step1 对参证站风速进行迁站订正
        if self.relocation_year is not None:
            result_dict.consistency_revision = edict()
            result_dict.consistency_revision.before = main_wind_seq.values.tolist()  # 订正前结果存入
            main_wind_seq = self.wind_consistency_revision(main_wind_seq)
            result_dict.consistency_revision.after = main_wind_seq.values.tolist()  # 订正后结果存入

        # Step2 对参证站风速进行高度订正
        if self.height_revision_year is not None:
            result_dict.height_revision = edict()
            result_dict.height_revision.before = main_wind_seq.values.tolist()
            main_wind_seq = self.wind_height_revision(main_wind_seq)
            result_dict.height_revision.after = main_wind_seq.tolist()

        # Step3 参证站重现期计算
        if self.fitting_method is not None:
            result_dict.main_return_result = edict()
            params_dict, max_values_dict, ks_values = self.calc_return_period_values(main_wind_seq)
            result_dict.main_return_result['max_values'] = max_values_dict
            result_dict.main_return_result['distribution_params'] = params_dict
            # result_dict['p3_base'] = p3_base
            
            # 极大风速重现期
            params_dict_i, max_values_dict_i, ks_values_i = self.calc_return_period_values(main_wind_seq_i)
            result_dict.main_return_result['max_values_i'] = max_values_dict_i
            result_dict.main_return_result['distribution_params_i'] = params_dict_i
            
        # Step4 参证站重现期的置信区间计算
        if self.CI is not None and len(self.CI) != 0:
            ci_result = self.calc_confidence_interval(main_wind_seq)
            result_dict.confidence_interval = ci_result.to_dict(orient='records')

        # Step5 厂址站相关分析 重现期转换
        if self.sub_df is not None and len(self.sub_df) != 0:
            params, data_points = self.calc_correlation(self.main_sequence, self.sub_df)

            if params is np.nan:
                result_dict.extra_station['max_values'] = np.nan
                result_dict.extra_station['params'] = np.nan
                result_dict.extra_station['data'] = np.nan
                result_dict.extra_station['msg'] = '筛选后没有数据，无法计算厂址站相关系数和重现期结果'
            else:
                sub_max_vals = edict()
                for key in list(max_values_dict.keys()):
                    max_vals = np.array(max_values_dict[key]) * params[0] + params[1]
                    sub_max_vals[key] = max_vals.round(3).tolist()

                result_dict.extra_station['max_values'] = sub_max_vals
                result_dict.extra_station['params'] = params
                result_dict.extra_station['data'] = data_points

        # Step6 空气密度、阵风系数和重现期风压计算
        # 空气密度
        # tem = np.array(self.main_sequence['TEM_Avg']) * units('degC')
        # e0 = mcalc.saturation_vapor_pressure(tem).m / 100  # 饱和水气压 hpa
        # e = np.multiply((self.main_sequence['RHU_Avg'] / 100).values, e0)
        # rho_2 = 1.276e-3 * (self.main_sequence['PRS_Avg'].values - 0.378 * e) / (1 + 3.66e-3 * self.main_sequence['TEM_Avg'].values)  # 2m高度的空气密度
        # rho_10 = rho_2 * np.exp(-0.0001 * (10 - 2))  # 订正到10m高度的空气密度
        # rho_10 = np.nanmean(rho_10)
        
        # new 根据《风电场风能资源评估方法》中的公式进行计算
        prs_mean = self.main_sequence['PRS_Avg'].mean()
        tem_mean = self.main_sequence['TEM_Avg'].mean()
        rho_10 = prs_mean * 100/ ((tem_mean + 273.15)* 287)
        result_dict['空气密度'] = rho_10.round(3) # kg/m3

        # 阵风系数
        temp_wind = self.main_sequence[['WIN_S_2mi_Avg','WIN_S_Inst_Max']]
        temp_wind.dropna(how='any')
        gust = (temp_wind['WIN_S_Inst_Max'].mean()/temp_wind['WIN_S_2mi_Avg'].mean())
        gust = np.nanmean(gust)
        # gust = gust[~gust.isin([np.nan, np.inf, -np.inf])].round(2)
        result_dict['阵风系数'] = gust.round(3)

        # 计算风压
        w_pressure = edict()
        for key, value in max_values_dict.items():
            w_pressure[key] = [((val**2)*rho_10*(0.5)*1e-3).round(3) for val in max_values_dict[key]] # 基本风压 kN/m**2
        result_dict.main_return_result['wind_pressure'] = w_pressure

        # Step7 参证站重现期画图
        result_dict.img_save_path = edict()
        keys = list(params_dict.keys())
        x = np.linspace(0.01, 100, 1000)

        if 'Gumbel' in keys:
            y = fitting.get_max_values_gumbel(100 / x, params_dict['Gumbel'][0], params_dict['Gumbel'][1])
            save_path = self.plot_result(fig, ax, main_wind_seq, x, y, '最大风速', 'Gumbel', ks_values['Gumbel_ks'])
            result_dict.img_save_path['Gumbel_plot'] = save_path
            
            # 极大风速
            y = fitting.get_max_values_gumbel(100 / x, params_dict_i['Gumbel'][0], params_dict_i['Gumbel'][1])
            save_path = self.plot_result(fig, ax, main_wind_seq_i, x, y, '极大风速', 'Gumbel', ks_values_i['Gumbel_ks'])
            result_dict.img_save_path['Gumbel_plot_i'] = save_path

        if 'P3' in keys:
            y = fitting.get_max_values_pearson3(100 / x, 0, params_dict['P3'][0], params_dict['P3'][1], params_dict['P3'][2])
            save_path = self.plot_result(fig, ax, main_wind_seq, x, y, '最大风速', 'Pearson3', ks_values['P3_ks'])
            result_dict.img_save_path['P3_plot'] = save_path
            
            # 极大风速
            y = fitting.get_max_values_pearson3(100 / x, 0, params_dict_i['P3'][0], params_dict_i['P3'][1], params_dict_i['P3'][2])
            save_path = self.plot_result(fig, ax, main_wind_seq_i, x, y, '极大风速', 'Pearson3', ks_values_i['P3_ks'])
            result_dict.img_save_path['P3_plot_i'] = save_path

        # 关闭图框
        plt.cla()
        plt.close('all')
        
        return result_dict


if __name__ == '__main__':
    daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    post_daily_df = daily_data_processing(daily_df)
    # post_daily_df = post_daily_df[post_daily_df.index.year>=1994]
    # post_daily_df = post_daily_df[post_daily_df.index.year<=2023]
    df_sequence = post_daily_df[post_daily_df['Station_Id_C']=='52853']
    sub_df = post_daily_df[post_daily_df['Station_Id_C']=='52866']
    return_years = [2,3,5,10,20,30,50,100]
    CI = [99,95]
    fitting_method = ['Gumbel', 'P3']
    img_path = r'C:/Users/MJY/Desktop/result'
    from_database = 0
    threshold = 0
    intercept = True
    
    relocation_year = None
    height_revision_year = None
    measure_height = None
    profile_index_main = None

    if height_revision_year is not None:
        for i in range(len(height_revision_year)):
            h_year = height_revision_year[i].split(',')
            h_years = list(range(int(h_year[0]), int(h_year[1]) + 1))
            num_years = len(h_years)
            height = measure_height[i]
            heights = [height] * num_years
            index = profile_index_main[i]
            indexes = [index] * num_years

            if i == 0:
                new_years = h_years
                new_height = heights
                new_index = indexes
            else:
                new_years = new_years + h_years
                new_height = new_height + heights
                new_index = new_index + indexes

        height_revision_year = new_years
        measure_height = new_height
        profile_index_main = new_index
        
    wind = calc_return_period_wind(df_sequence, relocation_year, height_revision_year, measure_height, profile_index_main, 
                                   return_years, CI, fitting_method, img_path, from_database, sub_df, threshold, intercept)
    wind_result = wind.run()

