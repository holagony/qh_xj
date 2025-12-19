import logging
import os
import uuid
import pickle
import json
import simplejson
import requests
import numpy as np
import pandas as pd
from flask import Blueprint, request, jsonify
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_loader_with_threads import get_cmadaas_daily_data
from Utils.data_loader import get_data_postgresql, is_self_station
from Utils.data_processing import daily_data_processing
from Utils.get_local_data import get_local_data
from Module00.wrapped.check import check
from Module04.module04_utils import time_revision, height_revision, get_station
from Report.code.Module04.re_wind import re_wind_report,re_wind_report_pg
from Report.code.Module04.re_snow import re_snow_report,re_snow_report_pg
from Report.code.Module04.re_tem import re_tem_report,re_tem_report_pg
from Report.code.Module04.re_frs import re_frs_report,re_frs_report_pg

from Utils.get_url_path import save_cmadaas_data
from Module04.wrapped.return_period_wind import calc_return_period_wind
from Module04.wrapped.return_period_pre import calc_return_period_pre
from Module04.wrapped.return_period_snow import calc_return_period_snow
from Module04.wrapped.return_period_tem import calc_return_period_tem
from Module04.wrapped.return_period_frs import calc_return_period_frs

def callback(url, result_id, result):
    header = {'Content-Type': 'application/json'}
    _json = {"id": result_id, "status": "finish", "results": result}
    if url is None:
        return
    return requests.put(url, headers=header, data=json.dumps(_json))


