import pickle
import simplejson
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.pyplot import MultipleLocator
from Utils.ordered_easydict import OrderedEasyDict as edict
import matplotlib

matplotlib.use('agg')


def rain_peak(step1_result, start_year, end_year):
    '''
    计算雨峰系数
    输出：
    peak 综合雨峰系数
    all_peak 不同历时的平均雨峰系数和综合雨峰系数
    all_r 历年不同历时最大的降水量对应的雨峰系数
    res 历年每场雨按X分钟滑动平均的起始时间和雨峰系数
    '''
    data_dict = step1_result
    all_r = []
    res = dict()
    for i in range(start_year, end_year + 1):
        rain_list = data_dict[str(i)]
        yearly_r = []
        res[str(i)] = dict()

        for time in [30, 60, 90, 120, 150, 180]:
            if time <= 120:
                rain_inr = rain_list['120min_interval']['each_rain']
            else:
                rain_inr = rain_list[str(time) + 'min_interval']['each_rain']

            # 每年每场雨取最大x雨量的信息
            rain_df = pd.DataFrame(columns=['start_' + str(time), 'end_' + str(time), 'sum_' + str(time), 'idx', 'year', 'rain_peak'])

            if len(rain_inr) != 0:
                for num, rain in enumerate(rain_inr):
                    if len(rain) > time:
                        max_sum = rain['pre'].rolling(window=time).sum().max()  # 最大降水量之和
                        max_sum_idx = rain['pre'].rolling(window=time).sum().idxmax()
                        max_seq = rain.loc[max_sum_idx - time + 1:max_sum_idx]

                        sequence = max_seq['pre'].values
                        idx = np.argwhere(sequence == sequence.max())
                        rain_peak = ((idx[0][0] + 1) / len(sequence))
                        rain_peak = round(rain_peak, 3)

                        start_time = max_seq.iloc[0, -1]
                        end_time = max_seq.iloc[-1, -1]
                        values = [start_time, end_time, max_sum, num, i, rain_peak]
                    else:
                        max_sum = rain['pre'].sum()
                        sequence = rain['pre'].values
                        idx = np.argwhere(sequence == sequence.max())
                        rain_peak = ((idx[0][0] + 1) / len(sequence))
                        rain_peak = round(rain_peak, 3)

                        start_time = rain.iloc[0, -1]
                        end_time = rain.iloc[-1, -1]
                        values = [start_time, end_time, max_sum, num, i, rain_peak]

                    rain_df.loc[len(rain_df)] = values
                    res[str(i)][str(time)] = rain_df

                selceted_r = rain_df.loc[rain_df['sum_' + str(time)] == rain_df['sum_' + str(time)].max(), 'rain_peak']
                selceted_r = selceted_r.to_numpy()[0]
                yearly_r.append(selceted_r)

            else:
                yearly_r.append(np.nan)

        all_r.append(yearly_r)

    all_r = np.array(all_r)
    all_r = pd.DataFrame(all_r, columns=['30min', '60min', '90min', '120min', '150min', '180min'])
    all_r.index = range(start_year, end_year + 1)
    all_r.index = all_r.index.astype(str)

    # all_r.dropna(how='all',axis=0,inplace=True)
    all_r1 = np.mean(all_r, axis=0).round(3)

    peak = (30 * all_r1[0] + 60 * all_r1[1] + 90 * all_r1[2] + 120 * all_r1[3] + 150 * all_r1[4] + 180 * all_r1[5]) / 630
    peak = round(peak, 3)

    # 增加各历时雨峰系数
    all_peak = pd.DataFrame(all_r1).T
    all_peak.columns = ['30min', '60min', '90min', '120min', '150min', '180min']
    all_peak['综合雨峰系数'] = peak
    all_peak = all_peak.round(3)

    return peak, all_peak, all_r, res


def chicago(year, time, rain_peak, A, b, C, n):
    '''
    芝加哥雨型计算
    '''
    P = year
    r = rain_peak
    tp = round(time * r, 0)  # 雨峰时间
    td = time

    a = A * (1 + C * np.log10(P))
    accum = []

    for t in range(1, td + 1, 1):

        if t <= tp:
            accum_pre = a * (((tp - t) / r) * (1 - n) + b) / np.power((tp - t) / r + b, 1 + n)
        elif t > tp:
            accum_pre = a * (((t - tp) / (1 - r)) * (1 - n) + b) / np.power((t - tp) / (1 - r) + b, 1 + n)

        accum.append(accum_pre)

    chicago_values = pd.DataFrame(accum, columns=['瞬时雨量'])

    return chicago_values


