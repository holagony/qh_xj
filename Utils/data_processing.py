import os
import glob
import json
import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.cost_time import cost_time


def ODay_C_process1(x):
    '''
    pandas的apply函数
    用于一般要素所对应的，出现日期要素处理，月数据
    要素是日数
    '''
    x = x.split('.')[0]

    if '9990' in x:
        x = x.split('0')[-1] + 'T'

    if '-' in x:
        lens = len(x.split('-'))
        x = str(lens) + 'T'

    if x[0] == '0':
        try:
            x = x[1]
        except:
            pass

    if x == '999999':
        x = np.nan

    return x


def ODay_C_process2(x):
    '''
    pandas的apply函数
    用于一般要素所对应的，出现日期要素处理，年数据
    '''
    x = x.split('.')[0]

    if '9990' in x:
        x = x.split('0')[-1] + 'T'

    # if '-' in x:
    #     lens = len(x.split('-'))
    #     x = str(lens) + 'T'

    try:
        if int(x) < 9999:
            month = x[:-2]
            day = x[-2:]
            if month == '':
                x = day.zfill(2) + '日'
            else:
                x = month.zfill(2) + '月' + day.zfill(2) + '日'
    except:
        x = np.nan

    if x == '999999':
        x = np.nan

    return x


def ODay_C_process3(x):
    '''
    pandas的apply函数
    用于降水要素所对应，出现日期要素处理，年数据
    '''
    if '9990' in x:
        x = x.split('0')[-1] + 'T'
    elif '999999' in x:
        # x = 'nan'
        x = np.nan

    return x


def wind_direction_to_symbol(x):
    '''
    pandas的apply函数
    把任何形式的风向统一处理为字母符号形式，年/月/日数据
    '''
    try:
        x = float(x)
        if (348.76 <= x <= 360.0) or (0 <= x <= 11.25) or (x == 999001):
            x = 'N'

        elif (11.26 <= x <= 33.75) or (x == 999002):
            x = 'NNE'

        elif (33.76 <= x <= 56.25) or (x == 999003):
            x = 'NE'

        elif (56.26 <= x <= 78.75) or (x == 999004):
            x = 'ENE'

        elif (78.76 <= x <= 101.25) or (x == 999005):
            x = 'E'

        elif (101.26 <= x <= 123.75) or (x == 999006):
            x = 'ESE'

        elif (123.76 <= x <= 146.25) or (x == 999007):
            x = 'SE'

        elif (146.26 <= x <= 168.75) or (x == 999008):
            x = 'SSE'

        elif (168.26 <= x <= 191.75) or (x == 999009):
            x = 'S'

        elif (191.26 <= x <= 213.75) or (x == 999010):
            x = 'SSW'

        elif (213.26 <= x <= 236.75) or (x == 999011):
            x = 'SW'

        elif (236.26 <= x <= 258.75) or (x == 999012):
            x = 'WSW'

        elif (258.26 <= x <= 281.75) or (x == 999013):
            x = 'W'

        elif (281.26 <= x <= 303.75) or (x == 999014):
            x = 'WNW'

        elif (303.26 <= x <= 326.75) or (x == 999015):
            x = 'NW'

        elif (326.26 <= x <= 348.75) or (x == 999016):
            x = 'NNW'

        elif x == 999017:
            x = 'C'

        elif x in [999999, 999982, 999983]: # 异常值
            x = np.nan

    except:
        x = x.upper()

    return x


