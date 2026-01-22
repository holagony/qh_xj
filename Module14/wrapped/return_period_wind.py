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
from matplotlib import font_manager
font = font_manager.FontProperties(fname=cfg.FILES.FONT)
matplotlib.use('agg')


class calc_return_period_wind:

    def __init__(self, df_sequence, return_years, fitting_method, img_path, main_station):

        self.main_sequence = df_sequence
        self.return_years = return_years
        self.fitting_method = fitting_method
        self.img_path = img_path
        self.main_station = main_station
        if self.threshold == None:
            self.threshold = 0

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

        return params_dict, max_values_dict, ks_values

    def get_fig_ax(self):
        fig, ax = plt.subplots(figsize=(7, 5))
        return fig, ax
    
    def plot_result(self, fig, ax, data_in, sample_x, sample_y, y_axis_name, method_name, ks_val):
        '''
        画重现期拟合曲线图，x轴为概率坐标
        '''
        plt.rcParams['axes.unicode_minus'] = False
        new_y_axis_name = y_axis_name + ' (m/s)'

        # 定义图表上X轴的可见概率范围
        xlim_min, xlim_max = 0.1, 99.5

        # 1. 筛选在可见X范围内的理论曲线数据
        visible_mask_sample = (sample_x >= xlim_min) & (sample_x <= xlim_max)
        visible_sample_y = sample_y[visible_mask_sample]

        # 2. 筛选在可见X范围内的经验散点数据
        # 必须先对数据排序以计算正确的经验概率
        data_in_sorted = np.sort(data_in)[::-1]
        empi_prob = (np.arange(len(data_in_sorted)) + 1) / (len(data_in_sorted) + 1) * 100
        visible_mask_data = (empi_prob >= xlim_min) & (empi_prob <= xlim_max)
        visible_data_in = data_in_sorted[visible_mask_data]

        # 3. 合并所有可见数据并计算范围
        # 清理可能存在的NaN或Inf值
        visible_sample_y_clean = visible_sample_y[np.isfinite(visible_sample_y)]
        visible_data_in_clean = visible_data_in[np.isfinite(visible_data_in)]

        if len(visible_sample_y_clean) == 0 or len(visible_data_in_clean) == 0:
            # 如果没有有效数据，使用默认范围
            y_min, y_max = 0, 50
        else:
            combined_data = np.concatenate([visible_sample_y_clean, visible_data_in_clean])
            data_min = np.min(combined_data)
            data_max = np.max(combined_data)
            data_range = data_max - data_min
            
            # 设置边距
            if data_range <= 1e-10:
                margin = max(abs(data_min), abs(data_max), 1) * 0.1
            else:
                margin = data_range * 0.04
            
            y_min = max(0, data_min - margin)
            y_max = data_max + margin

            # 最终检查，确保范围值有效
            if not (np.isfinite(y_min) and np.isfinite(y_max)):
                y_min, y_max = 0, 50
        
        # --- 开始画图 ---
        ax.grid(True)
        ax.set_xlabel('KS-test: ' + str(ks_val.round(3)) + '   频率P(%)', fontproperties=font)
        ax.set_ylabel(new_y_axis_name, fontproperties=font)
        ax.set_xscale('prob')
        plt.xticks(size=7)

        # 应用计算好的坐标轴范围
        ax.set_xlim(xlim_min, xlim_max)
        ax.set_ylim(y_min, y_max)

        # 绘制完整数据，matplotlib会自动裁剪到xlim和ylim
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

        # Step0 结果字典创建/数据处理
        main_wind_seq = self.main_sequence['WIN_S_Max'].resample('1A', closed='right', label='right').max()  # 参证站的日风速数据转化为年数据
        main_wind_seq = main_wind_seq.round(1).dropna()
        year_vals_save = main_wind_seq.to_frame().copy()
        year_vals_save.insert(loc=0, column='year', value=year_vals_save.index.year)
        year_vals_save.columns = ['年份','最大风速(m/s)']
        year_vals_save.reset_index(drop=True, inplace=True)

        # 增加极大风速序列保存
        main_wind_seq_i = self.main_sequence['WIN_S_Inst_Max'].resample('1A', closed='right', label='right').max()  # 参证站的日风速数据转化为年数据
        main_wind_seq_i = main_wind_seq_i.round(1).dropna()
        year_vals_i_save = main_wind_seq_i.to_frame().copy()
        year_vals_i_save.insert(loc=0, column='year', value=year_vals_i_save.index.year)
        year_vals_i_save.columns = ['年份','极大风速(m/s)']
        year_vals_i_save.reset_index(drop=True, inplace=True)

        # 创建字典
        result_dict = edict()
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
            
            # 极大风速重现期
            params_dict_i, max_values_dict_i, ks_values_i = self.calc_return_period_values(main_wind_seq_i)
            result_dict.main_return_result['max_values_i'] = max_values_dict_i
            result_dict.main_return_result['distribution_params_i'] = params_dict_i

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
    post_daily_df = daily_data_processing(daily_df,'1994,2023')
    # post_daily_df = post_daily_df[post_daily_df.index.year>=1994]
    # post_daily_df = post_daily_df[post_daily_df.index.year<=2023]
    df_sequence = post_daily_df[post_daily_df['Station_Id_C']=='52853']
    sub_df = post_daily_df[post_daily_df['Station_Id_C']=='52866']
    return_years = [2,3,5,10,20,30,50,100]
    CI = [99,95]
    fitting_method = ['Gumbel', 'P3']
    img_path = r'D:\Project\3_项目\2_气候评估和气候可行性论证'
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

