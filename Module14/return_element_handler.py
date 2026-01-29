import logging
import os
import uuid
import json
import simplejson
import requests
import numpy as np
import pandas as pd
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_loader_with_threads import get_cmadaas_daily_data
from Utils.data_processing import daily_data_processing
from Utils.get_local_data import get_local_data
from Module00.wrapped.check import check
from Module04.module04_utils import get_station
from Report.code.Module04.re_wind import re_wind_report,re_wind_report_pg
from Report.code.Module04.re_snow import re_snow_report,re_snow_report_pg
from Report.code.Module04.re_tem import re_tem_report,re_tem_report_pg
from Report.code.Module04.re_frs import re_frs_report,re_frs_report_pg
from Utils.get_url_path import save_cmadaas_data
from Module14.wrapped.return_period_wind import calc_return_period_wind
from Module14.wrapped.return_period_pre import calc_return_period_pre
from Module14.wrapped.return_period_snow import calc_return_period_snow
from Module14.wrapped.return_period_tem import calc_return_period_tem
from Module14.wrapped.return_period_frs import calc_return_period_frs


def convert_nested_df(data):
    if isinstance(data, dict):
        return {k: convert_nested_df(v) for k, v in data.items()}
    elif isinstance(data, pd.DataFrame):
        return data.to_dict(orient='records')
    elif isinstance(data, pd.Series):
        return data.to_frame().T.round(1).to_dict(orient='records')
    else:
        return data


def callback(url, result_id, result):
    header = {'Content-Type': 'application/json'}
    _json = {"id": result_id, "status": "finish", "results": result}
    if url is None:
        return
    return requests.put(url, headers=header, data=json.dumps(_json))


def workerReturnPeriod(data_json):

    code = 200
    msg = '获取数据成功'

    years = data_json.get('years')
    main_station = data_json.get('main_station')  # 参证站
    elements = data_json.get('element') # ['wind','pre','snow','frs','tem']
    if isinstance(elements, str):
        elements = elements.split(',')
    elements = [e.upper() for e in elements]

    return_years = [30, 50, 100]
    fitting_method = ['Gumbel', 'P3']
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

    # 获得选取年份列表
    sel_years = years.split(',')
    start_year = int(sel_years[0])
    end_year = int(sel_years[1])
    range_year = np.arange(start_year, end_year + 1, 1)
    assert len(range_year) >= 20, '选择的数据年份太短，小于20年，可能会出现计算错误或数据不足的情况，请重新选择'

    # 拼接需要下载的参数
    daily_elements = ''
    for ele in elements:
        if ele == 'WIND':
            daily_elements += 'WIN_S_Max,WIN_S_Inst_Max,'
        elif ele == 'TEM':
            daily_elements += 'TEM_Max,TEM_Min,'
        elif ele == 'PRE':
            daily_elements += 'PRE_Time_2020,'
        elif ele == 'SNOW':
            daily_elements += 'Snow_Depth,'
        elif ele == 'FRS':
            daily_elements += 'FRS_1st_Bot,FRS_2nd_Bot,'
    if daily_elements.endswith(','):
        daily_elements = daily_elements[:-1]
    
    sub_station = None
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
    df_sequence = daily_df[daily_df['Station_Id_C'] == main_station]
    all_results = edict()
    all_results['uuid'] = uuid4

    for ele in elements:
        if ele == 'WIND':
            wind_s = calc_return_period_wind(df_sequence, return_years, fitting_method, data_dir, main_station)
            r = wind_s.run()
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
            tem_s = calc_return_period_tem(df_sequence, return_years, fitting_method, data_dir)
            r = tem_s.run()
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
            all_results['TEM'] = r

        elif ele == 'PRE':
            pre_calc = calc_return_period_pre(df_sequence=df_sequence,
                                                return_years=return_years,
                                                fitting_method=fitting_method,
                                                img_path=data_dir,
                                                main_station=main_station)
            r = pre_calc.run()
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
        
        elif ele == 'SNOW':
            snow_calc = calc_return_period_snow(df_sequence=df_sequence,
                                                return_years=return_years,
                                                fitting_method=fitting_method,
                                                img_path=data_dir,
                                                main_station=main_station)
            r = snow_calc.run()
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
            all_results['SNOW'] = r
        
        elif ele == 'FRS':
            frs_calc = calc_return_period_frs(df_sequence=df_sequence,
                                                return_years=return_years,
                                                fitting_method=fitting_method,
                                                img_path=data_dir,
                                                main_station=main_station)
            r = frs_calc.run()
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

    # 完整新分析
    years_split = years.split(',')
    all_results.check_result = edict()
    if daily_df is not None and len(daily_df) != 0:
        daily_element_list = [e.strip() for e in daily_elements.split(',') if e.strip()]
        sta_list = [s.strip() for s in sta_ids.split(',') if s.strip()]
        checker = check(daily_df, 'D', daily_element_list, sta_list, years_split[0], years_split[1])
        all_results.check_result['使用的天擎日要素'] = checker.run()

    if cfg.INFO.SAVE_RESULT:
        all_results['csv'] = save_cmadaas_data(data_dir, day_data=daily_df)

    # 最后结果
    all_results = convert_nested_df(all_results)
    return_data = simplejson.dumps({'code': code, 'msg': msg, 'data': all_results}, ensure_ascii=False, ignore_nan=True)
    callback(callback_url, result_id, return_data)

    return return_data


if __name__=='__main__':
    
    data_json={
  "years": "1985,2009",
  "main_station": "52754",
  "element": ["TEM"]
}
    
    
    a=workerReturnPeriod(data_json)
    print(a)