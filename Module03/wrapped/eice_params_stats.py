import numpy as np
import pandas as pd
from Utils.data_processing import daily_data_processing
import logging

def eice_params_statistics(data_df):
    '''
    电线积冰-南北方向直径
    电线积冰-南北方向厚度
    电线积冰-南北方向重量
    电线积冰-东西方向直径
    电线积冰-东西方向厚度
    电线积冰-东西方向重量
    
    如果某个站的电线积冰要素全为nan，则结果里面没有这个站，
    如果所有站的所有积冰要素都是nan，则输出None
    '''
    try:
        eice = data_df[['Station_Name', 'EICED_NS', 'EICET_NS', 'EICEW_NS', 'EICED_WE', 'EICET_WE', 'EICEW_WE']]
    
        eice.insert(1, 'date', eice.index.strftime('%Y-%m-%d'))
        eice_dropna = eice.dropna(axis=0, how='all', subset=['EICED_NS', 'EICET_NS', 'EICEW_NS', 'EICED_WE', 'EICET_WE', 'EICEW_WE'])
    
        eice_result = eice_dropna.copy()
        eice_result['sum'] = eice_result.iloc[:, 2:].sum(axis=1)
        eice_result = eice_result[eice_result['sum'] != 0]
        eice_result.drop(['sum'], axis=1, inplace=True)
        eice_result.reset_index(drop=True, inplace=True)
        eice_result.columns = ['站名', '日期', '南北方向直径(mm)', '南北方向厚度(mm)', '南北方向重量(g)', '东西方向直径(mm)', '东西方向厚度(mm)', '东西方向重量(g)']
    
        eice_result.sort_values(by=['站名', '日期'], ascending=[True, True], inplace=True)
        eice_result.reset_index(drop=True, inplace=True)
        
        if eice_result.shape[0] == 0:
            eice_result = None
        else:
            eice_result = eice_result.round(1).to_dict(orient='records')
    
    except Exception as e:
        eice_result = None

    return eice_result


if __name__ == '__main__':
    path = r'C:\Users\mjynj\Desktop\sd-scdp-algo\Files\Module03_data\day.csv'
    day_data = pd.read_csv(path)
    day_data = daily_data_processing(day_data)
    # day_data.loc[day_data['Station_Id_C'] == '54843',
    #              ['EICED_NS', 'EICET_NS', 'EICEW_NS', 'EICED_WE', 'EICET_WE', 'EICEW_WE']] = np.nan  # 模拟某个站该要素全是nan
    # day_data.loc[day_data['Station_Id_C'] == '54823',
    #              ['EICED_NS', 'EICET_NS', 'EICEW_NS', 'EICED_WE', 'EICET_WE', 'EICEW_WE']] = np.nan  # 模拟某个站该要素全是nan
    # day_data = None
    eice_result = eice_params_statistics(day_data)