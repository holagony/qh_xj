import os
import uuid
import numpy as np
import pandas as pd
from collections import OrderedDict
from Module00.wrapped.check import check
from Module14.wrapped.key_frs_statistics import key_frs_statistics
from Module14.wrapped.key_pre_statistics import key_pre_statistics
from Module14.wrapped.key_snow_statistics import key_snow_statistics
from Module14.wrapped.key_tem_statistics import key_tem_statistics
from Module14.wrapped.key_wind_statistics import key_wind_statistics

from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_processing import yearly_data_processing, monthly_data_processing, daily_data_processing
from Utils.get_url_path import get_url_path
from Utils.get_local_data import get_local_data
from Utils.data_loader_with_threads import get_cmadaas_yearly_data, get_cmadaas_monthly_data, get_cmadaas_daily_data
from Report.code.Module02.wind import win_report
from Utils.get_url_path import save_cmadaas_data
from docx import Document
from docxcompose.composer import Composer

def feature_stats_handler(data_json):
    '''
    关键气象条件分析组件
    '''
    result_dict = edict()

    # 1.读取参数
    years = data_json.get('years')
    sta_ids = data_json.get('station_ids')
    if sta_ids is None:
        sta_ids = data_json.get('station_id')
    sub_sta_ids = data_json.get('sub_sta_ids')
    elements = data_json.get('elements')
    if years is None or not isinstance(years, str) or ',' not in years:
        raise Exception('缺少或格式错误的 years，需形如 YYYY,YYYY')
    if sta_ids is None or (isinstance(sta_ids, str) and len(sta_ids.strip()) == 0):
        raise Exception('缺少 station_ids 或 station_id')

    # 2.参数处理
    if isinstance(elements, str):
        elements = [e.strip() for e in elements.split(',') if e.strip()]
    if isinstance(elements, list):
        elements = [str(e).strip() for e in elements if str(e).strip()]

    uuid4 = uuid.uuid4().hex
    result_dict['uuid'] = uuid4
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)
    
    if isinstance(sta_ids, list):
        sta_ids = [str(ids).strip() for ids in sta_ids if str(ids).strip()]
        sta_ids = ','.join(sta_ids)
    elif isinstance(sta_ids, int):
        sta_ids = str(sta_ids)
    elif isinstance(sta_ids, str):
        sta_ids = ','.join([s.strip() for s in sta_ids.split(',') if s.strip()])
    
    if sub_sta_ids is not None:
        if isinstance(sub_sta_ids, list):
            sub_sta_ids = [str(ids).strip() for ids in sub_sta_ids if str(ids).strip()]
            sub_sta_ids = ','.join(sub_sta_ids)
        elif isinstance(sub_sta_ids, int):
            sub_sta_ids = str(sub_sta_ids)
        elif isinstance(sub_sta_ids, str):
            sub_sta_ids = ','.join([s.strip() for s in sub_sta_ids.split(',') if s.strip()])
        parts = [p for p in sta_ids.split(',') if p]
        sub_parts = [p for p in sub_sta_ids.split(',') if p]
        seen = set()
        merged = []
        for p in parts + sub_parts:
            if p and p not in seen:
                merged.append(p)
                seen.add(p)
        all_sta_ids = ','.join(merged)

    # 3.拼接需要下载的参数
    # yearly_elements = ''
    # monthly_elements = ''
    # yearly_df = None
    # monthly_df = None
    daily_elements = ''
    daily_df = None

    for ele in elements:
        if ele == 'TEM':
            # yearly_elements += 'TEM_Avg,TEM_Max_Avg,TEM_Min_Avg,TEM_Max,V12011_067,TEM_Min,V12012_067,'
            # onthly_elements += 'TEM_Avg,TEM_Max,TEM_Min,TEM_Max_Avg,TEM_Min_Avg,TEM_Max_ODay_C,TEM_Min_ODay_C,'
            daily_elements += 'TEM_Max,TEM_Min,'

        elif ele == 'WIND':
            # yearly_elements += 'WIN_S_2mi_Avg,WIN_S_Max,WIN_D_S_Max_C,V11042_067,WIN_S_Inst_Max,WIN_D_INST_Max_C,WIN_S_INST_Max_ODate_C,WIN_D_Max_C,WIN_D_Max_Freq,'
            # 检查青海和新疆，如：WIN_S_AVG_W 和 WIN_S_Avg__W
            # monthly_elements += 'WIN_S_2mi_Avg,WIN_S_Max,WIN_S_Max_ODay_C,WIN_S_Inst_Max,WIN_S_INST_Max_ODay_C,'
            daily_elements += 'WIN_S_Max,WIN_S_Inst_Max,'

        elif ele == 'PRE':
            # yearly_elements += 'PRE_Time_2020,PRE_Max_Day,V13052_067,PRE_A0p1mm_Days,PRE_A10mm_Days,PRE_A25mm_Days,PRE_A50mm_Days,PRE_A100mm_Days,PRE_A150mm_Days,Days_Max_Coti_PRE,PRE_Conti_Max,PRE_LCDays_EMon,EDay_Max_Coti_PRE,NPRE_LCDays,NPRE_LCDays_EMon,NPRE_LCDays_EDay,PRE_Max_Conti,Days_Max_Conti_PRE,PRE_Coti_Max_EMon,PRE_Coti_Max_EDay,'
            # monthly_elements += 'PRE_Time_2020,PRE_Max_Day,PRE_Max_ODay_C,PRE_A0p1mm_Days,PRE_A10mm_Days,PRE_A25mm_Days,PRE_A50mm_Days,PRE_A100mm_Days,PRE_A150mm_Days,Days_Max_Coti_PRE,PRE_Conti_Max,EDay_Max_Coti_PRE,NPRE_LCDays,NPRE_LCDays_EDay,PRE_Max_Conti,Days_Max_Conti_PRE,PRE_Coti_Max_EDay,'
            daily_elements += 'PRE_Time_2020,'
            
        elif ele == 'SNOW':
            # yearly_elements += 'Snow_Depth_Max,V13334_067,'
            # monthly_elements += 'Snow_Depth_Max,V13334_060_C,'
            daily_elements += 'Snow_Depth,'
        
        elif ele == 'FRS':
            # monthly_elements += 'FRS_Depth_Max,'
            daily_elements += 'FRS_1st_Bot,FRS_2nd_Bot,'
            
    # 4.数据获取
    if cfg.INFO.READ_LOCAL:
        # year_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,' + yearly_elements[:-1]).split(',')
        # month_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,' + monthly_elements[:-1]).split(',')
        day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements[:-1]).split(',')
        daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
        # monthly_df = pd.read_csv(cfg.FILES.QH_DATA_MONTH, low_memory=False)

        if 'SNOW' in elements:
            daily_df['Snow_Depth'] = 20

        daily_df = get_local_data(daily_df, all_sta_ids, day_eles, years, 'Day')
        # monthly_df = get_local_data(monthly_df, sta_ids, month_eles, years, 'Month')
    else:
        # 天擎数据下载 and 数据前处理
        try:
            # monthly_df = get_cmadaas_monthly_data(years, monthly_elements, sta_ids)
            # monthly_df = monthly_data_processing(monthly_df, years)
            daily_df = get_cmadaas_daily_data(years, daily_elements, all_sta_ids)
            daily_df = daily_data_processing(daily_df, years)
        except Exception as e:
            raise Exception('天擎数据下载或处理失败')

    # 5.计算之前先检测数据完整率 check h小时 D天 MS月 YS年
    years = years.split(',')
    result_dict.check_result = edict()
    
    # 移除末尾逗号并过滤空字符串
    # if yearly_elements.endswith(','):
    #     yearly_elements = yearly_elements[:-1]
    # if monthly_elements.endswith(','):
    #     monthly_elements = monthly_elements[:-1]
    if daily_elements.endswith(','):
        daily_elements = daily_elements[:-1]
    
    # if yearly_df is not None and len(yearly_df) != 0 and 'VAPOR' not in elements:
    #     yearly_element_list = [e.strip() for e in yearly_elements.split(',') if e.strip()]
    #     checker = check(yearly_df, 'YS', yearly_element_list, [sta_ids], years[0], years[1])
    #     check_result = checker.run()
    #     result_dict.check_result['使用的天擎年要素'] = check_result

    # if monthly_df is not None and len(monthly_df) != 0:
    #     monthly_element_list = [e.strip() for e in monthly_elements.split(',') if e.strip()]
    #     if monthly_element_list:  # 只有当列表不为空时才进行检查
    #         checker = check(monthly_df, 'MS', monthly_element_list, [sta_ids], years[0], years[1])
    #         check_result = checker.run()
    #         result_dict.check_result['使用的天擎月要素'] = check_result

    if daily_df is not None and len(daily_df) != 0:
        daily_element_list = [e.strip() for e in daily_elements.split(',') if e.strip()]
        if daily_element_list:  # 只有当列表不为空时才进行检查
            checker = check(daily_df, 'D', daily_element_list, [sta_ids], years[0], years[1])
            check_result = checker.run()
            result_dict.check_result['使用的天擎日要素'] = check_result

    # 6.结果生成
    result_path = []

    df_main = daily_df[daily_df['Station_Id_C'].isin(parts)]
    df_sub = daily_df[daily_df['Station_Id_C'].isin(sub_parts)]

    for ele in elements:
        if ele == 'TEM':
            result_dict.temperature = edict()
            result = key_tem_statistics(df_main, df_sub)
            result_dict['TEM'] = result
            try:
                report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                result_path.append(report_path)
                result_dict['TEM']['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
            except:
                result_dict['TEM']['report'] = None

        elif ele == 'WIND':
            result = key_wind_statistics(df_main, df_sub)
            result_dict['WIND'] = result
            try:
                report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                result_path.append(report_path)
                result_dict['WIND']['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
            except:
                result_dict['WIND']['report'] = None

        elif ele == 'PRE':
            result = key_pre_statistics(df_main, df_sub)
            result_dict['PRE'] = result
            try:
                report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                result_path.append(report_path)
                result_dict['PRE']['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
            except:
                result_dict['PRE']['report'] = None

        elif ele == 'SNOW':
            result = key_snow_statistics(df_main, df_sub)
            result_dict['SNOW'] = result
            try:
                report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                result_path.append(report_path)
                result_dict['SNOW']['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
            except:
                result_dict['SNOW']['report'] = None

        elif ele == 'FRS':
            result = key_frs_statistics(df_main, df_sub)
            result_dict['FRS'] = result
            try:
                report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                result_path.append(report_path)
                result_dict['FRS']['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
            except:
                result_dict['FRS']['report'] = None

    if len(result_path) == 0:
        result_dict['report'] = None
    else:
        try:
            new_docx_path = os.path.join(data_dir, 'weather_phenomena_days.docx')
            master = Document(result_path[0])
            middle_new_docx = Composer(master)
            for word in result_path[1:]:  # 从第二个文档开始追加
                word_document = Document(word)
                middle_new_docx.append(word_document)
            middle_new_docx.save(new_docx_path)
            new_docx_path = new_docx_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
            result_dict['report'] = new_docx_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)

        except Exception as e:
            print(f"发生错误：{e}")
            result_dict['report'] = None
            
    # 6.结果保存
    if cfg.INFO.SAVE_RESULT:
        result_dict['csv'] = save_cmadaas_data(data_dir, day_data=daily_df)

    return result_dict

if __name__=='__main__':
    
    data_json={
  "years": "1985,2009",
  "station_ids": "52754",
  "sub_sta_ids": "52863",
  "elements": ["TEM","WIND","PRE","FRS","SNOW"],
  "id": "uuid",
  "is_async": 0,
  "staValueName": [
    "青海省",
    "海北藏族自治州",
    "刚察县",
    "52754"
  ],
  "stationName": "刚察_52754",
  "staValue": "国家站"
}
    
    
    a=feature_stats_handler(data_json)