@cost_time
def yearly_data_processing(yearly_data, years):
    '''
    年数据前处理
    '''
    start_date = years.split(',')[0]
    end_date = years.split(',')[1]
    if yearly_data is None or yearly_data.empty:
        return yearly_data
    df_data = yearly_data.copy()

    try:
        df_data['Datetime'] = pd.to_datetime(df_data['Datetime'])
        df_data.set_index('Datetime', inplace=True)
    except:
        pass

    df_data['Station_Id_C'] = df_data['Station_Id_C'].astype(str)

    # reindex
    dates = pd.date_range(start=start_date, end=end_date, freq='YS')
    df_new = []
    for sta in df_data['Station_Id_C'].unique():
        df_sta = df_data[df_data['Station_Id_C'] == sta]
        df_sta = df_sta[~df_sta.index.duplicated()]  # 数据去除重复
        df_sta = df_sta.reindex(dates, fill_value=np.nan)
        
        # 填充
        fillna_values = {'Station_Id_C': df_sta.loc[df_sta['Station_Id_C'].notnull(), 'Station_Id_C'][0],
                         'Station_Name': df_sta.loc[df_sta['Station_Name'].notnull(), 'Station_Name'][0]}
                        #  'Lon': df_sta.loc[df_sta['Lon'].notnull(), 'Lon'][0],
                        #  'Lat': df_sta.loc[df_sta['Lat'].notnull(), 'Lat'][0]}
        df_sta = df_sta.fillna(fillna_values)
        df_sta['Year'] = df_sta.index.year
        df_new.append(df_sta)

    df_data = pd.concat(df_new,axis=0)
    df_data['Station_Name'] = df_data['Station_Name'].apply(lambda x: x.split('国家')[0]) # 国家站站名处理

    # 各要素处理
    if 'Unnamed: 0' in df_data.columns:
        df_data.drop(['Unnamed: 0'], axis=1, inplace=True)

    if 'V12011_067' in df_data.columns:
        df_data['V12011_067'] = df_data['V12011_067'].astype(str).apply(ODay_C_process2)

    if 'V12012_067' in df_data.columns:
        df_data['V12012_067'] = df_data['V12012_067'].astype(str).apply(ODay_C_process2)

    if 'V11042_067' in df_data.columns:
        df_data['V11042_067'] = df_data['V11042_067'].astype(str).apply(ODay_C_process2)

    if 'WIN_S_INST_Max_ODate_C' in df_data.columns:
        df_data['WIN_S_INST_Max_ODate_C'] = df_data['WIN_S_INST_Max_ODate_C'].astype(str).apply(ODay_C_process2)

    if 'V13007_067' in df_data.columns:
        df_data['V13007_067'] = df_data['V13007_067'].astype(str).apply(ODay_C_process2)

    if 'EICED_Max_Odate' in df_data.columns:
        df_data['EICED_Max_Odate'] = df_data['EICED_Max_Odate'].astype(str).apply(ODay_C_process2)

    if 'PRS_Max_Odate' in df_data.columns:
        df_data['PRS_Max_Odate'] = df_data['PRS_Max_Odate'].astype(str).apply(ODay_C_process2)

    if 'PRS_Min_Odate' in df_data.columns:
        df_data['PRS_Min_Odate'] = df_data['PRS_Min_Odate'].astype(str).apply(ODay_C_process2)

    if 'V13052_067' in df_data.columns:
        df_data['V13052_067'] = df_data['V13052_067'].astype(str).apply(ODay_C_process2)

    if ('PRE_LCDays_EMon' in df_data.columns) and ('EDay_Max_Coti_PRE' in df_data.columns):
        df_data['PRE_LCDays_EMon'] = df_data['PRE_LCDays_EMon'].apply(lambda x: '999999' if pd.isnull(x) else str(int(x)))
        df_data['EDay_Max_Coti_PRE'] = df_data['EDay_Max_Coti_PRE'].apply(lambda x: '999999' if pd.isnull(x) else str(int(x)))
        df_data['最长连续降水止月日'] = df_data['PRE_LCDays_EMon'] + '月' + df_data['EDay_Max_Coti_PRE'] + '日'
        df_data['最长连续降水止月日'] = df_data['最长连续降水止月日'].astype(str).apply(ODay_C_process3)

    if ('NPRE_LCDays_EMon' in df_data.columns) and ('NPRE_LCDays_EDay' in df_data.columns):
        df_data['NPRE_LCDays_EMon'] = df_data['NPRE_LCDays_EMon'].apply(lambda x: '999999' if pd.isnull(x) else str(int(x)))
        df_data['NPRE_LCDays_EDay'] = df_data['NPRE_LCDays_EDay'].apply(lambda x: '999999' if pd.isnull(x) else str(int(x)))
        df_data['最长连续无降水止月日'] = df_data['NPRE_LCDays_EMon'] + '月' + df_data['NPRE_LCDays_EDay'] + '日'
        df_data['最长连续无降水止月日'] = df_data['最长连续无降水止月日'].astype(str).apply(ODay_C_process3)

    if ('PRE_Coti_Max_EMon' in df_data.columns) and ('PRE_Coti_Max_EDay' in df_data.columns):
        df_data['PRE_Coti_Max_EMon'] = df_data['PRE_Coti_Max_EMon'].apply(lambda x: '999999' if pd.isnull(x) else str(int(x)))
        df_data['PRE_Coti_Max_EDay'] = df_data['PRE_Coti_Max_EDay'].apply(lambda x: '999999' if pd.isnull(x) else str(int(x)))
        df_data['最大连续降水止月日'] = df_data['PRE_Coti_Max_EMon'] + '月' + df_data['PRE_Coti_Max_EDay'] + '日'
        df_data['最大连续降水止月日'] = df_data['最大连续降水止月日'].astype(str).apply(ODay_C_process3)

    if 'V12311_067' in df_data.columns:
        df_data['V12311_067'] = df_data['V12311_067'].astype(str).apply(ODay_C_process2)

    if 'V12121_067' in df_data.columns:
        df_data['V12121_067'] = df_data['V12121_067'].astype(str).apply(ODay_C_process2)

    if 'V13334_067' in df_data.columns:
        df_data['V13334_067'] = df_data['V13334_067'].astype(str).apply(ODay_C_process2)

    if 'FRS_Depth_Max_Odate' in df_data.columns:
        df_data['FRS_Depth_Max_Odate'] = df_data['FRS_Depth_Max_Odate'].astype(str).apply(ODay_C_process2)

    if 'V13334_060_C' in df_data.columns:
        df_data['V13334_060_C'] = df_data['V13334_060_C'].astype(str).apply(ODay_C_process2)

    if 'FRS_Depth_Max_ODay_C' in df_data.columns:
        df_data['FRS_Depth_Max_ODay_C'] = df_data['FRS_Depth_Max_ODay_C'].astype(str).apply(ODay_C_process2)

    if 'WIN_D_S_Max_C' in df_data.columns:
        df_data['WIN_D_S_Max_C'] = df_data['WIN_D_S_Max_C'].astype(str).apply(wind_direction_to_symbol)

    if 'WIN_D_INST_Max_C' in df_data.columns:
        df_data['WIN_D_INST_Max_C'] = df_data['WIN_D_INST_Max_C'].astype(str).apply(wind_direction_to_symbol)

    if 'WIN_D_S_Max_C' in df_data.columns:
        df_data['WIN_D_Max_C'] = df_data['WIN_D_Max_C'].astype(str).apply(wind_direction_to_symbol)

    return df_data


