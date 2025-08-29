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
from Utils.get_local_data import get_local_data
from Utils.data_loader_with_threads import get_cmadaas_daily_data
from Utils.data_loader import get_data_postgresql, is_self_station
from Utils.data_processing import daily_data_processing, database_data_processing
from Module00.wrapped.check import check
from Module04.wrapped.return_period_tem import calc_return_period_tem
from Module04.module04_utils import get_station
from Report.code.Module04.re_wind import re_wind_report
from Report.code.Module04.re_tem import re_tem_report,re_tem_report_pg


def callback(url, result_id, result):
    header = {'Content-Type': 'application/json'}
    _json = {"id": result_id, "status": "finish", "results": result}
    if url is None:
        return
    requests.put(url, headers=header, data=json.dumps(_json))


class workerReturnTem:

    def act(self, jsons):
        json_str = jsons
        code = 200
        msg = '获取数据成功'

        # 1.读取json中的信息
        data_json = json.loads(json_str)
        years = data_json['years']
        main_station = data_json['main_station']  # 参证站
        return_period_flag = data_json['return_period_flag']  # 重现期/频率 0 or 1
        return_period = data_json['return_period']
        fitting_method = data_json['fitting_method']
        element_name = data_json['element_name']
        CI = data_json.get('CI')
        sub_station = data_json.get('sub_station')  # 厂址站号
        max_threshold = data_json.get('max_threshold')
        min_threshold = data_json.get('min_threshold')
        intercept = data_json.get('intercept')
        result_id = data_json.get('id')
        callback_url = data_json.get('callback')

        # 2.参数处理
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
        assert len(range_year) >= 10, '选择的数据年份太短，小于10年，可能会出现计算错误或数据不足的情况，请重新选择'

        # 重现期年份和频率统一
        if return_period_flag == 0:
            return_years = return_period

        elif return_period_flag == 1:
            return_years = (100 / np.array(return_period)).astype(int).tolist()
            assert 0 not in return_period, '设置的频率不能等于0'
        return_years.sort() # 排序

        # 3.拼接需要下载的参数
        daily_elements = 'TEM_Max,TEM_Min'

        # 4.数据获取
        # from_database = is_self_station(sub_station)  # o or 1
        from_database = 0

        if cfg.INFO.READ_LOCAL:
            if from_database == 0:
                sta_ids = get_station(main_station, sub_station)
                day_eles = ('Station_Id_C,Station_Name,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements).split(',')
                daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)

                daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')
            else:
                pass
        else:
            try:  # 天擎数据下载 and 数据前处理
                if from_database == 0:
                    sta_ids = get_station(main_station, sub_station)
                    daily_df = get_cmadaas_daily_data(years, daily_elements, sta_ids)
                    daily_df = daily_data_processing(daily_df, years)
                else:
                    pass

            except Exception as e:
                logging.exception(e)
                raise Exception('天擎某要素数据格式异常，导致nmc_met_io无法获取数据流，或因为无法在数据库中检索到自建站数据，\
                                 请检查和记录选取的站号、时间和要素，进行反馈排查')

        # 5.生成结果
        try:
            if from_database == 0:
                df_sequence = daily_df[daily_df['Station_Id_C'] == main_station]
                sub_df = daily_df[daily_df['Station_Id_C'] == sub_station]
            else:
                pass

            tem = calc_return_period_tem(df_sequence, return_years, CI, fitting_method, element_name, data_dir, sub_df, from_database, max_threshold, min_threshold, intercept)
            tem_result = tem.run()
            tem_result['uuid'] = uuid4
            
            try:
                if len(fitting_method)==2:
                    report_path = re_tem_report(tem_result,df_sequence,data_dir)
                    report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                    tem_result['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
                else:
                    report_path = re_tem_report_pg(tem_result,df_sequence,fitting_method[0],data_dir)
                    report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                    tem_result['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
                
            except Exception as e:
                print(f"温度重现期报告 发生了错误：{e}")
                tem_result['report'] = None

            # url替换
            for key, sub_dict in tem_result.items():
                if (type(sub_dict) != list) and (type(sub_dict) != str) and (sub_dict is not None):
                    for key1, sub_dict1 in sub_dict.items():
                        if key1 == 'img_save_path':
                            try:
                                for name, path in sub_dict1.items():
                                    path = path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)  # 图片容器内转容器外路径
                                    sub_dict1[name] = path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
                            except:
                                pass
            
            # module00完整率统计
            years_split = years.split(',')
            tem_result.check_result = edict()
            if daily_df is not None and len(daily_df) != 0:
                checker = check(daily_df, 'D', daily_elements.split(','), sta_ids.split(','), years_split[0], years_split[1])
                tem_result.check_result['使用的天擎日要素'] = checker.run()
            
        except Exception as e:
            logging.exception(e)
            raise e

        # 转成JSON字符串
        return_data = simplejson.dumps({'code': code, 'msg': msg, 'data': tem_result}, ensure_ascii=False, ignore_nan=True)
        callback(callback_url, result_id, return_data)

        # return_data保存pickle
        # with open (data_dir+'/return_data.txt', 'wb') as f:
        #     pickle.dump(return_data, f)

        return return_data
