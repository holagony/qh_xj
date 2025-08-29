import sys  
sys.path.append('..')

import os
import numpy as np
import pandas as pd
import time
from libs.nmc_met_io.retrieve_cmadaas import cmadaas_obs_by_time_range_and_id, cmadaas_obs_in_admin_by_time_range
from libs.nmc_met_io.retrieve_cmadaas_history import get_hist_obs_id
import datetime
from dateutil.relativedelta import relativedelta
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from Utils.config import cfg
from Utils.data_loader_with_threads import get_cmadaas_hourly_data, get_cmadaas_daily_data, get_cmadaas_min_data


def get_cmadaas_daily_data_range(years, elements, adcode='630000', sta_ids=None):
    '''
    多线程日值数据下载 用区域码
    '''
    def download_day(vals, ranges=None):
        '''
        数据下载代码
        '''
        time_range, elements, sta_ids, adcode = vals
        data_code = 'SURF_CHN_MUL_HOR'
        default_elements = 'Station_Id_C,Station_Name,Lat,Lon,Datetime,Year'
        all_elements = default_elements + ',' + elements

        # 获取数据 dataframe形式
        df = cmadaas_obs_in_admin_by_time_range(time_range=time_range, 
                                                admin=adcode, 
                                                data_code=data_code,
                                                elements=all_elements,
                                                ranges=ranges,
                                                sta_levels='011,012,013')
        return df

    # 生成输入参数
    
    start_year, end_year = map(int, years.split(','))
    range_year = np.arange(start_year, end_year+1, 1)
    time_range_template = '[{},{}]'
    all_params = [(time_range_template.format(str(year)+'0101000000', str(year)+'1231230000'), elements, sta_ids, adcode) for year in range_year]

    # 创建线程池
    with ThreadPoolExecutor(max_workers=cfg.FLIES.num_threads) as pool:
        futures = [pool.submit(download_day, param) for param in all_params]

    # 获取结果并合并数据
    # dfs = [f.result() for f in as_completed(futures)]
    dfs = []
    for f in as_completed(futures):
        if f.result() is not None:
            tmp = f.result().drop_duplicates()
            dfs.append(tmp)

    # concentrate dataframes
    if len(dfs) == 0:
        return None
    else:
        return pd.concat(dfs, axis=0, ignore_index=True).sort_values(by='Datetime')


# 保存路径
save_path = os.path.abspath(os.path.dirname(__file__))
qh_data = os.path.join(save_path,'qh_data.csv')
min_data = os.path.join(save_path,'min_data.csv')
hour_data = os.path.join(save_path,'hour_data.csv')
day_data = os.path.join(save_path,'day_data.csv')


# In[]
# 1.青海省日数据下载
years = '1990,2023'
day_ele = 'PRS_Avg,PRS_Max,PRS_Min,VAP_Avg,Squa,Lit,DuWhr,DrSnow,Snow,Frost,GSS,ICE,Thund,GST_Min,TEM_Min,TEM_Avg,WIN_S_Max,WIN_D_S_Max,SSH,PRE_Time_2020,TEM_Max,WIN_S_10mi_Avg,WIN_S_Inst_Max,RHU_Avg,PRS_Avg,TEM_Avg,TEM_Max,TEM_Min,RHU_Avg,PRS_Avg,TEM_Avg,TEM_Max,TEM_Min,RHU_Avg,RHU_Min,PRE_Time_2020,WIN_S_2mi_Avg,SSH,CLO_Cov_Avg,WIN_S_Max,FlSa,SaSt,Haze,Hail,Thund,Tord,Squa'
day_ele = day_ele.split(',')
day_ele = list(set(day_ele))
day_ele = ','.join(day_ele)