@cost_time
def monthly_data_processing(monthly_data, years):
    '''
    月数据前处理
    '''
    start_date = years.split(',')[0]
    end_date = years.split(',')[1]

    if monthly_data is None or monthly_data.empty:
        return monthly_data
    df_data = monthly_data.copy()

    try:
        df_data['Datetime'] = pd.to_datetime(df_data['Datetime'])
        df_data.set_index('Datetime', inplace=True)
    except:
        pass

    df_data['Station_Id_C'] = df_data['Station_Id_C'].astype(str)

    # reindex
    dates = pd.date_range(start=start_date, end=end_date, freq='MS')
    df_new = []
    for sta in df_data['Station_Id_C'].unique():
        df_sta = df_data[df_data['Station_Id_C'] == sta]
        df_sta = df_sta[~df_sta.index.duplicated()]  # 数据去除重复
        df_sta = df_sta.reindex(dates, fill_value=np.nan)
        
        # 填充
        fillna_values = {'Station_Id_C': df_sta.loc[df_sta['Station_Id_C'].notnull(), 'Station_Id_C'][0],
                         'Station_Name': df_sta.loc[df_sta['Station_Name'].notnull(), 'Station_Name'][0],
                         'Lon': df_sta.loc[df_sta['Lon'].notnull(), 'Lon'][0],
                         'Lat': df_sta.loc[df_sta['Lat'].notnull(), 'Lat'][0]}
        df_sta = df_sta.fillna(fillna_values)
        df_sta['Year'] = df_sta.index.year
        df_sta['Mon'] = df_sta.index.month
        df_new.append(df_sta)

    df_data = pd.concat(df_new,axis=0)
    df_data['Station_Name'] = df_data['Station_Name'].apply(lambda x: x.split('国家')[0]) # 国家站站名处理

    # 根据要素处理
    if 'Unnamed: 0' in df_data.columns:
        df_data.drop(['Unnamed: 0'], axis=1, inplace=True)

    if 'TEM_Max_ODay_C' in df_data.columns:
        df_data['TEM_Max_ODay_C'] = df_data['TEM_Max_ODay_C'].astype(str).apply(ODay_C_process1)

    if 'TEM_Min_ODay_C' in df_data.columns:
        df_data['TEM_Min_ODay_C'] = df_data['TEM_Min_ODay_C'].astype(str).apply(ODay_C_process1)

    if 'PRS_Max_ODay_C' in df_data.columns:
        df_data['PRS_Max_ODay_C'] = df_data['PRS_Max_ODay_C'].astype(str).apply(ODay_C_process1)

    if 'PRS_Min_ODay_C' in df_data.columns:
        df_data['PRS_Min_ODay_C'] = df_data['PRS_Min_ODay_C'].astype(str).apply(ODay_C_process1)

    if 'RHU_Min_ODay_C' in df_data.columns:
        df_data['RHU_Min_ODay_C'] = df_data['RHU_Min_ODay_C'].astype(str).apply(ODay_C_process1)

    if 'WIN_S_Max_ODay_C' in df_data.columns:
        df_data['WIN_S_Max_ODay_C'] = df_data['WIN_S_Max_ODay_C'].astype(str).apply(ODay_C_process1)

    if 'WIN_S_INST_Max_ODay_C' in df_data.columns:
        df_data['WIN_S_INST_Max_ODay_C'] = df_data['WIN_S_INST_Max_ODay_C'].astype(str).apply(ODay_C_process1)

    if 'WIN_D_S_Max_C' in df_data.columns:
        df_data['WIN_D_S_Max_C'] = df_data['WIN_D_S_Max_C'].astype(str).apply(wind_direction_to_symbol)

    if 'WIN_D_INST_Max_C' in df_data.columns:
        df_data['WIN_D_INST_Max_C'] = df_data['WIN_D_INST_Max_C'].astype(str).apply(wind_direction_to_symbol)

    if 'WIN_D_Max_C' in df_data.columns:
        df_data['WIN_D_Max_C'] = df_data['WIN_D_Max_C'].astype(str).apply(wind_direction_to_symbol)

    if 'PRE_Max_ODay_C' in df_data.columns:
        df_data['PRE_Max_ODay_C'] = df_data['PRE_Max_ODay_C'].astype(str).apply(ODay_C_process1)

    if 'EDay_Max_Coti_PRE' in df_data.columns:
        df_data['EDay_Max_Coti_PRE'] = df_data['EDay_Max_Coti_PRE'].astype(str).apply(ODay_C_process1)

    if 'NPRE_LCDays_EDay' in df_data.columns:
        df_data['NPRE_LCDays_EDay'] = df_data['NPRE_LCDays_EDay'].astype(str).apply(ODay_C_process1)

    if 'PRE_Coti_Max_EDay' in df_data.columns:
        df_data['PRE_Coti_Max_EDay'] = df_data['PRE_Coti_Max_EDay'].astype(str).apply(ODay_C_process1)

    if 'EGST_Max_ODay_C' in df_data.columns:
        df_data['EGST_Max_ODay_C'] = df_data['EGST_Max_ODay_C'].astype(str).apply(ODay_C_process1)

    if 'GST_Min_Ten_ODay_C' in df_data.columns:
        df_data['GST_Min_Ten_ODay_C'] = df_data['GST_Min_Ten_ODay_C'].astype(str).apply(ODay_C_process1)

    if 'V13334_060_C' in df_data.columns:
        df_data['V13334_060_C'] = df_data['V13334_060_C'].astype(str).apply(ODay_C_process1)

    if 'FRS_Depth_Max_ODay_C' in df_data.columns:
        df_data['FRS_Depth_Max_ODay_C'] = df_data['FRS_Depth_Max_ODay_C'].astype(str).apply(ODay_C_process1)

    if 'EICEW_Max_ODay_C' in df_data.columns:
        df_data['EICEW_Max_ODay_C'] = df_data['EICEW_Max_ODay_C'].astype(str).apply(ODay_C_process1)

    if 'PRE_Max_Day' in df_data.columns:
        df_data['PRE_Max_Day'] = df_data['PRE_Max_Day'].apply(lambda x: np.nan if x > 999 else x)

    if 'SSP_Mon' in df_data.columns:
        df_data['SSP_Mon'] = df_data['SSP_Mon'].apply(lambda x: np.nan if x > 999 else x)

    if 'FRS_Depth_Max' in df_data.columns:
        df_data['FRS_Depth_Max'] = df_data['FRS_Depth_Max'].apply(lambda x: np.nan if x > 999 else x)
    
    if 'Snow_Depth_Max' in df_data.columns:
        df_data['Snow_Depth_Max'] = df_data['Snow_Depth_Max'].apply(lambda x: np.nan if x > 999 else x)
    
    if 'RHU_Avg' in df_data.columns:
        df_data['RHU_Avg'] = df_data['RHU_Avg'].apply(lambda x: np.nan if x > 100 else x)
    
    if 'RHU_Min' in df_data.columns:
        df_data['RHU_Min'] = df_data['RHU_Min'].apply(lambda x: np.nan if x > 100 else x)
    
    if 'TEM_Avg' in df_data.columns:
        df_data['TEM_Avg'] = df_data['TEM_Avg'].apply(lambda x: np.nan if x > 999 else x)

    return df_data


