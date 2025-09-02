import os
import json
import uuid
import logging
import simplejson
import numpy as np
import pandas as pd
from flask import Blueprint, request, jsonify
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_loader_with_threads import get_cmadaas_monthly_data, get_cmadaas_daily_data, get_cmadaas_hourly_data
from Utils.data_processing import monthly_data_processing, daily_data_processing, hourly_data_processing
from Utils.get_local_data import get_local_data
from Module00.wrapped.check import check
from Module05.wrapped.heating_and_ventilation import calc_heating_and_ventilation, calc_summer_tem_and_enthalpy
from Module05.wrapped.nuclear_hvac import calc_nuclear_havc
from Module05.wrapped.building_energy_efficiency import calc_building_energy_efficiency
from Module05.wrapped.water_supply import calc_water_supply
from Module05.wrapped.water_circulation import calc_water_circulation
from Module05.wrapped.freezing_and_thawing import calc_freezing_and_thawing_times, calc_freezing_and_thawing_day
from Module05.wrapped.rain_runoff import rain_runoff_stats
from Utils.get_url_path import save_cmadaas_data

from Report.code.Module05.building_energy_efficiency import building_energy_efficiency
from Report.code.Module05.freezing_and_thawing import freezing_and_thawing_report
from Report.code.Module05.heating_and_ventilation_report import heating_and_ventilation_report
from Report.code.Module05.nuclear_hvac import nuclear_hvac_report
from Report.code.Module05.rain_runoff import rain_runoff_report
from Report.code.Module05.water_circulation import water_circulation_report
from Report.code.Module05.water_supply import water_supply_report
from docx import Document
from docxcompose.composer import Composer

'''
各个子模块缺失值处理方法
1.在暖通中，需要先对所有小时数据计算湿球温度，如果数据存在nan则报错，因此选择三次样条插值插值补全小时数据(写在函数中)
  另外，计算要是用到的小时数据为4次数据，应该插值到逐小时，目前已默认增加插值代码
2.在核岛中，考虑到4次观测数据和最小时观测数据的组合，暂时未做任何改动
3.在建筑节能参数中，目前源程序的写法是转成numpy，所以日数据不能存在缺失值，在函数中采用了线性插值的方法
4.在给排水中，存在计算湿球温度，因此暂时选择删掉nan所在行的处理方式(写在接口中)
5.在循环水中，存在计算湿球温度，因此暂时选择删掉nan所在行的处理方式(写在接口中)
6.在雨水年径流总量控制率与设计降雨深度，删除nan(写在接口中)
'''