def step5_run_chicago(pickle_path, chicago_times, param_A, param_b, param_C, param_n, save_path, start_year=None, end_year=None):
    '''
    读取step1的pickle，输出每年一场最大N分钟历时数据及对应的雨峰，
    计算综合雨峰系数，读取暴雨公式参数计算芝加哥雨型
    
    pickle_path step1输出的pickle文件路径
    start_year 设定起始时间
    end_year 设定终止时间
    chicago_times 设定芝加哥雨型时长list: [60,90,120,150,180]
    param_A/param_b/param_C/param_n 暴雨公式参数
    '''
    with open(pickle_path, 'rb') as f:
        data_dict = pickle.load(f)

    dict_years = list(data_dict.keys())
    dict_years = np.array([int(years) for years in dict_years])
    if start_year == None:
        start_year = dict_years.min()

    if end_year == None:
        end_year = dict_years.max()

    peak, all_peak, all_r, res = rain_peak(data_dict, start_year, end_year)
    all_r.dropna(inplace=True, axis=0)
    all_r.insert(loc=0, column='年份', value=all_r.index)
    all_r.reset_index(inplace=True, drop=True)
    # peak = 0.365

    # 创建结果字典+画图保存
    plt.rcParams['font.sans-serif'] = 'SimHei'
    plt.rcParams['axes.unicode_minus'] = False

    result = edict()
    # result['历年不同历时雨峰系数'] = all_r.to_dict(orient='records')
    result['不同历时平均雨峰系数'] = all_peak.to_dict(orient='records')
    result['综合雨峰系数'] = peak
    result['img_save_path'] = edict()
    result['rain_type'] = edict()

    for time in chicago_times:
        tmp = []
        for year in [2, 3, 5, 10, 20, 30, 50, 100]:
            chicago_values = chicago(year, time, peak, param_A, param_b, param_C, param_n)
            chicago_values = chicago_values['瞬时雨量'].to_frame().round(4).reset_index(drop=True)
            tmp.append(chicago_values)

        data = pd.concat(tmp, axis=1)
        data.columns = ['2a', '3a', '5a', '10a', '20a', '30a', '50a', '100a']
        data = data.round(4)
        data.insert(loc=0, column='分钟', value=data.index+1)
        result['rain_type'][str(time) + 'min' + '雨型'] = data.to_dict(orient='records')

        # plot
        fig = plt.figure(figsize=(20, 8))
        ax = fig.add_subplot(111)

        for i in [2, 3, 5, 10, 20, 30, 50, 100]:
            xs = data.index
            ys = data[str(i) + 'a']
            ax.plot(xs, ys, label='P=' + str(i) + 'a')

        ax.set_xlim(0, time)
        ax.xaxis.set_major_locator(MultipleLocator(5))
        ax.yaxis.set_major_locator(MultipleLocator(0.5))
        ax.xaxis.set_tick_params(labelsize=16)
        ax.yaxis.set_tick_params(labelsize=16)
        ax.set_xlabel('降水历时(min)', fontsize=18)
        ax.set_ylabel('降雨强度(mm/min)', fontsize=18)
        ax.legend()
        plt.grid()

        save_path1 = save_path + '/chicago_{}min.png'.format(str(time))
        plt.savefig(save_path1, dpi=300, bbox_inches='tight')
        result['img_save_path'][str(time) + 'min'+ '雨型'] = save_path1
        plt.cla()

    plt.close('all')

    return result


if __name__ == '__main__':
    pickle_path = r'C:/Users/mjynj/Desktop/result/step1_result.txt'
    chicago_times = [60, 90, 120, 150, 180]  # 创建的芝加哥雨型时间
    param_A = 7.589
    param_b = 11.835
    param_C = 2.279
    param_n = 1.005
    save_path = r'C:/Users/mjynj/Desktop/result'
    result_dict = step5_run_chicago(pickle_path, chicago_times, param_A, param_b, param_C, param_n, save_path)