@cost_time
def daily_data_processing(daily_data, years):
    '''
    日数据前处理
    '''
    start_date = years.split(',')[0]
    end_date = years.split(',')[1]

    if daily_data is None or daily_data.empty:
        return daily_data
    df_data = daily_data.copy()

    try:
        df_data['Datetime'] = pd.to_datetime(df_data['Datetime'])
        df_data.set_index('Datetime', inplace=True)
    except:
        pass

    df_data['Station_Id_C'] = df_data['Station_Id_C'].astype(str)
    
    # reindex
    dates = pd.date_range(start=start_date, end=end_date+'1231', freq='D')
    df_new = []
    for sta in df_data['Station_Id_C'].unique():
        df_sta = df_data[df_data['Station_Id_C'] == sta]
        df_sta = df_sta[~df_sta.index.duplicated()]  # 数据去除重复
        df_sta = df_sta.reindex(dates, fill_value=np.nan)
        
        # 填充
        fillna_values = {'Station_Id_C': df_sta.loc[df_sta['Station_Id_C'].notnull(), 'Station_Id_C'][0],
                         'Station_Name': df_sta.loc[df_sta['Station_Name'].notnull(), 'Station_Name'][0]}
                        #  'Lon': df_sta.loc[df_sta['Lon'].notnull(), 'Lon'][0],
                        #  'Lat': df_sta.loc[df_sta['Lat'].notnull(), 'Lat'][0]}
        df_sta = df_sta.fillna(fillna_values)
        df_sta['Year'] = df_sta.index.year
        df_sta['Mon'] = df_sta.index.month
        df_sta['Day'] = df_sta.index.day
        df_new.append(df_sta)

    df_data = pd.concat(df_new,axis=0)
    df_data['Station_Name'] = df_data['Station_Name'].apply(lambda x: x.split('国家')[0]) # 国家站站名处理

    if 'Unnamed: 0' in df_data.columns:
        df_data.drop(['Unnamed: 0'], axis=1, inplace=True)

    if 'WIN_D_S_Max' in df_data.columns:
        df_data['WIN_D_S_Max'] = df_data['WIN_D_S_Max'].astype(str).apply(wind_direction_to_symbol)
    
    if 'WIN_D_INST_Max' in df_data.columns:
        df_data['WIN_D_INST_Max'] = df_data['WIN_D_INST_Max'].astype(str).apply(wind_direction_to_symbol)

    if 'PRE_Time_2020' in df_data.columns:
        df_data['PRE_Time_2020'] = df_data['PRE_Time_2020'].map(str)
        df_data.loc[df_data['PRE_Time_2020'].str.contains('999'), 'PRE_Time_2020'] = np.nan
        df_data['PRE_Time_2020'] = df_data['PRE_Time_2020'].map(float)
    
    if 'PRS_Avg' in df_data.columns:
        df_data['PRS_Avg'] = df_data['PRS_Avg'].apply(lambda x: np.nan if x > 999 else x)
    
    if 'PRS_Max' in df_data.columns:
        df_data['PRS_Max'] = df_data['PRS_Max'].apply(lambda x: np.nan if x > 999 else x)
    
    if 'PRS_Min' in df_data.columns:
        df_data['PRS_Min'] = df_data['PRS_Min'].apply(lambda x: np.nan if x > 999 else x)
    
    if 'TEM_Avg' in df_data.columns:
        df_data['TEM_Avg'] = df_data['TEM_Avg'].apply(lambda x: np.nan if x > 999 else x)
        
    if 'TEM_Max' in df_data.columns:
        df_data['TEM_Max'] = df_data['TEM_Max'].apply(lambda x: np.nan if x > 999 else x)
    
    if 'TEM_Min' in df_data.columns:
        df_data['TEM_Min'] = df_data['TEM_Min'].apply(lambda x: np.nan if x > 999 else x)
        
    if 'WIN_S_2mi_Avg' in df_data.columns:
        df_data['WIN_S_2mi_Avg'] = df_data['WIN_S_2mi_Avg'].apply(lambda x: np.nan if x > 999 else x)

    if 'WIN_S_Max' in df_data.columns:
        df_data['WIN_S_Max'] = df_data['WIN_S_Max'].apply(lambda x: np.nan if x > 99 else x)
        
    if 'WIN_S_Inst_Max' in df_data.columns:
        df_data['WIN_S_Inst_Max'] = df_data['WIN_S_Inst_Max'].apply(lambda x: np.nan if x > 999 else x)
    
    if 'VAP_Avg' in df_data.columns:
        df_data['VAP_Avg'] = df_data['VAP_Avg'].apply(lambda x: np.nan if x > 999 else x)
        
    if 'RHU_Avg' in df_data.columns:
        df_data['RHU_Avg'] = df_data['RHU_Avg'].apply(lambda x: np.nan if x > 100 else x)

    if 'RHU_Min' in df_data.columns:
        df_data['RHU_Min'] = df_data['RHU_Min'].apply(lambda x: np.nan if x > 100 else x)
        
    if 'GST_Avg' in df_data.columns:
        df_data['GST_Avg'] = df_data['GST_Avg'].apply(lambda x: np.nan if x > 999 else x)

    if 'GST_Max' in df_data.columns:
        df_data['GST_Max'] = df_data['GST_Max'].apply(lambda x: np.nan if x > 999 else x)

    if 'GST_Min' in df_data.columns:
        df_data['GST_Min'] = df_data['GST_Min'].apply(lambda x: np.nan if x > 999 else x)
        
    if 'Snow_Depth' in df_data.columns:
        df_data['Snow_Depth'] = df_data['Snow_Depth'].apply(lambda x: np.nan if x > 999 else x)   

    return df_data


