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
from matplotlib import font_manager

font = font_manager.FontProperties(fname=cfg.FILES.FONT)
matplotlib.use('agg')


class calc_return_period_frs:

    def __init__(self, df_sequence, return_years, fitting_method, img_path, main_station):
        self.df_sequence = df_sequence
        self.return_years = return_years  # 重现期列表 list
        self.fitting_method = fitting_method  # 拟合方法列表 list
        self.img_path = img_path
        self.main_station = main_station

    def calc_return_period_values(self, data_in, periods):
        '''
        计算参证站不同重现期的数值
        注意：这里的data_in应该是已经过滤掉0值的数据
        '''
        params_dict = edict()  # 参数字典
        max_values_dict = edict()  # 重现期结果列表
        ks_values = edict()  # KS检验结果dict

        # 确保过滤掉0值和缺失值
        data_filtered = data_in[data_in > 0]
        data_filtered = data_filtered.dropna()

        if len(data_filtered) < 5:
            raise Exception(f'过滤0值后的有效积雪深度数据不足5个样本（当前{len(data_filtered)}个），无法进行重现期计算')

        if 'Gumbel' in self.fitting_method:
            loc, scale = fitting.estimate_parameters_gumbel(data_filtered, method='MOM')  # 根据现有数据计算该分布的参数
            max_values = fitting.get_max_values_gumbel(periods, loc, scale)  # 根据参数和重现期列表计算对应的最大值
            sample_gumbel = stats.gumbel_r.rvs(loc, scale, 200)
            _, ks_result = fitting.kolmogorov_smirnov_test(sample_gumbel, data_filtered)  # KS检验

            params_dict['Gumbel'] = [loc, scale]
            max_values_dict['Gumbel_max_vals'] = max_values.round(1).tolist()
            ks_values['Gumbel_ks'] = ks_result

        if 'P3' in self.fitting_method:
            skew, loc, scale = fitting.estimate_parameters_pearson3(data_filtered, method='normal')
            max_values = fitting.get_max_values_pearson3(periods, 0, skew, loc, scale)
            sample_p3 = stats.pearson3.rvs(skew, loc, scale, 200)
            _, ks_result = fitting.kolmogorov_smirnov_test(sample_p3, data_filtered)

            params_dict['P3'] = [skew, loc, scale]
            max_values_dict['P3_max_vals'] = max_values.round(1).tolist()
            ks_values['P3_ks'] = ks_result

        return params_dict, max_values_dict, ks_values  #, p3_base

    def get_fig_ax(self):
        fig, ax = plt.subplots(figsize=(7, 5))
        return fig, ax

    def plot_result(self, fig, ax, data_in, sample_x, sample_y, y_axis_name, method_name, ks_val):
        '''
        画重现期拟合曲线图，x轴为概率坐标
        注意：这里的data_in应该是已经过滤掉0值的数据
        '''
        plt.rcParams['axes.unicode_minus'] = False
        new_y_axis_name = y_axis_name + ' (cm)'

        # 确保过滤掉0值和缺失值
        data_filtered = data_in[data_in > 0]
        data_filtered = data_filtered.dropna()

        # 定义图表上X轴的可见概率范围
        xlim_min, xlim_max = 0.1, 99.5

        # --- 根据可见范围计算Y轴的最佳范围 ---

        # 1. 筛选在可见X范围内的理论曲线数据
        visible_mask_sample = (sample_x >= xlim_min) & (sample_x <= xlim_max)
        visible_sample_y = sample_y[visible_mask_sample]

        # 2. 筛选在可见X范围内的经验散点数据
        data_in_sorted = np.sort(data_filtered)[::-1]
        empi_prob = (np.arange(len(data_in_sorted)) + 1) / (len(data_in_sorted) + 1) * 100
        visible_mask_data = (empi_prob >= xlim_min) & (empi_prob <= xlim_max)
        visible_data_in = data_in_sorted[visible_mask_data]

        # 3. 合并所有可见数据并计算范围
        visible_sample_y_clean = visible_sample_y[np.isfinite(visible_sample_y)]
        visible_data_in_clean = visible_data_in[np.isfinite(visible_data_in)]

        if len(visible_sample_y_clean) == 0 or len(visible_data_in_clean) == 0:
            y_min, y_max = 0, 50  # 默认范围
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
                y_min, y_max = 0, 50

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

        # Step0 结果字典创建/数据处理
        result_dict = edict()
        result_dict.return_years = self.return_years

        # 将两列最大值作为新列 FRX_Depth_Max，再按年取最大
        self.df_sequence['FRX_Depth_Max'] = self.df_sequence[['FRS_1st_Bot', 'FRS_2nd_Bot']].max(axis=1).round(1)
        frs_data = self.df_sequence['FRX_Depth_Max'].resample('1A').max().dropna()

        if frs_data.shape[0] < 10:
            raise Exception('该参证站日数据存在缺测，转换后得到有效历年样本小于10个，不能进行后续重现期计算')

        # 保存原始数据（包含0值）用于展示
        frs_data_save = frs_data.to_frame().copy()
        frs_data_save.insert(loc=0, column='year', value=frs_data_save.index.year)
        frs_data_save.columns = ['年份', '最大冻土深度(cm)']
        frs_data_save.reset_index(drop=True, inplace=True)
        result_dict.data = frs_data_save.to_dict(orient='records')

        # 过滤掉0值，用于重现期计算
        frs_data_filtered = frs_data[frs_data > 0]
        if len(frs_data_filtered) < 5:
            raise Exception(f'过滤0值后的有效冻土深度数据不足5个样本（当前{len(frs_data_filtered)}个），无法进行重现期计算')

        # Step1 频率转换
        convert_periods = self.return_years

        # Step3 重现期计算（使用过滤后的数据）
        if self.fitting_method is not None:
            result_dict.main_return_result = edict()
            params_dict, max_values_dict, ks_values = self.calc_return_period_values(frs_data_filtered, convert_periods)
            result_dict.main_return_result['max_values'] = max_values_dict
            result_dict.main_return_result['distribution_params'] = params_dict

        # Step5 重现期画图（使用过滤后的数据）
        result_dict.img_save_path = edict()
        keys = list(params_dict.keys())
        x = np.linspace(0.01, 100, 1000)  # 对应图片频率 (%) 从左到右，1/(x/100)转化为年

        if 'Gumbel' in keys:
            y = fitting.get_max_values_gumbel(1 / (x / 100), params_dict['Gumbel'][0], params_dict['Gumbel'][1])
            save_path = self.plot_result(fig, ax, frs_data_filtered, x, y, '冻土深度', 'Gumbel', ks_values['Gumbel_ks'])
            result_dict.img_save_path['Gumbel_plot'] = save_path

        if 'P3' in keys:
            y = fitting.get_max_values_pearson3(1 / (x / 100), 0, params_dict['P3'][0], params_dict['P3'][1], params_dict['P3'][2])
            save_path = self.plot_result(fig, ax, frs_data_filtered, x, y, '冻土深度', 'Pearson3', ks_values['P3_ks'])
            result_dict.img_save_path['P3_plot'] = save_path

        # 关闭图框
        plt.cla()
        plt.close('all')

        return result_dict