def heating_and_ventilation_handler(data_json):
    '''
    计算暖通/室外空气要素接口
    '''
    # 1.读取json中的信息
    years = data_json['years']
    sta_ids = data_json['station_ids']

    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    if isinstance(sta_ids, list):
        sta_ids = [str(ids) for ids in sta_ids]
        sta_ids = ','.join(sta_ids)
    if isinstance(sta_ids, int):
        sta_ids = str(sta_ids)

    # 2.参数直接预设好
    years_split = years.split(',')
    num_years = int(years_split[1]) - int(years_split[0]) + 1
    start_date = years_split[0] + '010100000'

    monthly_elements = 'TEM_Avg,PRS_Avg,RHU_Avg,SSP_Mon,FRS_Depth_Max,WIN_S_2mi_Avg,WIN_NNE_Freq,WIN_NE_Freq,WIN_ENE_Freq,WIN_E_Freq,WIN_ESE_Freq,WIN_SE_Freq,WIN_SSE_Freq,WIN_S_Freq,WIN_SSW_Freq,WIN_SW_Freq,WIN_WSW_Freq,WIN_W_Freq,WIN_WNW_Freq,WIN_NW_Freq,WIN_NNW_Freq,WIN_N_Freq'
    daily_elements = 'PRS_Avg,TEM_Avg,TEM_Max,TEM_Min,RHU_Avg'
    hourly_elements = 'PRS,TEM,RHU'

    # 3.数据获取
    if cfg.INFO.READ_LOCAL:
        month_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,' + monthly_elements).split(',')
        day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements).split(',')
        hour_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,' + hourly_elements).split(',')

        monthly_df = pd.read_csv(cfg.FILES.QH_DATA_MONTH, low_memory=False)
        daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
        hourly_df = pd.read_csv(cfg.FILES.QH_DATA_HOUR)
        
        monthly_df = get_local_data(monthly_df, sta_ids, month_eles, years, 'Month')
        daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')
        hourly_df = get_local_data(hourly_df, sta_ids, hour_eles, years, 'Hour')

    else:
        try:
            monthly_df = get_cmadaas_monthly_data(years, monthly_elements, sta_ids)
            daily_df = get_cmadaas_daily_data(years, daily_elements, sta_ids)
            hourly_df = get_cmadaas_hourly_data(start_date, num_years, hourly_elements, sta_ids)

            if monthly_df is not None:
                monthly_df = monthly_data_processing(monthly_df, years)
                monthly_df['RHU_Avg'] = monthly_df['RHU_Avg'] / 100

            if daily_df is not None:
                daily_df = daily_data_processing(daily_df, years)
                daily_df['RHU_Avg'] = daily_df['RHU_Avg'] / 100

            if hourly_df is not None:
                hourly_df = hourly_data_processing(hourly_df, years)
                hourly_df['RHU'] = hourly_df['RHU'] / 100

        except Exception as e:
            logging.exception(e)
            raise Exception('天擎数据获取失败')

    # 4.生成结果
    try:
        df, df_hourly, result9, result33 = calc_heating_and_ventilation(monthly_df, daily_df, hourly_df)

        if result9 and result33 is not None:
            t_sh, enthalpy = calc_summer_tem_and_enthalpy(df_hourly, result9, result33)
            t_sh = t_sh.to_dict(orient='records')
            enthalpy = enthalpy.to_dict(orient='records')
        else:
            t_sh = None
            enthalpy = None

        result_dict = edict()
        result_dict['uuid'] = uuid4
        result_dict['采暖与室外空调参数'] = df.to_dict(orient='records')
        result_dict['夏季空调室外计算逐时温度'] = t_sh
        result_dict['夏季空调室外计算焓值'] = enthalpy
        
        try:
            report_path = heating_and_ventilation_report(df,t_sh,enthalpy,daily_df,monthly_df,data_dir)
            report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
            result_dict['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
        except:
            result_dict['report'] = None

        # module00完整率检验
        years_split = years.split(',')
        result_dict.check_result = edict()
        if monthly_df is not None and len(monthly_df) != 0:
            checker = check(monthly_df, 'MS', monthly_elements.split(','), [sta_ids], years_split[0], years_split[1])
            result_dict.check_result['使用的天擎月要素'] = checker.run()

        if daily_df is not None and len(daily_df) != 0:
            checker = check(daily_df, 'D', daily_elements.split(','), [sta_ids], years_split[0], years_split[1])
            result_dict.check_result['使用的天擎日要素'] = checker.run()

        if hourly_df is not None and len(hourly_df) != 0:
            checker = check(hourly_df, 'H', hourly_elements.split(','), [sta_ids], years_split[0], years_split[1])
            result_dict.check_result['使用的天擎小时要素'] = checker.run()

        # 6.结果保存
        if cfg.INFO.SAVE_RESULT:
            result_dict['csv'] = save_cmadaas_data(data_dir, mon_data=monthly_df, day_data=daily_df, hour_data=hourly_df)

    except Exception as e:
        logging.exception(e)
        raise Exception('现有获取的数据不能满足暖通要素计算条件，无法得到计算结果')

    return result_dict


def nuclear_havc_calc_handler(data_json):
    '''
    计算核岛要素接口
    '''
    # 1.读取json中的信息
    # json_str = request.get_data(as_text=True)  # 获取JSON字符串
    # data_json = json.loads(json_str)
    years = data_json['years']
    sta_ids = data_json['station_ids']
    # interpolation = data_json['interpolation']

    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    if isinstance(sta_ids, list):
        sta_ids = [str(ids) for ids in sta_ids]
        sta_ids = ','.join(sta_ids)
    if isinstance(sta_ids, int):
        sta_ids = str(sta_ids)

    # 2.参数直接预设好
    years_split = years.split(',')
    num_years = int(years_split[1]) - int(years_split[0]) + 1
    start_date = years_split[0] + '010100000'
    hourly_elements = 'PRS,TEM,RHU'

    # 3.数据获取
    if cfg.INFO.READ_LOCAL:
        hour_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,' + hourly_elements).split(',')
        hourly_df = pd.read_csv(cfg.FILES.QH_DATA_HOUR)
        hourly_df = get_local_data(hourly_df, sta_ids, hour_eles, years, 'Hour')
    else:
        try:  # 天擎数据下载 and 数据前处理
            hourly_df = get_cmadaas_hourly_data(start_date, num_years, hourly_elements, sta_ids)

            if hourly_df is not None:
                hourly_df = hourly_data_processing(hourly_df, years)
                hourly_df['RHU'] = hourly_df['RHU'] / 100

        except Exception as e:
            logging.exception(e)
            raise Exception('天擎数据获取失败')

    # 4.生成结果
    try:
        result_dict = calc_nuclear_havc(hourly_df, interpolation=0)
        result_dict['uuid'] = uuid4
        
        try:
            report_path = nuclear_hvac_report(result_dict,hourly_df,data_dir)
            report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
            result_dict['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
        except:
            result_dict['report'] = None
            
        # module00完整率统计
        years_split = years.split(',')
        result_dict.check_result = edict()
        if hourly_df is not None and len(hourly_df) != 0:
            checker = check(hourly_df, 'H', hourly_elements.split(','), [sta_ids], years_split[0], years_split[1])
            result_dict.check_result['使用的天擎小时要素'] = checker.run()
            
        # 6.结果保存
        if cfg.INFO.SAVE_RESULT:
            result_dict['csv'] = save_cmadaas_data(data_dir, hour_data=hourly_df)

    except Exception as e:
        logging.exception(e)
        raise Exception('现有获取的数据不能满足核岛要素计算条件，无法得到计算结果')

    return result_dict


def freezing_and_thawing_calc_handler(data_json):
    '''
    计算冻融交替要素接口 冻融参数算法
    '''
    # 1.读取json中的信息
    # json_str = request.get_data(as_text=True)  # 获取JSON字符串
    # data_json = json.loads(json_str)
    years = data_json['years']
    sta_ids = data_json['station_ids']
    elements = data_json['elements']  # 选择的冻融计算方式type1/2/3

    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    if isinstance(sta_ids, list):
        sta_ids = [str(ids) for ids in sta_ids]
        sta_ids = ','.join(sta_ids)
    if isinstance(sta_ids, int):
        sta_ids = str(sta_ids)

    # 2.拼接需要下载的参数，直接预设好
    years_split = years.split(',')
    num_years = int(years_split[1]) - int(years_split[0]) + 1
    start_date = years_split[0] + '010100000'

    daily_elements = ''
    hourly_elements = ''

    for ele in elements:
        if ele == 'type1':
            hourly_elements += 'TEM,'
        elif ele == 'type2':
            if 'TEM_Min' in daily_elements:
                pass
            else:
                daily_elements += 'TEM_Min,'
        elif ele == 'type3':
            if 'TEM_Min' in daily_elements:
                daily_elements += 'TEM_Max,'
            else:
                daily_elements += 'TEM_Max,TEM_Min,'

    # 3.数据获取
    if cfg.INFO.READ_LOCAL:
        day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements[:-1]).split(',')
        hour_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,' + hourly_elements[:-1]).split(',')
        day_eles = [item for item in day_eles if item != '']
        hour_eles = [item for item in hour_eles if item != '']
        daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
        hourly_df = pd.read_csv(cfg.FILES.QH_DATA_HOUR)
        daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')
        hourly_df = get_local_data(hourly_df, sta_ids, hour_eles, years, 'Hour')
        
    else:
        try:
            hourly_df = None
            daily_df = None
            if 'type1' in elements:
                hourly_df = get_cmadaas_hourly_data(start_date, num_years, hourly_elements, sta_ids)
                if hourly_df is not None:
                    hourly_df = hourly_data_processing(hourly_df, years)

            if 'type2' or 'type3' in elements:
                daily_df = get_cmadaas_daily_data(years, daily_elements, sta_ids)
                if daily_df is not None:
                    daily_df = daily_data_processing(daily_df, years)

        except Exception as e:
            logging.exception(e)
            raise Exception('天擎数据获取失败')

    # 4.生成结果
    try:
        # module00完整率统计
        years_split = years.split(',')
        result_dict = edict()
        result_dict['uuid'] = uuid4
        result_dict.check_result = edict()
        daily_elements = daily_elements[:-1]
        hourly_elements = hourly_elements[:-1]
        
        # 报告部分
        report_pathz=[]
        report_pathz.append(os.path.join(cfg['report']['template'],'Module05','freezing_and_thawing_1.docx'))

        if daily_df is not None and len(daily_df) != 0:
            checker = check(daily_df, 'D', daily_elements.split(','), [sta_ids], years_split[0], years_split[1])
            result_dict.check_result['使用的天擎日要素'] = checker.run()

        if hourly_df is not None and len(hourly_df) != 0:
            checker = check(hourly_df, 'H', hourly_elements.split(','), [sta_ids], years_split[0], years_split[1])
            result_dict.check_result['使用的天擎小时要素'] = checker.run()

        if 'type1' in elements:
            meteo = hourly_df['TEM']
            rate = (meteo.isnull().sum()) / meteo.shape[0]

            if np.any(rate == 1):
                result1 = None
            else:
                result1 = calc_freezing_and_thawing_times(hourly_df, hourly=1)
                result1 = result1.to_dict(orient='records')

            result_dict['冻融次数(小时数据)'] = result1
            
            try:
                report_path = freezing_and_thawing_report(1,result1, daily_df, data_dir)
                report_pathz.append(report_path)
            except:
                pass

        if 'type2' in elements:
            meteo = daily_df['TEM_Min']
            rate = (meteo.isnull().sum()) / meteo.shape[0]

            if np.any(rate == 1):
                result2 = None
            else:
                result2 = calc_freezing_and_thawing_times(daily_df, hourly=0)
                result2 = result2.to_dict(orient='records')

            result_dict['冻融次数(日数据)'] = result2
            
            # try:
            report_path = freezing_and_thawing_report(2,result2, daily_df, data_dir)
            report_pathz.append(report_path)

            # except:
            #     pass

        if 'type3' in elements:
            meteo = daily_df[['TEM_Max', 'TEM_Min']]
            rate = (meteo.isnull().sum()) / meteo.shape[0]

            if np.any(rate == 1):
                result3 = None
                result3_accum = None
            else:
                result3, result3_accum = calc_freezing_and_thawing_day(daily_df)
                result3 = result3.to_dict(orient='records')
                result3_accum = result3_accum.to_dict(orient='records')

            result_dict['冻融日'] = result3
            result_dict['累年各月冻融日'] = result3_accum
            
            try:
                report_path = freezing_and_thawing_report(3,result3, daily_df, data_dir)
                report_pathz.append(report_path)

            except:
                pass
            
        if len(report_pathz)==0:
            result_dict['report'] =None
        else:
            try:
                new_docx_path=os.path.join(data_dir,'freezing_and_thawing.docx')
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
        
        # 6.结果保存
        if cfg.INFO.SAVE_RESULT:
            result_dict['csv'] = save_cmadaas_data(data_dir, day_data=daily_df, hour_data=hourly_df)

    except Exception as e:
        logging.exception(e)
        raise Exception('现有获取的数据不能满足冻融要素计算条件，无法得到计算结果')

    return result_dict


def rain_runoff_calc_handler(data_json):
    '''
    雨水年径流总量控制率与设计降雨深度接口 使用日数据
    '''
    # 1.读取json中的信息
    # json_str = request.get_data(as_text=True)  # 获取JSON字符串
    # data_json = json.loads(json_str)
    years = data_json['years']
    sta_ids = data_json['station_ids']

    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    if isinstance(sta_ids, list):
        sta_ids = [str(ids) for ids in sta_ids]
        sta_ids = ','.join(sta_ids)
    if isinstance(sta_ids, int):
        sta_ids = str(sta_ids)

    # 2.参数直接预设好
    daily_elements = 'PRE_Time_2020'

    # 3.数据获取
    if cfg.INFO.READ_LOCAL:
        day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements).split(',')
        daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
        daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')
    else:
        try:
            daily_df = get_cmadaas_daily_data(years, daily_elements, sta_ids)
            daily_df = daily_data_processing(daily_df, years)
        except Exception as e:
            logging.exception(e)
            raise Exception('天擎数据获取失败')

    # 4.生成结果
    try:
        result_dict = edict()

        # module00完整率统计
        years_split = years.split(',')
        result_dict.check_result = edict()
        if daily_df is not None and len(daily_df) != 0:
            checker = check(daily_df, 'D', daily_elements.split(','), [sta_ids], years_split[0], years_split[1])
            result_dict.check_result['使用的天擎日要素'] = checker.run()

        # 计算
        daily_df.dropna(inplace=True)
        pre, table1, table2, img_path = rain_runoff_stats(daily_df, data_dir)
        pre = pre.to_dict(orient='records')
        table1 = table1.to_dict(orient='records')
        table2 = table2.to_dict(orient='records')

        result_dict['uuid'] = uuid4
        result_dict['result1'] = pre
        result_dict['result2'] = table1
        result_dict['result3'] = table2
        
        try:
            report_path = rain_runoff_report(pre, table1, table2, img_path, daily_df, data_dir)
            report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
            result_dict['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
        except:
            result_dict['report'] = None

        img_path = img_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)  # 图片容器内转容器外路径
        result_dict['img_save_path'] = img_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
        result_dict['Note'] = ['result1降水事件', 'result2降水事件抽取断点', 'result3年径流总量控制率']

        # 6.结果保存
        if cfg.INFO.SAVE_RESULT:
            result_dict['csv'] = save_cmadaas_data(data_dir, day_data=daily_df)

    except Exception as e:
        logging.exception(e)
        raise Exception('现有获取的数据不能满足雨水径流要素计算条件，无法得到计算结果')

    return result_dict