@cost_time
def hourly_data_processing(hourly_data, years):
    '''
    小时数据前处理
    '''
    start_date = years.split(',')[0]
    end_date = years.split(',')[1]

    if hourly_data is None or hourly_data.empty:
        return hourly_data
    df_data = hourly_data.copy()

    try:
        df_data['Datetime'] = pd.to_datetime(df_data['Datetime'])
        df_data.set_index('Datetime', inplace=True)
    except:
        pass
    
    df_data['Station_Id_C'] = df_data['Station_Id_C'].astype(str)

    # reindex
    dates = pd.date_range(start=start_date, end=end_date, freq='h')
    df_new = []
    for sta in df_data['Station_Id_C'].unique():
        df_sta = df_data[df_data['Station_Id_C'] == sta]
        df_sta = df_sta[~df_sta.index.duplicated()]  # 数据去除重复
        df_sta = df_sta.reindex(dates, fill_value=np.nan)
        
        # 填充
        fillna_values = {'Station_Id_C': df_sta.loc[df_sta['Station_Id_C'].notnull(), 'Station_Id_C'][0],
                         'Station_Name': df_sta.loc[df_sta['Station_Name'].notnull(), 'Station_Name'][0]}
                        #  'Lon': df_sta.loc[df_sta['Lon'].notnull(), 'Lon'][0],
                        #  'Lat': df_sta.loc[df_sta['Lat'].notnull(), 'Lat'][0]}
        df_sta = df_sta.fillna(fillna_values)
        df_sta['Year'] = df_sta.index.year
        df_sta['Mon'] = df_sta.index.month
        df_sta['Day'] = df_sta.index.day
        df_sta['Hour'] = df_sta.index.hour
        df_new.append(df_sta)

    df_data = pd.concat(df_new,axis=0)
    df_data['Station_Name'] = df_data['Station_Name'].apply(lambda x: x.split('国家')[0]) # 国家站站名处理

    if 'Unnamed: 0' in df_data.columns:
        df_data.drop(['Unnamed: 0'], axis=1, inplace=True)

    if 'WIN_D_Avg_2mi' in df_data.columns:
        df_data['WIN_D_Avg_2mi'] = df_data['WIN_D_Avg_2mi'].astype(str).apply(wind_direction_to_symbol)

    # if 'WIN_D_Avg_10mi' in df_data.columns:
    #     df_data['WIN_D_Avg_10mi'] = df_data['WIN_D_Avg_10mi'].astype(str).apply(wind_direction_to_symbol)

    if 'WIN_D_S_Max' in df_data.columns:
        df_data['WIN_D_S_Max'] = df_data['WIN_D_S_Max'].astype(str).apply(wind_direction_to_symbol)

    if 'PRE_1h' in df_data.columns:
        df_data['PRE_1h'] = df_data['PRE_1h'].where(df_data['PRE_1h'] < 9999, 0)

    if 'V14311' in df_data.columns:
        df_data['V14311'] = df_data['V14311'].apply(lambda x: np.nan if x > 999 else x)

    if 'RHU' in df_data.columns:
        df_data['RHU'] = df_data['RHU'].apply(lambda x: np.nan if x > 100 else x)
    
    if 'TEM' in df_data.columns:
        df_data['TEM'] = df_data['TEM'].apply(lambda x: np.nan if x > 999 else x)
        
    # 处理为世界时
    df_data.index += pd.Timedelta(hours=8)
    # df_data = df_data[df_data.index.year<=end_year]

    return df_data


