import pandas as pd
import numpy as np

path1 = r'C:/Users/mjynj/Desktop/闪电数据/闪电数据/2012-2023闪电资料.xlsx'
df_2012_2021 = pd.read_excel(path1,sheet_name='2012-2021')

# 清理数据中的中文字符，确保日期时间列都是数字格式
df_2012_2021['年'] = df_2012_2021['年'].astype(str).str.replace(r'[^0-9]', '', regex=True).astype(int)
df_2012_2021['月'] = df_2012_2021['月'].astype(str).str.replace(r'[^0-9]', '', regex=True).astype(int)
df_2012_2021['日'] = df_2012_2021['日'].astype(str).str.replace(r'[^0-9]', '', regex=True).astype(int)

# 处理HOUR列，可能包含AABBCC格式（AA小时BB分钟CC秒）
df_2012_2021['HOUR_str'] = df_2012_2021['HOUR'].astype(str).str.replace(r'[^0-9]', '', regex=True)

# 先处理MINUTE和SECOND列的原始数据
df_2012_2021['MINUTE'] = df_2012_2021['MINUTE'].astype(str).str.replace(r'[^0-9\.]', '', regex=True)
df_2012_2021['MINUTE'] = df_2012_2021['MINUTE'].replace('', '0').replace('nan', '0')
df_2012_2021['SECOND'] = df_2012_2021['SECOND'].astype(str).str.replace(r'[^0-9\.]', '', regex=True)
df_2012_2021['SECOND'] = df_2012_2021['SECOND'].replace('', '0').replace('nan', '0')

# 检查HOUR列是否为6位数格式（AABBCC）
def parse_time_columns(row):
    hour_str = str(row['HOUR_str']).strip()
    minute_str = str(row['MINUTE']).strip()
    second_str = str(row['SECOND']).strip()
    
    # 如果HOUR是6位数且MINUTE和SECOND都是0，则解析AABBCC格式
    if len(hour_str) == 6 and minute_str in ['0', '0.0'] and second_str in ['0', '0.0']:
        try:
            hour = int(hour_str[:2])
            minute = int(hour_str[2:4])
            second = int(hour_str[4:6])
        except ValueError:
            hour, minute, second = 0, 0, 0
    else:
        # 否则按原来的方式处理
        try:
            hour = int(float(hour_str)) if hour_str and hour_str != 'nan' else 0
            minute = int(float(minute_str)) if minute_str and minute_str != 'nan' else 0
            second = int(float(second_str)) if second_str and second_str != 'nan' else 0
        except ValueError:
            hour, minute, second = 0, 0, 0
    
    # 确保时间值在合理范围内
    hour = max(0, min(23, hour))
    minute = max(0, min(59, minute))
    second = max(0, min(59, second))
    
    return pd.Series([hour, minute, second])

# 应用时间解析函数
df_2012_2021[['HOUR', 'MINUTE', 'SECOND']] = df_2012_2021.apply(parse_time_columns, axis=1)

# 删除临时列
df_2012_2021= df_2012_2021.drop('HOUR_str', axis=1)

# 构建日期时间字符串，确保格式正确
df_2012_2021['Datetime'] = (df_2012_2021['年'].astype(str) + '-' + 
                           df_2012_2021['月'].astype(str).str.zfill(2) + '-' + 
                           df_2012_2021['日'].astype(str).str.zfill(2) + ' ' + 
                           df_2012_2021['HOUR'].astype(str).str.zfill(2) + ':' + 
                           df_2012_2021['MINUTE'].astype(str).str.zfill(2) + ':' + 
                           df_2012_2021['SECOND'].astype(str).str.zfill(2))
df_2012_2021['Datetime'] = pd.to_datetime(df_2012_2021['Datetime'], errors='coerce')

df_2012_2021 = df_2012_2021[['LATITUDE', 'LONGITUDE', 'Datetime', 'PROVINCE', 'DISTRICT', 'COUNTRY']]
df_2012_2021.columns = ['Lat', 'Lon', 'Datetime', '省', '市', '县']
# df_2012_2021.to_csv('C:/Users/mjynj/Desktop/2012_2021.csv', index=False, encoding='utf-8-sig')

# 读取2022和2023年的数据
path1 = r'C:/Users/mjynj/Desktop/闪电数据/闪电数据/2012-2023闪电资料.xlsx'
df_2022 = pd.read_excel(path1,sheet_name='2022')
df_2022 = df_2022[['LATITUDE', 'LONGITUDE', 'LNTIME', 'PROVINCE', 'DISTRICT', 'COUNTRY', 'INTENS']]
df_2022.columns = ['Lat', 'Lon', 'Datetime', '省', '市', '县', '强度']

df_2023 = pd.read_excel(path1,sheet_name='2023')
df_2023 = df_2023[['纬度', '经度', '时间', '省', '市', '县', '强度(KA)']]
df_2023.columns = ['Lat', 'Lon', 'Datetime', '省', '市', '县', '强度']

path = r'C:/Users/mjynj/Desktop/闪电数据/闪电数据/2024-1-12.csv'
df_2024 = pd.read_csv(path, encoding='gbk')
df_2024 = df_2024[['纬度', '经度', '时间', '省', '市', '县', '强度(KA)']]
df_2024.columns = ['Lat', 'Lon', 'Datetime', '省', '市', '县', '强度']

df_2022_2024 = pd.concat([df_2022,df_2023, df_2024],axis=0)
# df_2022_2024.to_csv('C:/Users/mjynj/Desktop/2022_2024.csv', index=False, encoding='utf-8-sig')


# In[]
df_2012_2021['强度'] = np.nan
df_all = pd.concat([df_2012_2021,df_2022_2024], axis=0)
df_all = df_all[['Lat', 'Lon', 'Datetime', '市', '县', '强度']]

# In[]
df_all.to_csv('C:/Users/mjynj/Desktop/adtd_xj.csv', index=False, encoding='utf-8-sig')













