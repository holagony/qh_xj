import os
import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Module11.wrapped.wind_dataloader import get_data_postgresql, wind_tower_processing
from Utils.data_processing import daily_data_processing


def wind_stats3(data_dict, df_sta, input_ws, output_ws):
    '''
    风速&风功率参数统计
    
    1.空气密度
    2.逐月平均风速
    3.逐月平均风功率密度
    4.逐月平均有效风功率密度
    5.平均风速日变化
    6.平均风功率密度日变化
    7.平均有效风功率密度日变化
    8.综合参数统计
    '''
    transfer_heights = np.array([10, 25, 30, 40, 50, 60, 70, 80, 90, 100]).reshape(-1, 1)  # 需要转换的高度，用来计算相应的空气密度
    result = edict()

    # 气象站空气密度
    rho_accum = []
    for i in range(1, 13):
        month_i_mean = df_sta[df_sta.index.month == i]
        rho_tmp = (month_i_mean['PRS_Avg'] * 100 / (287 * (month_i_mean['TEM_Avg'] + 273.15))).mean()
        rho_trans = (rho_tmp * np.exp(-0.0001 * (transfer_heights - 10))).round(3)
        rho_accum.append(rho_trans)
    rho_accum = np.concatenate(rho_accum, axis=1)
    rho_accum = pd.DataFrame(rho_accum, columns=[str(i) + '月' for i in range(1, 13)])
    rho_accum['年'] = rho_accum.iloc[:, :].mean(axis=1).round(3)
    rho_accum.insert(loc=0, column='高度', value=[str(h) + 'm' for h in transfer_heights.flatten()])

    for sta, sub_dict in data_dict.items():
        result[sta] = edict()
        ws_df = sub_dict['ws_10'].filter(like='m_hour_ws')
        ws_max = sub_dict['ws_max'].filter(like='m_ws_max')
        ws_max_inst = sub_dict['ws_max_inst'].filter(like='m_ws_inst_max')

        # 1.空气密度
        # try:
        #     meteo = pd.concat([sub_dict['prs'], sub_dict['tem']], axis=1)
        #     meteo_monthly = meteo.resample('1M')['prs', '10m_tem'].mean()
        #     time = list(meteo_monthly.index.strftime('%Y-%m'))
        #     prs = meteo_monthly['prs'].values  # 气压单位是百帕hpa
        #     tem = meteo_monthly['10m_tem'].values
        #     rho = prs * 100 / (287 * (tem + 273.15))
        #     rho_trans = (rho * np.exp(-0.0001 * (transfer_heights - 10))).round(3)
        #     rho_trans = pd.DataFrame(rho_trans, columns=time)
        #     rho_trans.insert(loc=0, column='高度', value=[str(h) + 'm' for h in transfer_heights.flatten()])
        # except:
        #     rho_trans = None

        # 2.逐月平均风速
        ws_monthly = ws_df.resample('1M').mean().round(2)
        ws_monthly.columns = [col.split('_')[0] for col in ws_monthly.columns]
        ws_monthly.insert(loc=0, column='时间', value=ws_monthly.index.strftime('%Y-%m'))
        ws_monthly.reset_index(drop=True, inplace=True)

        # 3.逐月平均风功率密度
        rho = (df_sta['PRS_Avg'] * 100 / (287 * (df_sta['TEM_Avg'] + 273.15))).mean()  # 10米高度平均空气密度
        wind_heights = np.array([int(col.split('_')[0][0:-1]) for col in ws_df.columns])
        new_rho = rho * np.exp(-0.0001 * (wind_heights - 10))
        wind_pd = (1 / 2) * new_rho * (ws_df**3)
        wind_pd_monthly = wind_pd.resample('1M').mean().round(1)
        wind_pd_monthly.columns = [col.split('_')[0] for col in wind_pd_monthly.columns]
        wind_pd_monthly.insert(loc=0, column='时间', value=wind_pd_monthly.index.strftime('%Y-%m'))
        wind_pd_monthly.reset_index(drop=True, inplace=True)

        # 4.逐月平均有效风功率密度
        mask_ws = ws_df.mask((ws_df > output_ws) | (ws_df < input_ws), np.nan)
        if len(mask_ws) == 0:  # 说明经过风速筛选后无数据
            mask_pd_monthly = None
            mask_pd_hourly_accum = None
        else:
            mask_pd = (1 / 2) * new_rho * (mask_ws**3)
            mask_pd_monthly = mask_pd.resample('1M').mean().round(1)
            mask_pd_monthly.columns = [col.split('_')[0] for col in mask_pd_monthly.columns]
            mask_pd_monthly.insert(loc=0, column='时间', value=mask_pd_monthly.index.strftime('%Y-%m'))
            mask_pd_monthly.reset_index(drop=True, inplace=True)

        # 5.平均风速日变化
        ws_hourly_accum = []
        for i in range(0, 24):
            hour_i_mean = ws_df[ws_df.index.hour == i].mean().round(2)
            ws_hourly_accum.append(hour_i_mean)

        ws_hourly_accum = pd.DataFrame(ws_hourly_accum).T
        ws_hourly_accum.columns = [str(i) + '时' for i in range(24)]
        ws_hourly_accum.insert(loc=0, column='高度', value=[idx.split('_')[0] for idx in ws_hourly_accum.index])
        ws_hourly_accum.reset_index(drop=True, inplace=True)

        # 6.平均风功率密度日变化
        wind_pd_hourly_accum = []
        for i in range(0, 24):
            hour_i_mean = wind_pd[wind_pd.index.hour == i].mean().round(1)
            wind_pd_hourly_accum.append(hour_i_mean)

        wind_pd_hourly_accum = pd.DataFrame(wind_pd_hourly_accum).T
        wind_pd_hourly_accum.columns = [str(i) + '时' for i in range(24)]
        wind_pd_hourly_accum.insert(loc=0, column='高度', value=[idx.split('_')[0] for idx in wind_pd_hourly_accum.index])
        wind_pd_hourly_accum.reset_index(drop=True, inplace=True)

        # 7.平均有效风功率密度日变化
        if len(mask_ws) != 0:
            mask_pd_hourly_accum = []
            for i in range(0, 24):
                hour_i_mean = mask_pd[mask_pd.index.hour == i].mean().round(1)
                mask_pd_hourly_accum.append(hour_i_mean)

            mask_pd_hourly_accum = pd.DataFrame(mask_pd_hourly_accum).T
            mask_pd_hourly_accum.columns = [str(i) + '时' for i in range(24)]
            mask_pd_hourly_accum.insert(loc=0, column='高度', value=[idx.split('_')[0] for idx in mask_pd_hourly_accum.index])
            mask_pd_hourly_accum.reset_index(drop=True, inplace=True)

        # 8.综合参数统计
        ratio = ws_df.apply(lambda x: round(len(x[(x > input_ws) & (x < output_ws)]) / len(x) * 100, 2))  # 3-25m/s百分率
        ratio = ratio.to_frame().reset_index(drop=True)
        ratio.columns = ['有效风速小时数百分率%']

        hours = ws_df.apply(lambda x: len(x[(x > input_ws) & (x < output_ws)]))  # 3-25m/s小时数(sum)
        hours = hours.to_frame().reset_index(drop=True)
        hours.columns = ['有效风速小时数']

        mean_ws = ws_df.mean().round(2)  # 平均风速(mean)
        mean_ws = mean_ws.to_frame().reset_index(drop=True)
        mean_ws.columns = ['平均风速(m/s)']

        mean_pd = wind_pd_monthly.iloc[:, 1:].mean(axis=0).round(1)  # 平均风功率密度(mean)
        mean_pd = mean_pd.to_frame().reset_index(drop=True)
        mean_pd.columns = ['平均风功率密度(W/m²)']

        mean_mask_pd = mask_pd_monthly.iloc[:, 1:].mean(axis=0).round(1)  # 有效风功率密度(mean)
        mean_mask_pd = mean_mask_pd.to_frame().reset_index(drop=True)
        mean_mask_pd.columns = ['有效风功率密度(W/m²)']

        max_ws = ws_max.max()
        max_ws = max_ws.to_frame().reset_index(drop=True)
        max_ws.columns = ['最大风速(m/s)']

        max_ws_inst = ws_max_inst.max()
        max_ws_inst = max_ws_inst.to_frame().reset_index(drop=True)
        max_ws_inst.columns = ['极大风速(m/s)']

        param_stats = pd.concat([ratio, hours, mean_ws, mean_pd, mean_mask_pd, max_ws, max_ws_inst], axis=1)
        param_stats.insert(loc=0, column='高度', value=[idx.split('_')[0] for idx in ws_df.columns])

    # 保存
    result['气象站空气密度'] = rho_accum.to_dict(orient='records')
    # result[sta]['1测风塔空气密度'] = rho_trans.to_dict(orient='records')
    result[sta]['综合参数统计'] = param_stats.to_dict(orient='records')
    result[sta]['逐月平均风速'] = ws_monthly.to_dict(orient='records')
    result[sta]['逐月平均风功率密度'] = wind_pd_monthly.to_dict(orient='records')
    result[sta]['逐月平均有效风功率密度'] = mask_pd_monthly.to_dict(orient='records')
    result[sta]['平均风速日变化'] = ws_hourly_accum.to_dict(orient='records')
    result[sta]['平均风功率密度日变化'] = wind_pd_hourly_accum.to_dict(orient='records')
    result[sta]['平均有效风功率密度日变化'] = mask_pd_hourly_accum.to_dict(orient='records')

    return result


if __name__ == '__main__':
    daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    post_daily_df = daily_data_processing(daily_df)
    post_daily_df = post_daily_df[post_daily_df['Station_Id_C'] == '52866']
    post_daily_df = post_daily_df[['TEM_Avg', 'PRS_Avg']]
    
    df = get_data_postgresql(sta_id='QH001', time_range='20230801,20240630')
    after_process = wind_tower_processing(df)
    result = wind_stats3(after_process, post_daily_df, 3, 25)
