import os
import numpy as np
import pandas as pd
import pickle
import simplejson
from Utils.config import cfg
from Utils.pearson3 import pearson_type3


def p3_calc(filename, element, mode, cs_cv=None):
    
    data_dir = os.path.join(cfg.INFO.OUT_DATA_DIR, filename)
    pickle_path = os.path.join(data_dir, 'return_data.txt')
    
    with open (pickle_path, 'rb') as f:
        pickle_data = pickle.load(f)
        
    pickle_data = simplejson.loads(pickle_data)
    
    # try:
    if element == 'snow':
        pickle_data = pickle_data['data']
        rp = pickle_data['return_years']
        p3_seq = pd.DataFrame(pickle_data['data'])
        p3_seq = p3_seq.iloc[:,-1]
        # p3_params = pickle_data['p3_base']['distribution_info'] # 第一次的参数
    
        p3_result = pearson_type3(element_name='积雪深度', 
                                data=p3_seq, 
                                rp=rp,
                                img_path=data_dir, 
                                mode=mode, 
                                sv_ratio=0, 
                                ex_fitting=True, 
                                manual_cs_cv=cs_cv)
    
    elif element == 'pre_day':
        pickle_data = pickle_data['data']
        rp = pickle_data['return_years']
        p3_seq = pd.DataFrame(pickle_data['PRE_Max_Day']['data'])
        p3_seq = p3_seq.iloc[:,-1]
        p3_result = pearson_type3(element_name='日最大降水量', 
                                data=p3_seq, 
                                rp=rp,
                                img_path=data_dir, 
                                mode=mode, 
                                sv_ratio=0, 
                                ex_fitting=True, 
                                manual_cs_cv=cs_cv)
    
    elif 'minute' in element: # pre_5minute
        # pre_5minute --> 5minute --> 5min
        time = element.split('_')[1][:-3]
        pickle_data = pickle_data['data']
        rp = pickle_data['return_years']
        p3_seq = pd.DataFrame(pickle_data['PRE_Duration']['data'])
        p3_seq = p3_seq.loc[:,time]
        p3_result = pearson_type3(element_name='最大'+time+'历时降水量', 
                                data=p3_seq, 
                                rp=rp,
                                img_path=data_dir, 
                                mode=mode, 
                                sv_ratio=0, 
                                ex_fitting=True, 
                                manual_cs_cv=cs_cv)
    
    elif element == 'max_tem':
        pickle_data = pickle_data['data']
        rp = pickle_data['return_years']
        p3_seq = pd.DataFrame(pickle_data['max_tem']['data'])
        p3_seq = p3_seq.iloc[:,-1]
        p3_result = pearson_type3(element_name='极端最高气温', 
                                data=p3_seq, 
                                rp=rp,
                                img_path=data_dir, 
                                mode=mode, 
                                sv_ratio=0, 
                                ex_fitting=True, 
                                manual_cs_cv=cs_cv)
    
    elif element == 'min_tem':
        pickle_data = pickle_data['data']
        rp = pickle_data['return_years']
        p3_seq = pd.DataFrame(pickle_data[element]['data'])
        p3_seq = p3_seq.iloc[:,-1]
        p3_result = pearson_type3(element_name='极端最低气温', 
                                data=p3_seq, 
                                rp=rp,
                                img_path=data_dir, 
                                mode=mode, 
                                sv_ratio=0, 
                                ex_fitting=True, 
                                manual_cs_cv=cs_cv)
    
    elif element == 'base_max_tem':
        pickle_data = pickle_data['data']
        rp = pickle_data['return_years']
        p3_seq = pd.DataFrame(pickle_data['base_tem_max']['data'])
        p3_seq = p3_seq.iloc[:,-1]
        p3_result = pearson_type3(element_name='基本最高气温', 
                                data=p3_seq, 
                                rp=rp,
                                img_path=data_dir, 
                                mode=mode, 
                                sv_ratio=0, 
                                ex_fitting=True, 
                                manual_cs_cv=cs_cv)
    
    elif element == 'base_min_tem':
        pickle_data = pickle_data['data']
        rp = pickle_data['return_years']
        p3_seq = pd.DataFrame(pickle_data['base_tem_min']['data'])
        p3_seq = p3_seq.iloc[:,-1]
        p3_result = pearson_type3(element_name='基本最低气温', 
                                data=p3_seq, 
                                rp=rp,
                                img_path=data_dir, 
                                mode=mode, 
                                sv_ratio=0, 
                                ex_fitting=True, 
                                manual_cs_cv=cs_cv)
    
    elif element == 'wind':
        pickle_data = pickle_data['data']
        pickle_data = pickle_data['result_part1']
        rp = pickle_data['return_years']
        p3_seq = pd.DataFrame(pickle_data['wind_data'])
        p3_seq = p3_seq.iloc[:,-1]
        p3_result = pearson_type3(element_name='风速', 
                                data=p3_seq, 
                                rp=rp,
                                img_path=data_dir, 
                                mode=mode, 
                                sv_ratio=0, 
                                ex_fitting=True, 
                                manual_cs_cv=cs_cv)
            
    # except Exception:
    #         raise Exception('无法调参，请先生成初始的P3画图')

    return p3_result


if __name__ == '__main__':
    # filename = 'bbb'
    # element = 'wind'
    # mode = 4
    # cs_cv = [0.1,0.2]
    # # p3_result = p3_calc(filename, element, mode, cs_cv)
    
    # data_dir = os.path.join(cfg.INFO.OUT_DATA_DIR, filename)
    # pickle_path = os.path.join(data_dir, 'return_data.txt')
    
    pickle_path = r'C:\Users\MJY\Desktop\result\bbb\风2_return_data.txt'
    with open (pickle_path, 'rb') as f:
        pickle_data = pickle.load(f)
        
    pickle_data = simplejson.loads(pickle_data)
    # pickle_data = pickle_data['data']
    # pickle_data = pickle_data['result_part1']






