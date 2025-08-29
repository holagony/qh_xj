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

# 逐小时下载
# set retrieve parameters
# data_code = "SURF_CHN_MUL_HOR"  # 中国地面逐小时(国家站) # SURF_CHN_MUL_HOR/SURF_CHN_PRE_MIN
# elements = "Station_Id_C,Station_Name,Lat,Lon,Alti,Datetime,Year,Mon,Day,Hour,TEM"
# sta_ids = "59948"

# fmt = '%Y%m%d%H%M%S'
# start = datetime.datetime.strptime('20000101000000', fmt)

# num_years = 21
# interval = 6*num_years
# for i in tqdm(range(0,interval)):
#     start_1 = (start+relativedelta(months=2)*i).strftime(fmt)  
#     end_1 = (start+relativedelta(months=2)*(i+1)).strftime(fmt)

#     time_range = '[' + start_1 + ',' + end_1 + ')'
#     data = cmadaas_obs_by_time_range_and_id(time_range, data_code=data_code, elements=elements, sta_ids=sta_ids)

#     if i == 0:
#         df = data
#     else:
#         df = pd.concat([df,data],axis=0)
# df.to_csv(r'C:\Users\MJY\Desktop\59948分钟1980-2021.csv',encoding='utf_8_sig')



def get_hourly_data(vals, ranges=None):
    '''
    以年为跨度，获取天擎小时数据
    '''
    # ranges = 'Station_Id_d:(50000,60000)'
    ranges = None
    time_range, elements, sta_ids = vals
    data_code = 'SURF_CHN_MUL_HOR'
    default_elements = 'Station_Id_C,Station_Name,Lat,Lon,Datetime,Year,Mon,Day,Hour'
    all_elements = default_elements + ',' + elements
    # df = pd.DataFrame([time_range, elements, sta_ids]).T
    df = cmadaas_obs_by_time_range_and_id(time_range=time_range, 
                                          data_code=data_code, 
                                          elements=all_elements,  
                                          sta_ids=sta_ids,
                                          ranges=ranges)

    # df = cmadaas_obs_in_admin_by_time_range(time_range=time_range,
    #                                         admin='320900',
    #                                         data_code=data_code,
    #                                         ranges=ranges,
    #                                         elements=all_elements)
    return df


def download(start_date,num_years,elements,sta_ids,N):
    # 生成输入参数
    fmt = '%Y%m%d%H%M%S'
    date = datetime.datetime.strptime(str(start_date), fmt)
    interval = 6 * num_years - 1

    all_params = []
    for i in range(0, interval + 1):
        start = (date + relativedelta(months=2) * i).strftime(fmt)
        end = (date + relativedelta(months=2) * (i + 1)).strftime(fmt)
        time_range = '[' + start + ',' + end + ')'
        p = [time_range, elements, sta_ids]
        all_params.append(p)

    # 创建线程
    with ThreadPoolExecutor(max_workers=N) as pool:
        res = [pool.submit(lambda params: get_hourly_data(*params), (vals,)) for vals in all_params]

    for num,future in enumerate(tqdm(as_completed(res))):
        data = future.result()

        if num == 0:
            df = data
        else:
            df = pd.concat([df,data],axis=0)
    
    return df


# run
N = 10
start_date = '19930101000000'
num_years = 30
elements = 'TEM,PRS,RHU,PRE_1h,WIN_D_Avg_10mi,WIN_S_Avg_10mi'
sta_ids = '59948'
df = download(start_date,num_years,elements,sta_ids,N)

print(df.head(10))
df.to_csv(cfg.FILES.test_csv, encoding='utf_8_sig')


# path = r'C:\Users\HT\Desktop\test.csv'
# df = pd.read_csv(path)
# df.set_index('Datetime', inplace=True)
# df.index = pd.DatetimeIndex(df.index)
# df = df.sort_index()