def database_data_processing_module01(df, self_built_elements):
    '''
    数据库读取的数据格式处理，用于module01的计算
    '''
    self_built_elements = self_built_elements.split(',')
    meteo_elements = ['tem_avg', 'tem_max', 'tem_min', 'rhu', 'prs', 'pre']  # module01完整的气象要素（只有一个高度）
    diff_h_elements = ['min10_ws', 'tem']  # module01完整的不同高度层的要素

    # 取两个列表交集
    cur_meteo = ['year', 'month', 'day', 'hour'] + list(set(self_built_elements) & set(meteo_elements))
    cur_diff_h_elements = ['year', 'month', 'day', 'hour'] + list(set(self_built_elements) & set(diff_h_elements))

    data_meteo = df.loc[df['height'] == df['height'].unique()[0], cur_meteo]
    data_meteo['Datetime'] = pd.to_datetime(data_meteo['year'].map(str) + '-' + data_meteo['month'].map(str) + '-' + data_meteo['day'].map(str) + '-' + data_meteo['hour'].map(str),
                                            format='%Y-%m-%d-%H')
    data_meteo.set_index('Datetime', inplace=True)
    data_meteo = data_meteo.iloc[4:, :]  # 去掉年月日小时
    data_meteo.dropna(how='any', inplace=True)  # 暂时这么处理一下，目前数据库数据有问题

    for i, group in enumerate(list(df.groupby('height'))):
        h = group[0]
        group_df = group[1]
        group_df.dropna(how='any', inplace=True)  # 暂时这么处理一下，目前数据库数据有问题

        group_df = group_df[cur_diff_h_elements]
        group_df = group_df.rename(columns={'min10_ws': str(h) + 'm_min10_ws', 'tem': str(h) + 'm_tem'})

        if i == 0:
            wind_tem = group_df
        else:
            wind_tem = pd.merge(wind_tem, group_df, on=['year', 'month', 'day', 'hour'])

    wind_tem['Datetime'] = pd.to_datetime(wind_tem['year'].map(str) + '-' + wind_tem['month'].map(str) + '-' + wind_tem['day'].map(str) + '-' + wind_tem['hour'].map(str), format='%Y-%m-%d-%H')
    wind_tem.set_index('Datetime', inplace=True)
    data_wind_tem = wind_tem[wind_tem.filter(like='m_').columns]
    data = pd.concat([data_meteo, data_wind_tem], axis=1)

    return data


