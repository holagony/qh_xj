import os
import json
import logging
import uuid
import simplejson
import numpy as np
import pandas as pd
from collections import OrderedDict
from flask import Blueprint, request, jsonify
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_loader_with_threads import get_cmadaas_daily_data
from Utils.data_processing import daily_data_processing
from Utils.get_local_data import get_local_data
from Module00.wrapped.check import check
from Module06.wrapped.climate_livable import calc_climate_livable_factors
from Module06.wrapped.climate_disadvantage import calc_climate_disadvantage_factors
from Module06.wrapped.climate_comfort_new import climate_comfort_main
from Report.code.Module06.climate_1 import climate_1_report
from Report.code.Module06.climate_2 import climate_2_report
from Report.code.Module06.climate_comfort_report import climate_comfort_report
from Report.code.Module06.climate_disadvantage_report import climate_disadvantage_report
from Report.code.Module06.climate_livable_report import climate_livable_report
from docx import Document
from docxcompose.composer import Composer

def calc_climate_assessment(data_json):
    '''
    完整的气候宜居评估入口
    '''
    # data_json = json.loads(json_str)
    years = data_json['years']
    sta_ids = data_json['station_ids']
    elements = data_json['elements']

    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    # 2.参数处理
    if isinstance(years, dict):  # 支持dict
        years = list(years.values())
        years.sort()

    if isinstance(sta_ids, list):
        sta_ids = [str(ids) for ids in sta_ids]
        sta_ids = ','.join(sta_ids)
    if isinstance(sta_ids, int):
        sta_ids = str(sta_ids)

    if isinstance(elements, str):  # 支持str
        elements = elements.split(',')

    if len(elements) == 0:
        raise Exception('必须要选择计算的气候宜居的子类别')

    # 3.参数直接预设好
    daily_elements = 'PRS_Avg,TEM_Avg,TEM_Max,TEM_Min,RHU_Avg,RHU_Min,PRE_Time_2020,WIN_S_2mi_Avg,SSH,CLO_Cov_Avg,WIN_S_Max,FlSa,SaSt,Haze,Hail,Thund,Tord,Squa'

    # 4.数据获取
    if cfg.INFO.READ_LOCAL:
        day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements).split(',')
        daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
        daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')
        daily_df['RHU_Avg'] = daily_df['RHU_Avg'] / 100
        daily_df['RHU_Min'] = daily_df['RHU_Min'] / 100
    else:
        try:
            daily_df = get_cmadaas_daily_data(years, daily_elements, sta_ids)
            daily_df = daily_data_processing(daily_df, years)
            daily_df['RHU_Avg'] = daily_df['RHU_Avg'] / 100
            daily_df['RHU_Min'] = daily_df['RHU_Min'] / 100
        except Exception as e:
            logging.exception(e)
            raise Exception('天擎数据获取失败')

    # 5.生成结果
    try:
        result_dict = edict()
        result_dict['uuid'] = uuid4
        report_pathz=[]
        # report_pathz.append(os.path.join(cfg['report']['template'],'Module05','freezing_and_thawing_1.docx'))
        # module00完整率统计
        years_split = years.split(',')
        result_dict.check_result = edict()
        if daily_df is not None and len(daily_df) != 0:
            checker = check(daily_df, 'D', daily_elements.split(','), [sta_ids], years_split[0], years_split[1])
            result_dict.check_result['使用的天擎日要素'] = checker.run()
    
        # 计算结果
        columns1 = ['TEM_Max', 'TEM_Min', 'PRE_Time_2020', 'WIN_S_Max', 'WIN_S_2mi_Avg', 'PRS_Avg', 'TEM_Avg', 'RHU_Avg', 'RHU_Min', 'SSH', 'CLO_Cov_Avg']
        columns2 = ['Hail', 'Tord', 'SaSt', 'FlSa', 'Haze', 'Thund', 'Squa']        
        daily_df[columns1] = daily_df[columns1].interpolate(method='linear', axis=0)  # 缺失值线性插值填充
        daily_df[columns1] = daily_df[columns1].fillna(method='bfill')  # 填充后一条数据的值，但是后一条也不一定有值
        daily_df[columns2] = daily_df[columns2].fillna(0)
        
        
        try :
            path=climate_1_report(daily_df,data_dir)
            report_pathz.append(path)
        except:
            pass
        
        table_list = []
        for ele in elements:
            if ele == 'livable':
                climate_livable_dict = calc_climate_livable_factors(daily_df)  # 宜居结果
                result_dict['气候宜居禀赋'] = climate_livable_dict
    
                livable_level = climate_livable_dict.assessments.level  # 评价等级表
                livable_level = pd.DataFrame(livable_level)
                table_list.append(livable_level)
                
                
                try :
                    path=climate_livable_report(climate_livable_dict,daily_df,data_dir)
                    report_pathz.append(path)
                except:
                    pass
                
    
            elif ele == 'disadvantage':
                climate_disadvantage_dict = calc_climate_disadvantage_factors(daily_df)  # 气候不利条件结果
                result_dict['气候不利条件'] = climate_disadvantage_dict
    
                disadvantage_level = climate_disadvantage_dict.assessments.level  # 评价等级表
                disadvantage_level = pd.DataFrame(disadvantage_level)
                table_list.append(disadvantage_level)
                
                try :
                    path= climate_disadvantage_report(climate_disadvantage_dict,daily_df,data_dir)
                    report_pathz.append(path)
                except:
                    pass
    
            elif ele == 'comfort_new':
                climate_comfort_dict = climate_comfort_main(daily_df)  # 气候舒适性结果
                result_dict['气候舒适度'] = climate_comfort_dict
    
                comfort_level = climate_comfort_dict.assessments.level  # 评价等级表
                comfort_level = pd.DataFrame(comfort_level)
                table_list.append(comfort_level)
                
                try :
                    path= climate_comfort_report(climate_comfort_dict,daily_df,data_dir)
                    report_pathz.append(path)
                except:
                    pass
    
        if 'assessment' in elements:
            if len(table_list) != 0:
                total_level = pd.concat(table_list, axis=0).reset_index(drop=True)
                try :
                    path= climate_2_report(total_level,data_dir)
                    report_pathz.append(path)
                except:
                    pass
            
                result_dict['气候宜居评价表'] = total_level.to_dict(orient='records')
            else:
                result_dict['气候宜居评价表'] = None
                
                
        try:
            new_docx_path=os.path.join(data_dir,'climate.docx')
            master = Document(report_pathz[0])
            middle_new_docx = Composer(master)
            for word in report_pathz[1:]:  # 从第二个文档开始追加
                word_document = Document(word)
                # 删除手动添加分页符的代码
                middle_new_docx.append(word_document)
            middle_new_docx.save(new_docx_path)
            new_docx_path = new_docx_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
            result_dict['report'] = new_docx_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
            
        except Exception as e:
            print(f"发生错误：{e}")
            result_dict['report'] =None

    except Exception as e:
        logging.exception(e)
        raise Exception('现有获取的数据不能满足气候宜居要素计算条件，无法得到计算结果')

    return result_dict


def climate_assessment_handler(data_json):
    '''
    气候宜居评估接口
    '''
    products = data_json.get('products')  # list

    if isinstance(products, str):
        products = products.split(',')

    if products is None:
        result_dict = calc_climate_assessment(data_json)
        return result_dict

    if 'climate_suitable' in products:
        result_dict = calc_climate_assessment(data_json)
        return result_dict

    if 'summer_holiday' in products:
        pass

    if 'oxygen_bar' in products:
        pass
