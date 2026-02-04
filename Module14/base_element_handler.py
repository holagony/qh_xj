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
from Utils.get_url_path import save_cmadaas_data

from Report.code.Module14.wind import win_report
from Report.code.Module14.tem import tem_report
from Report.code.Module14.pre import pre_report
from Report.code.Module14.snow import snow_report
from Report.code.Module14.frs import frs_report

from docx import Document
from docxcompose.composer import Composer


def convert_nested_df(data):
    if isinstance(data, dict):
        return {k: convert_nested_df(v) for k, v in data.items()}
    elif isinstance(data, pd.DataFrame):
        return data.to_dict(orient='records')
    elif isinstance(data, pd.Series):
        return data.to_frame().T.round(1).to_dict(orient='records')
    else:
        return data

    
def feature_stats_handler(data_json):
    '''
    关键气象条件分析组件
    '''
    result_dict = edict()

    # 1.读取参数
    years = data_json.get('years')
    sta_ids = data_json.get('station_ids')
    sub_sta_ids = data_json.get('sub_sta_ids')
    elements = data_json.get('elements')
    if years is None or not isinstance(years, str) or ',' not in years:
        raise Exception('缺少或格式错误的 years，需形如 YYYY,YYYY')
    if sta_ids is None or (isinstance(sta_ids, str) and len(sta_ids.strip()) == 0):
        raise Exception('缺少 station_ids 或 station_id')
    sub_sta_ids = None if sub_sta_ids == '' else sub_sta_ids

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

    if sub_sta_ids is not None:
        if isinstance(sub_sta_ids, list):
            sub_sta_ids = [str(ids).strip() for ids in sub_sta_ids if str(ids).strip()]
            sub_sta_ids = ','.join(sub_sta_ids)
        elif isinstance(sub_sta_ids, int):
            sub_sta_ids = str(sub_sta_ids)
            
        all_sta_ids = sta_ids + ',' + sub_sta_ids
    else:
        all_sta_ids = sta_ids

    # 3.拼接需要下载的参数
    daily_elements = ''
    daily_df = None

    for ele in elements:
        if ele == 'TEM':
            daily_elements += 'TEM_Max,TEM_Min,'

        elif ele == 'WIND':
            daily_elements += 'WIN_S_Max,WIN_S_Inst_Max,'

        elif ele == 'PRE':
            daily_elements += 'PRE_Time_2020,'
            
        elif ele == 'SNOW':
            daily_elements += 'Snow_Depth,'
        
        elif ele == 'FRS':
            daily_elements += 'FRS_1st_Bot,FRS_2nd_Bot,'
            
    # 4.数据获取
    if cfg.INFO.READ_LOCAL:
        day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements[:-1]).split(',')
        daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)

        if 'SNOW' in elements:
            daily_df['Snow_Depth'] = 20

        daily_df = get_local_data(daily_df, all_sta_ids, day_eles, years, 'Day')
    else:
        # 天擎数据下载 and 数据前处理
        try:

            daily_df = get_cmadaas_daily_data(years, daily_elements, all_sta_ids)
            daily_df = daily_data_processing(daily_df, years)
        except Exception as e:
            raise Exception('天擎数据下载或处理失败')

    # 5.计算之前先检测数据完整率 check h小时 D天 MS月 YS年
    years = years.split(',')
    result_dict.check_result = edict()
    
    if daily_elements.endswith(','):
        daily_elements = daily_elements[:-1]
    


    if daily_df is not None and len(daily_df) != 0:
        daily_element_list = [e.strip() for e in daily_elements.split(',') if e.strip()]
        if daily_element_list:  # 只有当列表不为空时才进行检查
            checker = check(daily_df, 'D', daily_element_list, [sta_ids], years[0], years[1])
            check_result = checker.run()
            result_dict.check_result['使用的天擎日要素'] = check_result

    # 6.结果生成
    result_path = []
    for ele in elements:
        if ele == 'TEM':
            result = key_tem_statistics(daily_df)
            result_dict['TEM'] = result
            try:
                report_path=tem_report(years,sta_ids,sub_sta_ids,daily_df,result,data_dir)
                result_path.append(report_path)
                report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                result_dict['TEM']['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
            except:
                result_dict['TEM']['report'] = None

        elif ele == 'WIND':
            result = key_wind_statistics(daily_df)
            result_dict['WIND'] = result
            try:
                report_path=win_report(years,sta_ids,sub_sta_ids,daily_df,result,data_dir)
                result_path.append(report_path)
                report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                result_dict['WIND']['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
            except:
                result_dict['WIND']['report'] = None

        elif ele == 'PRE':
            result = key_pre_statistics(daily_df)
            result_dict['PRE'] = result
            try:
                report_path=pre_report(years,sta_ids,sub_sta_ids,daily_df,result,data_dir)
                result_path.append(report_path)
                report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                result_dict['PRE']['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
            except:
                result_dict['PRE']['report'] = None

        elif ele == 'SNOW':
            result = key_snow_statistics(daily_df)
            result_dict['SNOW'] = result
            try:
                report_path=snow_report(years,sta_ids,sub_sta_ids,daily_df,result,data_dir)
                result_path.append(report_path)
                report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                result_dict['SNOW']['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
            except:
                result_dict['SNOW']['report'] = None

        elif ele == 'FRS':
            result = key_frs_statistics(daily_df)
            result_dict['FRS'] = result
            try:
                report_path=frs_report(years,sta_ids,sub_sta_ids,daily_df,result,data_dir)
                result_path.append(report_path)
                report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                result_dict['FRS']['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
            except:
                result_dict['FRS']['report'] = None

    if len(result_path) == 0:
        result_dict['report'] = None
    else:
        try:
            new_docx_path = os.path.join(data_dir, 'base_element.docx')
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
    
    result_dict = convert_nested_df(result_dict)

    return result_dict

if __name__=='__main__':
    
    data_json={
  "years": "1985,2009",
  "station_ids": "52866",
  "sub_sta_ids": "",
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
    
    
    b=feature_stats_handler(data_json)