# from Utils.data_loader import get_data_postgresql
# self_built_elements = 'tem,tem_avg'
# df = get_data_postgresql(sta_id='Z0001', time_range='2002,2003',use='module01',module01_elements=self_built_elements)
# post_sub_df = database_data_processing_module01(df, self_built_elements)
# tem_columns = list(post_sub_df.filter(like='m_tem').columns)


def database_data_processing(df):
    '''
    数据库读取的数据格式处理，用于module04_new的计算
    '''
    data_meteo = df.loc[df['height'] == df['height'].unique()[0], ['year', 'month', 'day', 'hour', 'tem_avg', 'tem_max', 'tem_min', 'rhu', 'prs', 'pre']]
    data_meteo['Datetime'] = pd.to_datetime(data_meteo['year'].map(str) + '-' + data_meteo['month'].map(str) + '-' + data_meteo['day'].map(str) + '-' + data_meteo['hour'].map(str),
                                            format='%Y-%m-%d-%H')
    data_meteo.set_index('Datetime', inplace=True)
    data_meteo = data_meteo[['tem_avg', 'tem_max', 'tem_min', 'rhu', 'prs', 'pre']]

    for i, group in enumerate(list(df.groupby('height'))):
        h = group[0]
        group_df = group[1]
        group_df = group_df[['year', 'month', 'day', 'hour', 'min10_ws', 'sec3_ws']]
        group_df = group_df.rename(columns={'min10_ws': str(h) + 'm_min10_ws', 'sec3_ws': str(h) + 'm_sec3_ws'})

        if i == 0:
            wind = group_df

        else:
            wind = pd.merge(wind, group_df, on=['year', 'month', 'day', 'hour'])

    wind['Datetime'] = pd.to_datetime(wind['year'].map(str) + '-' + wind['month'].map(str) + '-' + wind['day'].map(str) + '-' + wind['hour'].map(str), format='%Y-%m-%d-%H')
    wind.set_index('Datetime', inplace=True)

    data_10min_wind = wind[wind.filter(like='min10').columns]
    data_3s_wind = wind[wind.filter(like='sec3').columns]

    return data_meteo, data_10min_wind, data_3s_wind


# from Utils.data_loader import get_data_postgresql
# df = get_data_postgresql(sta_id='Z0001',time_range='2000,2020', use='module04')
# data_meteo, data_10min_wind, data_3s_wind = database_data_processing(df)