if __name__ == '__main__':
    monthly_df = pd.read_csv(cfg.FILES.QH_DATA_MONTH, low_memory=False)
    monthly_df = monthly_df[['Station_Name', 'Station_Id_C', 'Lon', 'Lat', 'Datetime', 'Snow_Depth_Max']]
    post_monthly_df = monthly_data_processing(monthly_df, '1990,2023')
    post_monthly_df = post_monthly_df[post_monthly_df['Station_Id_C'] == '56067']
    post_monthly_df = post_monthly_df[post_monthly_df.index.year >= 1990]
    post_monthly_df = post_monthly_df[post_monthly_df.index.year <= 2023]
    df_sequence = post_monthly_df.resample('1A').max()

    # path = r'C:/Users/MJY/Desktop/Ckextreme(1).xlsx'
    # df_sequence = pd.read_excel(path)
    # df_sequence.columns = ['Datetime','TEM_Max','TEM_Min','PRE_Time_2020','WIN_S_Max','Snow_Depth_Max','WIN_S_Inst_Max']
    # df_sequence['Datetime'] = df_sequence['Datetime'].map(str)
    # df_sequence['Datetime'] = pd.to_datetime(df_sequence['Datetime'],format='%Y')
    # df_sequence.set_index('Datetime',inplace=True)

    return_years = [2, 3, 5, 10, 20, 30, 50, 100]
    CI = None
    fitting_method = ['Gumbel', 'P3']
    img_path = r'D:\Project'
    frs = calc_return_period_frs(df_sequence, return_years, fitting_method, img_path, '56067')
    frs_result = frs.run()