mon_ele = 'PRS_Avg,PRS_Max,PRS_Min,PRS_Max_ODay_C,PRS_Min_ODay_C,TEM_Avg,TEM_Max,TEM_Min,TEM_Max_Avg,TEM_Min_Avg,TEM_Max_ODay_C,TEM_Min_ODay_C,WIN_S_2mi_Avg,WIN_S_Max,WIN_D_S_Max_C,WIN_S_Max_ODay_C,WIN_S_Inst_Max,WIN_D_INST_Max_C,WIN_S_INST_Max_ODay_C,WIN_D_Max_C,WIN_D_Max_Freq,WIN_NNE_Freq,WIN_NE_Freq,WIN_ENE_Freq,WIN_E_Freq,WIN_ESE_Freq,WIN_SE_Freq,WIN_SSE_Freq,WIN_S_Freq,WIN_SSW_Freq,WIN_SW_Freq,WIN_WSW_Freq,WIN_W_Freq,WIN_WNW_Freq,WIN_NW_Freq,WIN_NNW_Freq,WIN_N_Freq,WIN_C_Freq,WIN_S_Avg_NNE,WIN_S_Avg_NE,WIN_S_Avg_ENE,WIN_S_Avg_E,WIN_S_Avg_ESE,WIN_S_Avg_SE,WIN_S_Avg_SSE,WIN_S_Avg_S,WIN_S_Avg_SSW,WIN_S_Avg_SW,WIN_S_Avg_WSW,WIN_S_Avg__W,WIN_S_Avg_WNW,WIN_S_Avg_NW,WIN_S_Avg_NNW,WIN_S_Avg__N,PRE_Time_2020,PRE_Max_Day,PRE_Max_ODay_C,PRE_A0p1mm_Days,PRE_A10mm_Days,PRE_A25mm_Days,PRE_A50mm_Days,PRE_A100mm_Days,PRE_A150mm_Days,Days_Max_Coti_PRE,PRE_Conti_Max,EDay_Max_Coti_PRE,NPRE_LCDays,NPRE_LCDays_EDay,PRE_Max_Conti,Days_Max_Conti_PRE,PRE_Coti_Max_EDay,RHU_Avg,RHU_Min,RHU_Min_ODay_C,GST_Avg,EGST_Max_Avg_Mon,GST_Min_Avg,GST_Max,EGST_Max_ODay_C,GST_Min,GST_Min_Ten_ODay_C,Snow_Depth_Max,V13334_060_C,PRE_Days,Hail_Days,Fog_Days,Mist_Days,Glaze_Days,Tord_Days,SoRi_Days,SaSt_Days,FlSa_Days,FlDu_Days,Haze_Days,GaWIN_Days,TEM_Avg,PRS_Avg,RHU_Avg,SSP_Mon,FRS_Depth_Max,WIN_S_2mi_Avg,WIN_S_Avg_NNE,WIN_S_Avg_NE,WIN_S_Avg_ENE,WIN_S_Avg_E,WIN_S_Avg_ESE,WIN_S_Avg_SE,WIN_S_Avg_SSE,WIN_S_Avg_S,WIN_S_Avg_SSW,WIN_S_Avg_SW,WIN_S_Avg_WSW,WIN_S_Avg__W,WIN_S_Avg_WNW,WIN_S_Avg_NW,WIN_S_Avg_NNW,WIN_S_Avg__N,WIN_NNE_Freq,WIN_NE_Freq,WIN_ENE_Freq,WIN_E_Freq,WIN_ESE_Freq,WIN_SE_Freq,WIN_SSE_Freq,WIN_S_Freq,WIN_SSW_Freq,WIN_SW_Freq,WIN_WSW_Freq,WIN_W_Freq,WIN_WNW_Freq,WIN_NW_Freq,WIN_NNW_Freq,WIN_N_Freq'
mon_ele = mon_ele.split(',')
mon_ele = set(mon_ele)
mon_ele = list(set(mon_ele))
mon_ele = ','.join(mon_ele)