class workerReturnWind:

    def act(self, jsons):
        code = 200
        msg = '获取数据成功'
        json_str = jsons
        data_json = json.loads(json_str)
        years = data_json.get('years')
        main_station = data_json.get('main_station')  # 参证站
        if (years is None) or (not isinstance(years, str)) or (',' not in years):
            raise Exception('缺少或格式错误的 years，需形如 YYYY,YYYY')
        if not main_station:
            raise Exception('缺少 main_station')

        relocation_year = data_json.get('relocation_year')  # 迁站订正 list [2005,2010,2022] 单点
        height_revision_year = data_json.get('height_revision_year')  # 高度订正 ["1990,2000","2001,2005"]
        measure_height = data_json.get('measure_height')  # 高度订正 测风仪高度(m) 单值
        profile_index_main = data_json.get('profile_index_main')  # 高度订正 参证站数据风廓线指数 单值
        
        element = data_json.get('element')
        if element is None:
            elements = ['WIND']
        elif isinstance(element, list):
            elements = [str(e) for e in element]
        elif isinstance(element, str):
            elements = [e.strip() for e in element.split(',') if e.strip()]
        else:
            elements = ['WIND']
        elements = [e.upper() for e in elements]
        return_period_flag = data_json.get('return_period_flag', 0)  # 重现期/频率 0 or 1
        return_period = data_json.get('return_period', [2, 3, 5, 10, 20, 30, 50, 100])
        fitting_method = data_json.get('fitting_method', ['Gumbel', 'P3'])
        CI = data_json.get('CI', None)  # 置信区间
        sub_station = data_json.get('sub_station', None)
        threshold = data_json.get('threshold', 0)
        intercept = data_json.get('intercept', True)

        result_id = data_json.get('id')
        callback_url = data_json.get('callback')

        # 参数处理
        uuid4 = uuid.uuid4().hex
        data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            os.chmod(data_dir, 0o007 | 0o070 | 0o700)

        if isinstance(main_station, list):
            main_station = [str(ids) for ids in main_station]
            main_station = ','.join(main_station)
        if isinstance(main_station, int):
            main_station = str(main_station)

        if isinstance(sub_station, list):
            sub_station = [str(ids) for ids in sub_station]
            sub_station = ','.join(sub_station)
        if isinstance(sub_station, int):
            sub_station = str(sub_station)

        # 获得选取年份列表
        sel_years = years.split(',')
        start_year = int(sel_years[0])
        end_year = int(sel_years[1])
        range_year = np.arange(start_year, end_year + 1, 1)
        assert len(range_year) >= 15, '选择的数据年份太短，小于10年，可能会出现计算错误或数据不足的情况，请重新选择'

        # 高度订正参数转换
        height_revision_year, measure_height, profile_index_main = (height_revision(height_revision_year, measure_height, profile_index_main))
        if height_revision_year is not None:
            assert (max(height_revision_year) <= range_year.max()) and (min(height_revision_year) >= range_year.min()), '高度订正年份选择超过数据年份'

        # 重现期年份和频率统一
        if return_period_flag == 0:
            return_years = return_period
        elif return_period_flag == 1:
            return_years = (100 / np.array(return_period)).astype(int).tolist()
            assert 0 not in return_period, '设置的频率不能等于0'
        return_years.sort() # 排序

        # 拼接需要下载的参数
        daily_elements = ''
        for ele in elements:
            if ele == 'WIND':
                daily_elements += 'WIN_S_Max,WIN_S_2mi_Avg,WIN_S_Inst_Max,TEM_Avg,PRS_Avg,'
            elif ele == 'PRE':
                daily_elements += 'PRE_Time_2020,'
            elif ele == 'SNOW':
                daily_elements += 'Snow_Depth,'
            elif ele == 'TEM':
                daily_elements += 'TEM_Max,TEM_Min,'
            elif ele == 'FRS':
                daily_elements += 'FRS_1st_Bot,FRS_2nd_Bot,'
        if daily_elements.endswith(','):
            daily_elements = daily_elements[:-1]

        if cfg.INFO.READ_LOCAL:
            sta_ids = get_station(main_station, sub_station)
            day_eles = ('Station_Id_C,Station_Name,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements).split(',')
            daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
            daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')
        else:
            try:
                sta_ids = get_station(main_station, sub_station)
                daily_df = get_cmadaas_daily_data(years, daily_elements, main_station)
                daily_df = daily_data_processing(daily_df, years)
            except Exception as e:
                logging.exception(e)
                raise Exception('天擎数据获取失败')

        # 5.生成结果
        try:
            from_database = 0
            df_sequence = daily_df[daily_df['Station_Id_C'] == main_station]
            sub_df = daily_df[daily_df['Station_Id_C'] == sub_station]
            all_results = edict()
            for ele in elements:
                if ele == 'WIND':
                    wind_s = calc_return_period_wind(df_sequence, relocation_year, height_revision_year, measure_height, profile_index_main,
                                                     return_years, CI, fitting_method, data_dir, from_database, sub_df, threshold, intercept, main_station)
                    r = wind_s.run()
                    r['uuid'] = uuid4
                    try:
                        if len(fitting_method) == 2:
                            report_path = re_wind_report(r, daily_df, data_dir)
                            report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                            r['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
                        else:
                            report_path = re_wind_report_pg(r, daily_df, fitting_method[0], data_dir)
                            report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                            r['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
                    except Exception as e:
                        r['report'] = None
                    if 'img_save_path' in r:
                        try:
                            for name, path in r['img_save_path'].items():
                                path = path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                                r['img_save_path'][name] = path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
                        except:
                            pass
                    all_results['WIND'] = r

                elif ele == 'TEM':
                    tem_s = calc_return_period_tem(df_sequence, relocation_year, height_revision_year, measure_height, profile_index_main,
                                                     return_years, CI, fitting_method, data_dir, from_database, sub_df, threshold, intercept, main_station)
                    r = tem_s.run()
                    r['uuid'] = uuid4
                    try:
                        if len(fitting_method) == 2:
                            report_path = re_tem_report(r, daily_df, data_dir)
                            report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                            r['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
                        else:
                            report_path = re_tem_report_pg(r, daily_df, fitting_method[0], data_dir)
                            report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                            r['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
                    except Exception as e:
                        r['report'] = None
                    if 'img_save_path' in r:
                        try:
                            for name, path in r['img_save_path'].items():
                                path = path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                                r['img_save_path'][name] = path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
                        except:
                            pass
                    all_results['WIND'] = r

                elif ele == 'PRE':
                    pre_calc = calc_return_period_pre(df_sequence=df_sequence,
                                                      return_years=return_years,
                                                      CI=CI,
                                                      fitting_method=fitting_method,
                                                      img_path=data_dir,
                                                      sub_df=sub_df,
                                                      from_database=from_database,
                                                      threshold=threshold,
                                                      intercept=intercept)
                    r = pre_calc.run()
                    r['uuid'] = uuid4
                    try:
                        if len(fitting_method) == 2:
                            report_path = re_snow_report(r, daily_df, data_dir)
                            report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                            r['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
                        else:
                            report_path = re_snow_report_pg(r, daily_df, fitting_method[0], data_dir)
                            report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                            r['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
                    except Exception as e:
                        r['report'] = None
                    if 'img_save_path' in r:
                        try:
                            for name, path in r['img_save_path'].items():
                                path = path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                                r['img_save_path'][name] = path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
                        except:
                            pass
                    all_results['PRE'] = r

                elif ele == 'FRS':
                    frs_calc = calc_return_period_frs(df_sequence=df_sequence,
                                                      return_years=return_years,
                                                      CI=CI,
                                                      fitting_method=fitting_method,
                                                      img_path=data_dir)
                    r = frs_calc.run()
                    r['uuid'] = uuid4
                    try:

                        
                        if len(fitting_method) == 2:
                            report_path = re_frs_report(r, daily_df, data_dir)
                            report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                            r['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
                        else:
                            report_path = re_frs_report_pg(r, daily_df, fitting_method[0], data_dir)
                            report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                            r['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
                            
                    except Exception as e:
                        r['report'] = None
                    if 'img_save_path' in r:
                        try:
                            for name, path in r['img_save_path'].items():
                                path = path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                                r['img_save_path'][name] = path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
                        except:
                            pass
                    all_results['FRS'] = r

            years_split = years.split(',')
            all_results.check_result = edict()
            if daily_df is not None and len(daily_df) != 0:
                checker = check(daily_df, 'D', daily_elements.split(','), sta_ids.split(','), years_split[0], years_split[1])
                all_results.check_result['使用的天擎日要素'] = checker.run()
            if cfg.INFO.SAVE_RESULT:
                all_results['csv'] = save_cmadaas_data(data_dir, day_data=daily_df)

        except Exception as e:
            logging.exception(e)
            raise Exception('现有获取的数据不能满足重现期计算条件，无法得到计算结果')

        return_data = simplejson.dumps({'code': code, 'msg': msg, 'data': all_results}, ensure_ascii=False, ignore_nan=True)
        callback(callback_url, result_id, return_data)

        return return_data
