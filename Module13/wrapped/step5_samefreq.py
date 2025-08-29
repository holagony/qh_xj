import os
import glob
import json
import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.pyplot import MultipleLocator
from datetime import timedelta
from tqdm import tqdm
from Utils.ordered_easydict import OrderedEasyDict as edict
import matplotlib
matplotlib.use('agg')

def get_max1440(pickle_path, file_path, start_year=None, end_year=None):
    '''
    提取10场最大1440历时雨对应的完整场雨 逐5分钟
    输出：
    total_max10 10场最大的1440场雨信息汇总表
    rain1440_list 10场最大的1440场雨详情(逐5分钟)
    '''
    try:
        with open(pickle_path, 'rb') as f:
            data_dict = pickle.load(f)

    except Exception:
        raise Exception('第一步划分场雨生成的pickle文件没有读取成功，请检查文件输出路径')

    dict_years = list(data_dict.keys())
    dict_years = np.array([int(years) for years in dict_years])
    if start_year == None:
        start_year = dict_years.min()

    if end_year == None:
        end_year = dict_years.max()

    rain_list_yearly = {}  # 每年所有划分的场雨
    for i in range(start_year, end_year + 1):
        rain_list = data_dict[str(i)]
        rain_inr1440 = rain_list['1440min_interval']['each_rain']  # 这一年1440min间隔场雨
        rain_list_yearly[i] = rain_inr1440
        rain_df = pd.DataFrame(columns=['场雨开始时间', '场雨结束时间', '总降雨历时', '总降雨量', '最大1440雨开始时间', '最大1440雨结束时间', '最大1440雨量', 'idx', 'year'])

        for num, rain in enumerate(rain_inr1440):
            if len(rain) > 1440:
                # 场雨开始时间/场雨结束时间/总降雨历时/总降雨量
                start_time = rain.iloc[0, -1]
                end_time = rain.iloc[-1, -1]
                delta = end_time - start_time
                all_minutes = delta.total_seconds() / 60 + 1
                all_sum = rain['pre'].sum()

                # 最大1440雨开始时间/最大1440雨结束时间
                max_sum_idx = rain['pre'].rolling(window=1440).sum().idxmax()
                max_seq = rain.loc[max_sum_idx - 1440 + 1:max_sum_idx]
                start_time1440 = max_seq.iloc[0, -1]
                end_time1440 = max_seq.iloc[-1, -1]

                # 最大1440雨量
                max1440_sum = rain['pre'].rolling(window=1440).sum().max()  # 最大降水量之和
                values = [start_time, end_time, all_minutes, all_sum, start_time1440, end_time1440, max1440_sum, num, i]
            else:
                start_time = rain.iloc[0, -1]
                end_time = rain.iloc[-1, -1]
                delta = end_time - start_time
                all_minutes = delta.total_seconds() / 60 + 1
                all_sum = rain['pre'].sum()

                values = [start_time, end_time, all_minutes, all_sum, start_time, end_time, all_sum, num, i]

            rain_df.loc[len(rain_df)] = values

        if i == start_year:
            total_1440 = rain_df

        else:
            total_1440 = pd.concat([total_1440, rain_df], axis=0)

    # 10场最大1440雨记录
    total_max10 = total_1440[total_1440['最大1440雨量'].isin(total_1440['最大1440雨量'].nlargest(20))].sort_values('最大1440雨量', ascending=[False]).reset_index(drop=True)
    # total_max10.to_csv(file_path+'/10场最大1440历时雨汇总表.csv',encoding='utf_8_sig')

    rain1440_list = []
    for i in range(total_max10.shape[0]):
        year = total_max10.iloc[i, -1]
        idx = total_max10.iloc[i, -2]
        rain = rain_list_yearly[year][idx].reset_index(drop=True)

        # update method1 变成隔5min
        rain = rain.assign(pre=rain.groupby(rain.index // 5)['pre'].transform('sum'))  # sum
        idx_5min = list(range(0, rain.shape[0], 5))  # 获取每5min里面，第一个时刻的idx
        rain = rain.loc[idx_5min, :]  # 提取数据
        rain['time'] = rain['time'] + timedelta(minutes=4)  # time列每行加4分钟

        rain.to_csv(file_path + '/第{}场1440对应的完整场雨.csv'.format(i + 1), encoding='utf_8_sig')  # 10场最大1440对应的完整降水过程
        rain1440_list.append(rain)

    return total_max10, rain1440_list


def calc_same_frequency(file_path, param_A, param_b, param_C, param_n):
    '''
    同频率雨型计算 
    使用逐5分钟降水数据
    计算H5/H15/H30/H45/H60/H90/H120/H150/H180/H240/H360/H720/H1440
    输出：
    rain_type_df 同频率雨型
    rain_rp_df 不同重现期的同频率雨型分配
    '''
    # 1.数据读取
    total_path = glob.glob(os.path.join(file_path, '*1440*.csv'))
    data_list = []
    for path in total_path:
        rain = pd.read_csv(path)
        rain = rain['pre'].to_frame().reset_index(drop=True)
        data_list.append(rain)

    df = pd.concat(data_list, axis=1)

    ##########################################################
    # 2.各场雨最大值位置对齐 然后取平均得到序列
    num_rain = len(data_list)
    new_rain_np = df.values.T
    rain_pad = np.pad(new_rain_np, ((0, 0), (30000, 30000)), constant_values=np.nan)
    all_max_idx = np.nanargmax(rain_pad, axis=1)
    gap = all_max_idx - all_max_idx[0]

    for i in range(1, num_rain):
        rain_pad[i] = np.roll(rain_pad[i], -1 * gap[i])

    mask = np.all(np.isnan(rain_pad), axis=0)
    rain_pad = rain_pad[:, ~mask]
    rain_mean = np.nanmean(rain_pad, axis=0)
    rain_mean = np.round(rain_mean, 5)  # 序列

    ##########################################################
    # 3.滑动得到最大288段序列
    def get_max_seq288(data, seq_len):
        seq_lst = []
        max_value = []
        for i in range(len(data)):
            arr = data[i:i + seq_len]
            arr_sum = np.sum(arr, axis=0)
            seq_lst.append(arr)
            max_value.append(arr_sum)

        max_index = max_value.index(max(max_value))
        seq_result = seq_lst[max_index]
        return seq_result

    seq_288 = get_max_seq288(rain_mean, 288)
    max_288 = np.max(seq_288, axis=0)

    ##########################################################
    # 4.计算最大的H15/H30/H45/H60/H90/H120/H150/H180/H240/H360/H720，长包短
    def get_seq(data, seq_len, peak_val):
        seq_lst = []
        max_value = []
        idx_lst = []  # 和seq_lst相对应

        for i in range(len(data)):
            arr = data[i:i + seq_len]
            arr_sum = np.sum(arr, axis=0)
            seq_lst.append(arr)
            max_value.append(arr_sum)
            idx_lst.append(list(range(i, i + seq_len)))

        max_index = max_value.index(max(max_value))
        seq_result = seq_lst[max_index]
        idx_result = idx_lst[max_index]

        flag = True
        while flag:
            if set(peak_val) < set(seq_result):
                flag = False
                return seq_result, idx_result  # 返回序列和相应的idx
            else:
                # print('不包含峰值', seq_len)
                seq_lst.pop(max_index)
                max_value.pop(max_index)
                idx_lst.pop(max_index)
                max_index = max_value.index(max(max_value))
                seq_result = seq_lst[max_index]
                idx_result = idx_lst[max_index]

    # 各降水段数和相应的在288段中的idx
    seq_3, idx_3 = get_seq(seq_288, 3, peak_val=[max_288])  # H15
    seq_6, idx_6 = get_seq(seq_288, 6, peak_val=seq_3.tolist())  # H30
    seq_9, idx_9 = get_seq(seq_288, 9, peak_val=seq_6.tolist())  # H45
    seq_12, idx_12 = get_seq(seq_288, 12, peak_val=seq_9.tolist())  # H60
    seq_18, idx_18 = get_seq(seq_288, 18, peak_val=seq_12.tolist())  # H90
    seq_24, idx_24 = get_seq(seq_288, 24, peak_val=seq_18.tolist())  # H120
    seq_30, idx_30 = get_seq(seq_288, 30, peak_val=seq_24.tolist())  # H150
    seq_36, idx_36 = get_seq(seq_288, 36, peak_val=seq_30.tolist())  # H180
    seq_48, idx_48 = get_seq(seq_288, 48, peak_val=seq_36.tolist())  # H240
    seq_72, idx_72 = get_seq(seq_288, 72, peak_val=seq_48.tolist())  # H360
    seq_144, idx_144 = get_seq(seq_288, 144, peak_val=seq_72.tolist())  # H720

    # 确认各段最大值都是一个值 (要等于max_288的值)
    max_3 = np.max(seq_3, axis=0)
    max_6 = np.max(seq_6, axis=0)
    max_9 = np.max(seq_9, axis=0)
    max_12 = np.max(seq_12, axis=0)
    max_18 = np.max(seq_18, axis=0)
    max_24 = np.max(seq_24, axis=0)
    max_30 = np.max(seq_30, axis=0)
    max_36 = np.max(seq_36, axis=0)
    max_48 = np.max(seq_48, axis=0)
    max_72 = np.max(seq_72, axis=0)
    max_144 = np.max(seq_144, axis=0)
    assert max_3 == max_6 == max_9 == max_12 == max_18 == max_24 == max_30 == max_36 == max_48 == max_72 == max_144 == max_288

    ##########################################################
    # 5.计算百分比结果
    # 5-1.得到每段索引，从288段里面提取
    idx_1 = np.argmax(seq_288)  # 5min
    idx_288 = np.arange(288)
    idx_3 = np.array(idx_3)
    idx_6 = np.array(idx_6)
    idx_9 = np.array(idx_9)
    idx_12 = np.array(idx_12)
    idx_18 = np.array(idx_18)
    idx_24 = np.array(idx_24)
    idx_30 = np.array(idx_30)
    idx_36 = np.array(idx_36)
    idx_48 = np.array(idx_48)
    idx_72 = np.array(idx_72)
    idx_144 = np.array(idx_144)

    # 5-2.删除新段里面的旧段索引 (如：在6段的索引里面包含3段的索引，删除3段索引)
    mask_3 = np.in1d(idx_3, idx_1)
    mask_6 = np.in1d(idx_6, idx_3)
    mask_9 = np.in1d(idx_9, idx_6)
    mask_12 = np.in1d(idx_12, idx_9)
    mask_18 = np.in1d(idx_18, idx_12)
    mask_24 = np.in1d(idx_24, idx_18)
    mask_30 = np.in1d(idx_30, idx_24)
    mask_36 = np.in1d(idx_36, idx_30)
    mask_48 = np.in1d(idx_48, idx_36)
    mask_72 = np.in1d(idx_72, idx_48)
    mask_144 = np.in1d(idx_144, idx_72)
    mask_288 = np.in1d(idx_288, idx_144)

    idx_3_new = idx_3[~mask_3]
    idx_6_new = idx_6[~mask_6]
    idx_9_new = idx_9[~mask_9]
    idx_12_new = idx_12[~mask_12]
    idx_18_new = idx_18[~mask_18]
    idx_24_new = idx_24[~mask_24]
    idx_30_new = idx_30[~mask_30]
    idx_36_new = idx_36[~mask_36]
    idx_48_new = idx_48[~mask_48]
    idx_72_new = idx_72[~mask_72]
    idx_144_new = idx_144[~mask_144]
    idx_288_new = idx_288[~mask_288]

    # index从0开始排序
    idx_3_new_sort = np.argwhere(~mask_3)
    idx_6_new_sort = np.argwhere(~mask_6)
    idx_9_new_sort = np.argwhere(~mask_9)
    idx_12_new_sort = np.argwhere(~mask_12)
    idx_18_new_sort = np.argwhere(~mask_18)
    idx_24_new_sort = np.argwhere(~mask_24)
    idx_30_new_sort = np.argwhere(~mask_30)
    idx_36_new_sort = np.argwhere(~mask_36)
    idx_48_new_sort = np.argwhere(~mask_48)
    idx_72_new_sort = np.argwhere(~mask_72)
    idx_144_new_sort = np.argwhere(~mask_144)
    idx_288_new_sort = np.argwhere(~mask_288)

    # 5-3.得到index对应的数值，计算百分比
    def calc_percent(seq, ind):
        remain = seq[ind]
        remain_sum = remain.sum()
        tmp = []
        for i in range(len(remain)):
            tmp.append(remain[i] / remain_sum)
        tmp = np.array(tmp)

        return tmp

    seq3_remain_percent = calc_percent(seq_3, idx_3_new_sort)
    seq6_remain_percent = calc_percent(seq_6, idx_6_new_sort)
    seq9_remain_percent = calc_percent(seq_9, idx_9_new_sort)
    seq12_remain_percent = calc_percent(seq_12, idx_12_new_sort)
    seq18_remain_percent = calc_percent(seq_18, idx_18_new_sort)
    seq24_remain_percent = calc_percent(seq_24, idx_24_new_sort)
    seq30_remain_percent = calc_percent(seq_30, idx_30_new_sort)
    seq36_remain_percent = calc_percent(seq_36, idx_36_new_sort)
    seq48_remain_percent = calc_percent(seq_48, idx_48_new_sort)
    seq72_remain_percent = calc_percent(seq_72, idx_72_new_sort)
    seq144_remain_percent = calc_percent(seq_144, idx_144_new_sort)
    seq288_remain_percent = calc_percent(seq_288, idx_288_new_sort)

    # 5-4.填充结果表格3
    rain_type = np.zeros((288, 13))  # 1~288，一共13列
    rain_type[idx_1:idx_1 + 1, 12:13] = 1  # 手动自定义
    rain_type[idx_3_new, 11:12] = seq3_remain_percent
    rain_type[idx_6_new, 10:11] = seq6_remain_percent
    rain_type[idx_9_new, 9:10] = seq9_remain_percent
    rain_type[idx_12_new, 8:9] = seq12_remain_percent
    rain_type[idx_18_new, 7:8] = seq18_remain_percent
    rain_type[idx_24_new, 6:7] = seq24_remain_percent
    rain_type[idx_30_new, 5:6] = seq30_remain_percent
    rain_type[idx_36_new, 4:5] = seq36_remain_percent
    rain_type[idx_48_new, 3:4] = seq48_remain_percent
    rain_type[idx_72_new, 2:3] = seq72_remain_percent
    rain_type[idx_144_new, 1:2] = seq144_remain_percent
    rain_type[idx_288_new, 0:1] = seq288_remain_percent
    rain_type_df = pd.DataFrame(rain_type,
                                columns=['H1440-H720', 'H720-H360', 'H360-H240', 'H240-H180', 'H180-H150', 'H150-H120', 'H120-H90', 'H90-H60', 'H60-H45', 'H45-H30', 'H30-H15', 'H15-H5', 'H5'])

    # 5-5.填充结果表格4
    def calc_rain_opt(t, p, param_A, param_b, param_C, param_n):
        '''
        计算重现期
        '''
        for i in range(len(p)):
            p_time = p[i]
            formula = (param_A * (1 + param_C * np.log10(p_time))) / ((t + param_b)**param_n)
            formula = formula.reshape(-1, 1)
            formula1 = np.multiply(formula, t)

            if i == 0:
                ult = formula1
            else:
                ult = np.concatenate((ult, formula1), axis=1)

        return ult

    rain_type_col = np.sum(rain_type, axis=1)
    p = [100, 50, 30, 20, 10, 5, 3, 2]  # 重现期固定
    t = [5, 15, 30, 45, 60, 90, 120, 150, 180, 240, 360, 720, 1440]
    t = np.array(t).reshape(-1, 1)

    num_p = len(p)
    rain_rp = np.ones((288, num_p))

    # 差分
    ult = calc_rain_opt(t, p, param_A, param_b, param_C, param_n)
    rain_d_value = np.diff(ult, axis=0)
    rain_d_value = np.concatenate((ult[0].reshape(1, -1), rain_d_value), axis=0)

    rain_rp[idx_1:idx_1 + 1] = rain_d_value[0]
    rain_rp[idx_3_new] = (np.multiply(rain_d_value[1].reshape(num_p, 1), rain_type_col[idx_3_new].reshape(1, -1))).T
    rain_rp[idx_6_new] = (np.multiply(rain_d_value[2].reshape(num_p, 1), rain_type_col[idx_6_new].reshape(1, -1))).T
    rain_rp[idx_9_new] = (np.multiply(rain_d_value[3].reshape(num_p, 1), rain_type_col[idx_9_new].reshape(1, -1))).T
    rain_rp[idx_12_new] = (np.multiply(rain_d_value[4].reshape(num_p, 1), rain_type_col[idx_12_new].reshape(1, -1))).T
    rain_rp[idx_18_new] = (np.multiply(rain_d_value[5].reshape(num_p, 1), rain_type_col[idx_18_new].reshape(1, -1))).T
    rain_rp[idx_24_new] = (np.multiply(rain_d_value[6].reshape(num_p, 1), rain_type_col[idx_24_new].reshape(1, -1))).T
    rain_rp[idx_30_new] = (np.multiply(rain_d_value[7].reshape(num_p, 1), rain_type_col[idx_30_new].reshape(1, -1))).T
    rain_rp[idx_36_new] = (np.multiply(rain_d_value[8].reshape(num_p, 1), rain_type_col[idx_36_new].reshape(1, -1))).T
    rain_rp[idx_48_new] = (np.multiply(rain_d_value[9].reshape(num_p, 1), rain_type_col[idx_48_new].reshape(1, -1))).T
    rain_rp[idx_72_new] = (np.multiply(rain_d_value[10].reshape(num_p, 1), rain_type_col[idx_72_new].reshape(1, -1))).T
    rain_rp[idx_144_new] = (np.multiply(rain_d_value[11].reshape(num_p, 1), rain_type_col[idx_144_new].reshape(1, -1))).T
    rain_rp[idx_288_new] = (np.multiply(rain_d_value[12].reshape(num_p, 1), rain_type_col[idx_288_new].reshape(1, -1))).T

    rain_rp = np.round(rain_rp, 4)
    rain_rp_df = pd.DataFrame(rain_rp, columns=['100a', '50a', '30a', '20a', '10a', '5a', '3a', '2a'])

    return rain_type_df, rain_rp_df, seq_288


def step5_run_samefreq(pickle_path, file_path, param_A, param_b, param_C, param_n, save_path, start_year=None, end_year=None):
    '''
    同频率雨型
    file_path 保存10场1440雨的路径
    输出：
    seq_288 为10场雨雨峰对齐求平均后，滑动获得的最大288段
    '''
    total_max10, rain1440_list = get_max1440(pickle_path, file_path, start_year, end_year)
    rain_type_df, rain_rp_df, seq_288 = calc_same_frequency(file_path, param_A, param_b, param_C, param_n)

    # 由小数转化为百分比
    for col in rain_type_df.columns:
        rain_type_df[col] = rain_type_df[col].apply(lambda x: format(x, '.2%') if x > 0 else x)

    result = edict()
    # result['10场最大1440历时雨'] = total_max10.to_dict(orient='records')
    # result['10场最大1440对应的原始场雨(逐5min)'] = rain1440_list # 未转换dict
    # result['同频率雨型'] = rain_type_df.to_dict(orient='records')

    # 同频率画图
    result['img_save_path'] = edict()
    plt.rcParams['font.sans-serif'] = 'SimHei'
    plt.rcParams['axes.unicode_minus'] = False

    for i in [2, 3, 5, 10, 20, 30, 50, 100]:
        fig = plt.figure(figsize=(15, 8))
        ax = fig.add_subplot(111)
        xs = rain_rp_df.index
        ys = rain_rp_df[str(i) + 'a']
        ax.bar(xs, ys)
        ax.set_xlim(0, 288)
        ax.xaxis.set_major_locator(MultipleLocator(5))
        ax.yaxis.set_major_locator(MultipleLocator(1))
        ax.set_xlabel('降水时段(5min/段)', fontsize=12)
        ax.set_ylabel('降雨量', fontsize=12)
        plt.xticks(size=8)
        plt.yticks(size=8)
        plt.grid()

        save_path1 = save_path + '/samefreq_{}a.png'.format(str(i))
        plt.savefig(save_path1, dpi=300, bbox_inches='tight')
        result['img_save_path'][str(i) + 'a'] = save_path1

    plt.cla()
    plt.close('all')
    
    rain_rp_df.insert(loc=0, column='雨量段(逐5分钟)', value=rain_rp_df.index+1)
    result['rain_type'] = rain_rp_df.to_dict(orient='records')
    
    return result, seq_288


if __name__ == '__main__':
    pickle_path = 'C:/Users/mjynj/Desktop/result/step1_result.txt'
    file_path = 'C:/Users/mjynj/Desktop/result/rain10'
    param_A = 10.510
    param_b = 12.576
    param_C = 0.736
    param_n = 0.685
    save_path = 'C:/Users/mjynj/Desktop/result'
    result, seq_288 = step5_run_samefreq(pickle_path, file_path, param_A, param_b, param_C, param_n, save_path)