year_ele = 'PRS_Avg,PRS_Max,PRS_Max_Odate,PRS_Min,PRS_Min_Odate,TEM_Avg,TEM_Max_Avg,TEM_Min_Avg,TEM_Max,V12011_067,TEM_Min,V12012_067,WIN_S_2mi_Avg,WIN_S_Max,WIN_D_S_Max_C,V11042_067,WIN_S_Inst_Max,WIN_D_INST_Max_C,WIN_S_INST_Max_ODate_C,WIN_D_Max_C,WIN_D_Max_Freq,PRE_Time_2020,PRE_Max_Day,V13052_067,PRE_A0p1mm_Days,PRE_A10mm_Days,PRE_A25mm_Days,PRE_A50mm_Days,PRE_A100mm_Days,PRE_A150mm_Days,Days_Max_Coti_PRE,PRE_Conti_Max,PRE_LCDays_EMon,EDay_Max_Coti_PRE,NPRE_LCDays,NPRE_LCDays_EMon,NPRE_LCDays_EDay,PRE_Max_Conti,Days_Max_Conti_PRE,PRE_Coti_Max_EMon,PRE_Coti_Max_EDay,RHU_Avg,RHU_Min,V13007_067,GST_Avg,EGST_Max_Avg_Mon,GST_Min_Avg,GST_Max,V12311_067,GST_Min,V12121_067,Snow_Depth_Max,V13334_067'
year_ele = year_ele.split(',')
year_ele = set(year_ele)
year_ele = list(set(year_ele))
year_ele = ','.join(year_ele)

hour_ele = 'PRS,TEM,RHU,WIN_D_Avg_10mi,WIN_S_Avg_10mi'



sta_ids = None
province_admincodes = [
    # '110000',  # 北京市
    # '120000',  # 天津市
    # '130000',  # 河北省
    # '140000',  # 山西省
    # '150000',  # 内蒙古自治区
    # '210000',  # 辽宁省
    # '220000',  # 吉林省
    # '230000',  # 黑龙江省
    # '310000',  # 上海市
    # '320000',  # 江苏省
    # '330000',  # 浙江省
    # '340000',  # 安徽省
    # '350000',  # 福建省
    # '360000',  # 江西省
    # '370000',  # 山东省
    # '410000',  # 河南省
    # '420000',  # 湖北省
    # '430000',  # 湖南省
    # '440000',  # 广东省
    # '450000',  # 广西壮族自治区
    # '460000',  # 海南省
    # '500000',  # 重庆市
    # '510000',  # 四川省
    # '520000',  # 贵州省
    # '530000',  # 云南省
    # '540000',  # 西藏自治区
    # '610000',  # 陕西省
    # '620000',  # 甘肃省
    '630000',  # 青海省
    # '640000',  # 宁夏回族自治区
    # '650000',  # 新疆维吾尔自治区
    # '710000',  # 台湾省
    # '810000',  # 香港特别行政区
    # '820000'   # 澳门特别行政区
]

for adcode in tqdm(province_admincodes):
    df1 = get_cmadaas_daily_data_range(years, hour_ele, adcode, sta_ids=None)
    save = os.path.join(save_path, adcode+'.csv')
    df1.to_csv(save, encoding='utf_8_sig', index=False)
    print(f'finish {adcode}')
    print(f'{save}')
    print()





# In[]
# 2.分钟数据下载
start_date = '20200101000000'
num_years = 6
elements = 'PRE'
sta_ids = 'G1185,G3760,G3509,G3518,G1185,G3570,G3564,G3558,G3758,G3739,G1166'
df2 = get_cmadaas_min_data(start_date,num_years,elements,sta_ids)

# In[]
df2.to_csv(min_data, encoding='utf_8_sig')
# print('分钟数据 finish')


# In[]
# # 3.小时数据下载
start_date = '20000101000000'
num_years = 10
elements = 'WIN_D_Avg_10mi,WIN_S_Avg_10mi'
sta_ids = '51576'
df3 = get_cmadaas_hourly_data(start_date,num_years,elements,sta_ids)
# df3.to_csv(hour_data, encoding='utf_8_sig')
print('小时数据 finish')


# In[]
# # 4.日数据下载
years = '2000,2020'
elements = 'PRE_Time_2020'
sta_ids = '51730'
df4 = get_cmadaas_daily_data(years, elements, sta_ids)
# df4.to_csv(day_data, encoding='utf_8_sig')
# print('日数据 finish')



