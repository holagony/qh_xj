import os
import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Module11.wrapped.wind_dataloader import get_data_postgresql, wind_tower_processing
from Utils.data_processing import wind_direction_to_symbol, daily_data_processing
from Utils.get_local_data import get_local_data


def wind_stats4(data_dict, df_sta, input_ws, output_ws):
    '''
    风能参数统计
    1.风向频率
    2.风能密度方向频率
    3.逐月有效风速小时数
    4.各风速等级小时数
    5.风速频率分布
    6.各风速区间风能频率分布
    '''
    result = edict()

    for sta, sub_dict in data_dict.items():
        ws_df = sub_dict['ws_10'].filter(like='m_hour_ws')
        wd_df = sub_dict['wd_10'].filter(like='m_hour_wd').round(0)
        wd_df = wd_df.copy()

        # 1.风向频率
        for i, col in enumerate(wd_df.columns):
            wd_df[col] = wd_df[col].astype(str).apply(wind_direction_to_symbol)
            counts = wd_df[col].value_counts().to_frame()
            freq = ((counts / counts.sum()) * 100).round(1)

            if i == 0:
                all_freq_wd = freq
            else:
                all_freq_wd = pd.concat([all_freq_wd, freq], axis=1)

        all_freq_wd = all_freq_wd.T
        all_freq_wd.insert(loc=0, column='高度', value=[h.split('_')[0] for h in all_freq_wd.index])
        all_freq_wd.reset_index(drop=True, inplace=True)

        # 2.风能密度方向频率
        # 计算空气密度
        rho = (df_sta['PRS_Avg'] * 100 / (287 * (df_sta['TEM_Avg'] + 273.15))).mean()  # 10米高度平均空气密度
        wind_heights = np.array([int(col.split('_')[0][0:-1]) for col in ws_df.columns])
        new_rho = rho * np.exp(-0.0001 * (wind_heights - 10))

        # 计算不同高度风速对应的小时风能密度(t=1)
        wind_pd = (1 / 2) * new_rho * (ws_df**3)

        # 对每个高度，统计不同风向下的风能密度之和
        for i in range(len(wind_heights)):
            h = wind_heights[i]
            concat = pd.concat([wd_df.iloc[:, i], wind_pd.iloc[:, i]], axis=1)
            counts = concat.groupby(str(h) + 'm_hour_wd')[str(h) + 'm_hour_ws'].sum()
            freq = ((counts / counts.sum()) * 100).round(1)

            if i == 0:
                all_freq_pd = freq
            else:
                all_freq_pd = pd.concat([all_freq_pd, freq], axis=1)

        all_freq_pd = all_freq_pd.T
        all_freq_pd.insert(loc=0, column='高度', value=[h.split('_')[0] for h in all_freq_pd.index])
        all_freq_pd.reset_index(drop=True, inplace=True)
        all_freq_pd = all_freq_pd[all_freq_wd.columns]  # 列排序

        # 3.逐月有效风速小时数
        ws_hours = ws_df.resample('1M').apply(lambda x: len(x[(x > input_ws) & (x < output_ws)]))
        ws_hours.columns = [col.split('_')[0] for col in ws_hours.columns]
        ws_hours.insert(loc=0, column='时间', value=ws_hours.index.strftime('%Y-%m'))
        ws_hours.reset_index(drop=True, inplace=True)

        # 4.各风速等级小时数
        def sample_hours(x):
            x_res = []
            for i in range(3, 16):
                if i != 15:
                    x1 = len(x[(x > i) & (x < 25)])
                else:
                    x1 = len(x[x > i])
                x_res.append(x1)
            return x_res

        ws_hours_filter = ws_df.apply(sample_hours, axis=0).T
        ws_hours_filter.columns = ['3-25m/s', '4-25m/s', '5-25m/s', '6-25m/s', '7-25m/s', '8-25m/s', '9-25m/s', '10-25m/s', '11-25m/s', '12-25m/s', '13-25m/s', '14-25m/s', '>15m/s']
        ws_hours_filter.insert(loc=0, column='高度', value=[h.split('_')[0] for h in ws_hours_filter.index])
        ws_hours_filter.reset_index(drop=True, inplace=True)

        # 5.风速频率分布
        ws_bins = [0, 0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21.5]  # 划分的风速等级
        ws_bins_cols = [str(ws_bins[i - 1]) + '-' + str(ws_bins[i]) + 'm/s' for i in range(1, len(ws_bins))]  # 生成的列名

        for i, col in enumerate(ws_df.columns):
            h = col.split('_')[0]
            ws_hist, _ = np.histogram(ws_df[col], bins=ws_bins)  # numpy直方图分箱一维风速数据
            ws_hist = ((ws_hist / ws_hist.sum()) * 100).round(1)  # 随后对每个区间统计的次数转化为频率
            ws_hist = pd.DataFrame(ws_hist.reshape(1, -1), index=[h], columns=ws_bins_cols)

            if i == 0:
                all_ws_hist = ws_hist
            else:
                all_ws_hist = pd.concat([all_ws_hist, ws_hist], axis=0)

        all_ws_hist.insert(loc=0, column='高度', value=all_ws_hist.index)
        all_ws_hist.reset_index(drop=True, inplace=True)

        # 6.各风速区间风能频率分布
        pd_bins = [0, 0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24.5]
        pd_bins_cols = [str(pd_bins[i - 1]) + '-' + str(pd_bins[i]) + 'm/s' for i in range(1, len(pd_bins))]

        for i in range(len(wind_heights)):
            h = wind_heights[i]
            concat = pd.concat([ws_df.iloc[:, i], wind_pd.iloc[:, i]], axis=1)
            concat.columns = [str(h) + 'm_ws', str(h) + 'm_pd']
            concat[str(h) + 'm_ws'] = pd.cut(concat[str(h) + 'm_ws'], bins=pd_bins, labels=pd_bins_cols)  # pd.cut对风速数据分箱
            hist = concat.groupby(str(h) + 'm_ws')[str(h) + 'm_pd'].sum()  # 对分箱后的分速标签groupby，计算在各区间里面对应的风能密度总和
            hist = ((hist / hist.sum()) * 100).round(1)  # 转为频率

            if i == 0:
                all_pd_hist = hist
            else:
                all_pd_hist = pd.concat([all_pd_hist, hist], axis=1)

        all_pd_hist = all_pd_hist.T
        all_pd_hist.insert(loc=0, column='高度', value=[h.split('_')[0] for h in all_pd_hist.index])
        all_pd_hist.reset_index(drop=True, inplace=True)

        # 结果创建
        result[sta] = edict()
        result[sta]['风向频率'] = all_freq_wd.to_dict(orient='records')
        result[sta]['风能密度方向频率'] = all_freq_pd.to_dict(orient='records')
        result[sta]['逐月有效风速小时数'] = ws_hours.to_dict(orient='records')
        result[sta]['各风速等级小时数'] = ws_hours_filter.to_dict(orient='records')
        result[sta]['风速频率分布'] = all_ws_hist.to_dict(orient='records')
        result[sta]['各风速区间风能频率分布'] = all_pd_hist.to_dict(orient='records')

    return result


if __name__ == '__main__':
    daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    day_eles = ('Station_Id_C,Station_Name,Lat,Lon,Datetime,Year,Mon,Day,' + 'TEM_Avg,PRS_Avg').split(',')
    years = '2010,2020'
    post_daily_df = get_local_data(daily_df, '52866', day_eles, years, 'Day')
    
    df = get_data_postgresql(sta_id='XJ_dabancheng', time_range='20220701,20230731')
    after_process = wind_tower_processing(df)
    result = wind_stats4(after_process, post_daily_df, 3, 25)