import numpy as np
import pandas as pd
from scipy import stats
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_processing import daily_data_processing


def t_test_independent_samples(test_data, alpha=2):
    '''
    两独立样本T检验，用于检验两个独立样本总体的均值是否相等
    要求样本服从正态分布，不要求数据长度相等

    Args:
        data1: 输入的气象要素时间序列A，如: 站A的2020.1-2020.2的逐小时温度；类型: array/dataframe
        data1: 输入的气象要素时间序列B，如: 站B的2020.1-2020.2的逐小时温度；类型: array/dataframe
        alpha: 检验两组样本是否具有方差齐性的超参，根据经验设定2~4；类型: float

    Returns:
        t_statistic: 独立样本T检验的计算结果；类型: float
        p_val: 计算得到的p值，p大于0.05说明无差异；类型: float
    '''
    test_data = test_data.values
    data1 = test_data[:, 0]
    data2 = test_data[:, 1]

    # 先确定两组样本是否具有方差齐性
    _, pvalue = stats.levene(data1, data2)

    if pvalue > 0.05 * alpha:  # 认为两组数据具有方差齐性
        t_statistic, p_val = stats.ttest_ind(data1, data2, equal_var=True)
    else:
        t_statistic, p_val = stats.ttest_ind(data1, data2, equal_var=False)

    return t_statistic, p_val


def levene_test(test_data):
    '''
    F检验 方差检验
    '''
    test_data = test_data.values
    data1 = test_data[:, 0]
    data2 = test_data[:, 1]
    f_statistic, p_val = stats.levene(data1, data2)

    return f_statistic, p_val


def get_value_matrix(data, elements, main_st, sub_st, method):
    '''
    获得多个主站 vs 一个子站的T检验/F检验结果矩阵
    '''
    result_matrix = np.zeros((len(elements), len(sub_st)))
    element_name = []

    for i, ele in enumerate(elements):

        for j in range(len(sub_st)):
            main_data = data[data['Station_Id_C'] == main_st][ele].to_frame()
            sub_data = data[data['Station_Id_C'] == sub_st[j]][ele].to_frame()
            concat_data = pd.concat([main_data, sub_data], axis=1)
            concat_data = concat_data.dropna(how='any', axis=0)  # 保证时间一致

            if method == 't_test':
                _, p_val = t_test_independent_samples(concat_data, alpha=2)
            elif method == 'f_test':
                _, p_val = levene_test(concat_data)

            result_matrix[i][j] = p_val

        result_matrix = result_matrix.round(5)
        element_name.append(ele)

    result_df = pd.DataFrame(result_matrix, index=element_name, columns=sub_st)

    return result_df


def sample(x):
    all_dict = edict()
    for ele in x.columns:
        if ele in ['TEM_Avg','PRS_Avg','RHU_Avg','WIN_S_2mi_Avg']:
            mean_accum = []
            tmp = x[ele]
            for i in range(1, 13):
                month_i_mean = tmp[tmp.index.month == i].mean().round(1)
                mean_accum.append(month_i_mean)
            all_dict[ele] = mean_accum
                            
        elif ele in ['TEM_Max','PRS_Max','WIN_S_Max']:
            max_accum = []
            tmp = x[ele]
            for i in range(1, 13):
                month_i_max = np.round(tmp[tmp.index.month == i].max(),1)
                max_accum.append(month_i_max)
            all_dict[ele] = max_accum
        
        elif ele in ['TEM_Min','PRS_Min']:
            min_accum = []
            tmp = x[ele]
            for i in range(1, 13):
                month_i_min =  np.round(tmp[tmp.index.month == i].min(),1)
                min_accum.append(month_i_min)
            all_dict[ele] = min_accum
        
        elif ele == 'PRE_Time_2020':
            sum_accum = []
            tmp = x[ele]
            for i in range(1, 13):
                month_i_sum =  np.round(tmp[tmp.index.month == i].sum(),1)
                sum_accum.append(month_i_sum)
            all_dict[ele] = sum_accum

    return all_dict


