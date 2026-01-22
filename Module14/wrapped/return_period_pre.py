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
from matplotlib import font_manager
font = font_manager.FontProperties(fname=cfg.FILES.FONT)
matplotlib.use('agg')


class calc_return_period_pre:
    '''
    重现期降水以及降水历时重现期计算
    '''
    def __init__(self, df_sequence, return_years, fitting_method, img_path):

        self.df_sequence = df_sequence
        self.return_years = return_years
        self.fitting_method = fitting_method
        self.img_path = img_path

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

        return params_dict, max_values_dict, ks_values#, p3_base

    def get_fig_ax(self):
        fig, ax = plt.subplots(figsize=(7, 5))
        return fig, ax
    
    def plot_result(self, fig, ax, data_in, sample_x, sample_y, y_axis_name, method_name, ks_val):
        '''
        画重现期拟合曲线图，x轴为概率坐标
        '''
        plt.rcParams['axes.unicode_minus'] = False
        
        if y_axis_name == '日最大降水量':
            new_y_axis_name = y_axis_name + ' (mm)'
        else:
            new_y_axis_name = y_axis_name + ' (mm/h)'

        # 定义图表上X轴的可见概率范围
        xlim_min, xlim_max = 0.1, 99.5

        # --- 根据可见范围计算Y轴的最佳范围 ---
        visible_mask_sample = (sample_x >= xlim_min) & (sample_x <= xlim_max)
        visible_sample_y = sample_y[visible_mask_sample]

        data_in_sorted = np.sort(data_in)[::-1]
        empi_prob = (np.arange(len(data_in_sorted)) + 1) / (len(data_in_sorted) + 1) * 100
        visible_mask_data = (empi_prob >= xlim_min) & (empi_prob <= xlim_max)
        visible_data_in = data_in_sorted[visible_mask_data]

        visible_sample_y_clean = visible_sample_y[np.isfinite(visible_sample_y)]
        visible_data_in_clean = visible_data_in[np.isfinite(visible_data_in)]

        if len(visible_sample_y_clean) == 0 or len(visible_data_in_clean) == 0:
            y_min, y_max = 0, 100 # 默认范围
        else:
            combined_data = np.concatenate([visible_sample_y_clean, visible_data_in_clean])
            data_min = np.min(combined_data)
            data_max = np.max(combined_data)
            data_range = data_max - data_min
            
            if data_range <= 1e-10:
                margin = max(abs(data_min), abs(data_max), 1) * 0.1
            else:
                margin = data_range * 0.04
            
            y_min = max(0, data_min - margin)
            y_max = data_max + margin

            if not (np.isfinite(y_min) and np.isfinite(y_max)):
                y_min, y_max = 0, 100
        
        # --- 开始画图 ---
        ax.grid(True)
        ax.set_xlabel('KS-test: ' + str(ks_val.round(3)) + '   频率P(%)', fontproperties=font)
        ax.set_ylabel(new_y_axis_name, fontproperties=font)
        ax.set_xscale('prob')
        plt.xticks(size=7)

        ax.set_xlim(xlim_min, xlim_max)
        ax.set_ylim(y_min, y_max)

        ax.scatter(empi_prob, data_in_sorted, marker='o', s=8, c='red', edgecolors='k', label='经验概率数据点')
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
