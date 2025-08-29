import numpy as np
import pandas as pd
import probscale
import matplotlib
import matplotlib.pyplot as plt
from scipy import stats
import Utils.distribution_fitting as fitting
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_processing import hourly_data_processing, daily_data_processing
from Module01.wrapped.correlation_analysis import linear_regression
from Utils.pearson3 import pearson_type3

from matplotlib import font_manager
font = font_manager.FontProperties(fname=cfg.FILES.FONT)
matplotlib.use('agg')


class calc_return_period_pre:
    '''
    重现期降水以及降水历时重现期计算
    '''
    def __init__(self, df_sequence, return_years, CI, fitting_method, img_path, sub_df, from_database, threshold, intercept):

        self.df_sequence = df_sequence
        self.return_years = return_years
        self.CI = CI
        self.fitting_method = fitting_method
        self.img_path = img_path
        self.sub_df = sub_df
        self.from_database = from_database
        self.intercept = intercept
        self.threshold = threshold

        if self.threshold == None:
            self.threshold = 0

    def calc_correlation(self, main_df, sub_df):
        '''
        参证站和厂址站的相关性分析，以及厂址站重现期
        '''
        if self.from_database == 1:
            sub_df.columns = ['降水']
            sub_pre_daily = sub_df['降水'].resample('1D', closed='right', label='right').sum().to_frame()
        elif self.from_database == 0:
            sub_pre_daily = sub_df['PRE_Time_2020'].to_frame()
            sub_pre_daily.columns = ['降水']
        
        sub_pre_daily = sub_pre_daily[sub_pre_daily > self.threshold]
        
        # 参证站降水日数据
        main_pre = main_df['PRE_Time_2020'].to_frame()
        main_pre = main_pre[main_pre > self.threshold]

        # 参证站数据和厂址站数据合并，并删除时间不对应的行
        concat_pre = pd.concat([main_pre, sub_pre_daily], axis=1)
        concat_pre = concat_pre.dropna(how='any')
        # concat_pre = concat_pre.loc[~(concat_pre==0).all(axis=1)] # 删除全是0的行

        if len(concat_pre) < 200:  # 没有数据的情况
            params = np.nan
            data_points = np.nan
        else:
            # 计算线性回归参数
            w, b, r_square = linear_regression(concat_pre['PRE_Time_2020'], concat_pre['降水'], intercept=self.intercept)
            w = round(w,3)
            b = round(b,3)
            r_square = round(r_square,5)
            params = [w, b, r_square]
            
            concat_pre = concat_pre.round(1)
            concat_pre = concat_pre.sample(n=200)
            data_points = concat_pre.values.tolist()

        return params, data_points

    def calc_return_period_values(self, data_in):
        '''
        计算不同重现期的最大数值
        '''
        params_dict = edict()  # 参数字典
        max_values_dict = edict()  # 重现期结果列表
        ks_values = edict()  # KS检验结果dict

        if 'Gumbel' in self.fitting_method:
            loc, scale = fitting.estimate_parameters_gumbel(data_in, method='MOM')  # 根据现有数据计算该分布的参数
            max_values = fitting.get_max_values_gumbel(self.return_years, loc, scale)
            sample_gumbel = stats.gumbel_r.rvs(loc, scale, 200)
            _, ks_result = fitting.kolmogorov_smirnov_test(sample_gumbel, data_in)  # KS检验

            params_dict['Gumbel'] = [loc, scale]
            max_values_dict['耿贝尔'] = max_values.round(1).tolist()
            ks_values['Gumbel_ks'] = ks_result

        if 'P3' in self.fitting_method:
            skew, loc, scale = fitting.estimate_parameters_pearson3(data_in, method='normal')
            max_values = fitting.get_max_values_pearson3(self.return_years, 0, skew, loc, scale)
            sample_p3 = stats.pearson3.rvs(skew, loc, scale, 200)
            _, ks_result = fitting.kolmogorov_smirnov_test(sample_p3, data_in)

            params_dict['P3'] = [skew, loc, scale]
            max_values_dict['皮尔逊Ⅲ型'] = max_values.round(1).tolist()
            ks_values['P3_ks'] = ks_result

            # 2023新增P3调参
            # p3_result = pearson_type3(element_name='Precipitation', 
            #                           data=data_in, 
            #                           rp=self.return_years,
            #                           img_path=self.img_path, 
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
        ci_result = ci_result.round(1)

        # ci_result转成dataframe
        # number = [str(year) + '年' for year in self.return_years]
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

        new_y_axis_name = y_axis_name + ' (mm)'
        data_in = np.sort(data_in)[::-1]
        ax.set_ylim(0, 120)

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

        if self.df_sequence is not None:
            max_pre_seq = self.df_sequence['PRE_Time_2020'].resample('1A', closed='right', label='right').max()
            max_pre_seq = max_pre_seq.round(1)

            year_vals = max_pre_seq.dropna()
            if year_vals.shape[0] < 15:
                raise Exception('该参证站日数据存在缺测，转换后得到有效历年样本小于15个，不能进行后续重现期计算')

            pre_df = max_pre_seq.to_frame()
            pre_df.insert(loc=0, column='year', value=pre_df.index.year)
            pre_df.columns = ['年份', '最大日降水量(mm)']
            pre_df.reset_index(drop=True, inplace=True)

            result_dict.PRE_Max_Day = edict()
            result_dict.PRE_Max_Day.data = pre_df.to_dict(orient='records')

            # 重现期计算
            params_dict, max_values_dict, ks_values = self.calc_return_period_values(max_pre_seq)
            result_dict.PRE_Max_Day.return_result = edict()
            result_dict.PRE_Max_Day.return_result['max_values'] = max_values_dict
            result_dict.PRE_Max_Day.return_result['distribution_params'] = params_dict
            # result_dict.PRE_Max_Day['p3_base'] = p3_base

            # 置信区间
            if self.CI is not None and len(self.CI) != 0:
                ci_result = self.calc_confidence_interval(max_pre_seq)
                result_dict.PRE_Max_Day.confidence_interval = ci_result.to_dict(orient='records')

            # 厂址站相关分析 重现期转换
            if self.sub_df is not None and len(self.sub_df) != 0:
                result_dict.extra_station = edict()
                params, data_points = self.calc_correlation(self.df_sequence, self.sub_df)

                if params is np.nan:
                    result_dict.extra_station['max_values'] = np.nan
                    result_dict.extra_station['params'] = np.nan
                    result_dict.extra_station['data'] = np.nan
                    result_dict.extra_station['msg'] = '筛选后没有数据，无法计算厂址站相关系数和重现期结果'

                else:
                    sub_max_vals = edict()
                    for key in list(max_values_dict.keys()):
                        max_vals = np.array(max_values_dict[key]) * params[0] + params[1]
                        sub_max_vals[key] = max_vals.round(1).tolist()

                    result_dict.extra_station['max_values'] = sub_max_vals
                    result_dict.extra_station['params'] = params
                    result_dict.extra_station['data'] = data_points

            # 画图
            result_dict.PRE_Max_Day.img_save_path = edict()
            keys = list(params_dict.keys())
            x = np.linspace(0.01, 100, 1000)

            if 'Gumbel' in keys:
                y = fitting.get_max_values_gumbel(100 / x, params_dict['Gumbel'][0], params_dict['Gumbel'][1])
                save_path = self.plot_result(fig, ax, max_pre_seq, x, y, '最大日降水量', 'Gumbel', ks_values['Gumbel_ks'])
                result_dict.PRE_Max_Day.img_save_path['Gumbel_plot'] = save_path

            if 'P3' in keys:
                y = fitting.get_max_values_pearson3(100 / x, 0, params_dict['P3'][0], params_dict['P3'][1], params_dict['P3'][2])
                save_path = self.plot_result(fig, ax, max_pre_seq, x, y, '最大日降水量', 'Pearson3', ks_values['P3_ks'])
                result_dict.PRE_Max_Day.img_save_path['P3_plot'] = save_path

            # 关闭图框
            plt.cla()
            plt.close('all')

        return result_dict


if __name__ == '__main__':
    daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    post_daily_df = daily_data_processing(daily_df)
    post_daily_df = post_daily_df[post_daily_df.index.year>=1994]
    post_daily_df = post_daily_df[post_daily_df.index.year<=2023]
    df_sequence = post_daily_df[post_daily_df['Station_Id_C']=='52853']
    sub_df = post_daily_df[post_daily_df['Station_Id_C']=='52866']
    
    
    
    
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
    img_path = r'C:/Users/MJY/Desktop/result'
    from_database = 0
    threshold = 0
    intercept = True
    
    pre = calc_return_period_pre(df_sequence=df_sequence, 
                                 return_years=return_years, 
                                 CI=CI, 
                                 fitting_method=fitting_method, 
                                 img_path=img_path, 
                                 sub_df=sub_df,
                                 from_database=from_database,
                                 threshold=threshold, 
                                 intercept=intercept)
    pre_result = pre.run()