def space_analysis(data, elements, main_st, sub_st, method):
    '''
    空间一致性分析，T检验和F检验
    主站和子站数据都来自天擎
    main_st: str
    sub_st: list
    '''
    # 生成elements对应的中文列表
    replace_dict = {'PRS_Avg': '平均气压', 
                    'PRS_Max': '最高气压', 
                    'PRS_Min': '最低气压', 
                    'TEM_Avg': '平均气温', 
                    'TEM_Min': '最低气温', 
                    'TEM_Max': '最高气温', 
                    'RHU_Avg': '平均湿度', 
                    'PRE_Time_2020': '降水量', 
                    'WIN_S_2mi_Avg': '平均风速', 
                    'WIN_S_Max': '最大风速'}

    # elements_ch和elements顺序相同 list
    elements_ch = [replace_dict[ele] if ele in replace_dict else ele for ele in elements]

    # T检验/F检验计算
    all_result = edict()
    all_result['day'] = edict()

    if 't_test' in method:
        result_t_month = get_value_matrix(data, elements, main_st, sub_st, 't_test')
        result_t_month.reset_index(inplace=True,drop=True)
        result_t_month.insert(loc=0, column='要素', value=elements_ch)
        all_result['day']['t_test'] = result_t_month.to_dict(orient='records')
        
    if 'f_test' in method:
        result_f_month = get_value_matrix(data, elements, main_st, sub_st, 'f_test')
        result_f_month.reset_index(inplace=True,drop=True)
        result_f_month.insert(loc=0, column='要素', value=elements_ch)
        all_result['day']['f_test'] = result_f_month.to_dict(orient='records')

    # 数据累年各月计算，合并放一起
    data_list = list(data.groupby(['Station_Name','Station_Id_C']))
    accum_concat = []
    for key in data_list:
        st_name = key[0][0]
        st_id = key[0][1]
        data_tmp = key[1]
        accum_tmp = sample(data_tmp)
        accum_tmp = pd.DataFrame(accum_tmp).T
        accum_tmp.reset_index(drop=False,inplace=True)
        accum_tmp.insert(loc=1, column='Station_Name', value=st_name)
        accum_tmp.insert(loc=2, column='Station_Id', value=st_id)
        accum_concat.append(accum_tmp)
    
    accum_result = pd.concat(accum_concat,axis=0)
    accum_result.columns = ['要素','站名','站号','1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月']
    accum_result['平均'] = accum_result.iloc[:,3:].mean(axis=1).round(1)
    accum_result.replace(replace_dict, inplace=True)
    
    for ele in elements_ch:
        try:
            tmp = accum_result[accum_result['要素']==ele]
            tmp.set_index('站号',inplace=True)
            sta_ids = [main_st] + sub_st
            tmp = tmp.reindex(index=sta_ids)
            tmp.insert(loc=2, column='站号', value=tmp.index)
            tmp.reset_index(drop=True,inplace=True)
            all_result[ele] = tmp.to_dict(orient='records')
        except:
            pass

    return all_result


if __name__ == '__main__':
    method = ['f_test','t_test']
    elements = ['TEM_Avg','PRS_Avg','RHU_Avg','WIN_S_2mi_Avg','TEM_Max','PRS_Max','WIN_S_Max','TEM_Min','PRS_Min','PRE_Time_2020']
    daily_elements = ','.join(elements)
    day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements).split(',')
    main_sta_ids = '52866'
    sub_sta_ids = '52818,52602'
    sta_ids = main_sta_ids + ',' + sub_sta_ids
    sta_ids1 = [int(ids) for ids in sta_ids.split(',')]
    daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    daily_df = daily_df.loc[daily_df['Station_Id_C'].isin(sta_ids1), day_eles]
    daily_df = daily_data_processing(daily_df)

    sub_sta_ids = sub_sta_ids.split(',')
    result_dict = space_analysis(daily_df, elements, main_sta_ids, sub_sta_ids, method)


    