def water_supply_calc_handler(data_json):
    '''
    计算给排水要素接口
    '''
    # 1.读取json中的信息
    # json_str = request.get_data(as_text=True)  # 获取JSON字符串
    # data_json = json.loads(json_str)
    years = data_json['years']
    sta_ids = data_json['station_ids']

    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    # 2.参数直接预设好
    daily_elements = 'TEM_Avg,PRS_Avg,RHU_Avg'

    # 3.数据获取
    if cfg.INFO.READ_LOCAL:
        day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements).split(',')
        daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
        daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')
        daily_df['RHU_Avg'] = daily_df['RHU_Avg'] / 100
    else:
        try:
            daily_df = get_cmadaas_daily_data(years, daily_elements, sta_ids)
            daily_df = daily_data_processing(daily_df, years)
            # daily_df['RHU_Avg'] = daily_df['RHU_Avg'] / 100
        except Exception as e:
            logging.exception(e)
            raise Exception('天擎数据获取失败')

    # 4.生成结果
    try:
        # module00完整率统计
        years_split = years.split(',')
        if daily_df is not None and len(daily_df) != 0:
            checker = check(daily_df, 'D', daily_elements.split(','), [sta_ids], years_split[0], years_split[1])

        # 计算
        daily_df.dropna(inplace=True)
        result_dict = calc_water_supply(daily_df)
        result_dict['uuid'] = uuid4
        result_dict.check_result = edict()
        result_dict.check_result['使用的天擎日要素'] = checker.run()
        
        try:
            report_path = water_supply_report(result_dict,daily_df,data_dir)
            report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
            result_dict['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
        except:
            result_dict['report'] = None

        # 6.结果保存
        if cfg.INFO.SAVE_RESULT:
            result_dict['csv'] = save_cmadaas_data(data_dir, day_data=daily_df)

    except Exception as e:
        logging.exception(e)
        raise Exception('现有获取的数据不能满足给排水要素计算条件，无法得到计算结果')

    return result_dict


def water_circulation_calc_handler(data_json):
    '''
    计算循环水要素接口
    '''
    # 1.读取json中的信息
    # json_str = request.get_data(as_text=True)  # 获取JSON字符串
    # data_json = json.loads(json_str)
    years = data_json['years']
    sta_ids = data_json['station_ids']

    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    if isinstance(sta_ids, list):
        sta_ids = [str(ids) for ids in sta_ids]
        sta_ids = ','.join(sta_ids)
    if isinstance(sta_ids, int):
        sta_ids = str(sta_ids)

    # 2.参数直接预设好
    daily_elements = 'TEM_Avg,PRS_Avg,RHU_Avg'

    # 3.数据获取
    if cfg.INFO.READ_LOCAL:
        day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements).split(',')
        daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
        daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')
        daily_df['RHU_Avg'] = daily_df['RHU_Avg'] / 100
    else:
        try:
            daily_df = get_cmadaas_daily_data(years, daily_elements, sta_ids)
            daily_df = daily_data_processing(daily_df, years)
            # daily_df['RHU_Avg'] = daily_df['RHU_Avg'] / 100
        except Exception as e:
            raise Exception('天擎数据获取失败')

    # 4.生成结果
    try:
        # module00完整率统计
        years_split = years.split(',')
        if daily_df is not None and len(daily_df) != 0:
            checker = check(daily_df, 'D', daily_elements.split(','), [sta_ids], years_split[0], years_split[1])

        # 计算
        daily_df.dropna(inplace=True)
        result_dict = calc_water_circulation(daily_df)
        result_dict['uuid'] = uuid4
        result_dict.check_result = edict()
        result_dict.check_result['使用的天擎日要素'] = checker.run()

        try:
            report_path = water_circulation_report(result_dict,daily_df,data_dir)
            report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
            result_dict['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
        except:
            result_dict['report'] = None
        
        # 6.结果保存
        if cfg.INFO.SAVE_RESULT:
            result_dict['csv'] = save_cmadaas_data(data_dir, day_data=daily_df)

    except Exception as e:
        logging.exception(e)
        raise Exception('现有获取的数据不能满足循环水要素计算条件，无法得到计算结果')

    return result_dict


def building_energy_efficiency_calc_handler(data_json):
    '''
    计算建筑节能要素接口
    '''
    # 1.读取json中的信息
    # json_str = request.get_data(as_text=True)  # 获取JSON字符串
    # data_json = json.loads(json_str)
    years = data_json['years']
    sta_ids = data_json['station_ids']

    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    if isinstance(sta_ids, list):
        sta_ids = [str(ids) for ids in sta_ids]
        sta_ids = ','.join(sta_ids)
    if isinstance(sta_ids, int):
        sta_ids = str(sta_ids)

    # 2.参数直接预设好
    daily_elements = 'TEM_Avg'

    # 3.数据获取    
    if cfg.INFO.READ_LOCAL:
        day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements).split(',')
        daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
        daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')
    else:
        try:  # 天擎数据下载 and 数据前处理
            daily_df = get_cmadaas_daily_data(years, daily_elements, sta_ids)
            daily_df = daily_data_processing(daily_df, years)
        except Exception as e:
            logging.exception(e)
            raise Exception('天擎数据获取失败')

    # 4.生成结果
    try:
        result_dict = calc_building_energy_efficiency(daily_df)
        result_dict['uuid'] = uuid4
        try:
            report_path = building_energy_efficiency(result_dict, daily_df, data_dir)
            report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
            result_dict['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
        except:
            result_dict['report'] = None
            
        # module00完整率统计
        years_split = years.split(',')
        result_dict.check_result = edict()
        if daily_df is not None and len(daily_df) != 0:
            checker = check(daily_df, 'D', daily_elements.split(','), [sta_ids], years_split[0], years_split[1])
            result_dict.check_result['使用的天擎日要素'] = checker.run()
        
        # 6.结果保存
        if cfg.INFO.SAVE_RESULT:
            result_dict['csv'] = save_cmadaas_data(data_dir, day_data=daily_df)

    except Exception as e:
        logging.exception(e)
        raise Exception('现有获取的数据不能满足建筑节能要素计算条件，无法得到计算结果')

    return result_dict