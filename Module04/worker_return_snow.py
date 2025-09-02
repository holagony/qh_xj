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
from Utils.data_loader_with_threads import get_cmadaas_monthly_data
from Utils.data_processing import monthly_data_processing
from Utils.get_local_data import get_local_data
from Module00.wrapped.check import check
from Module04.wrapped.return_period_snow import calc_return_period_snow
from Report.code.Module04.re_snow import re_snow_report,re_snow_report_pg
from Report.code.Module04.re_frs import re_frs_report,re_frs_report_pg
from Utils.get_url_path import save_cmadaas_data


def callback(url, result_id, result):
    header = {'Content-Type': 'application/json'}
    _json = {"id": result_id, "status": "finish", "results": result}

    if url is None:
        return
    requests.put(url, headers=header, data=json.dumps(_json))


class workerReturnSnow:

    def act(self, jsons):
        json_str = jsons
        code = 200
        msg = '获取数据成功'

        # 1.读取json中的信息
        data_json = json.loads(json_str)
        element = data_json.get('element', 'snow')
        years = data_json['years']
        main_station = data_json['main_station']  # 参证站
        return_period_flag = data_json['return_period_flag']  # 重现期/频率 0 or 1
        return_period = data_json['return_period']
        fitting_method = data_json['fitting_method']
        CI = data_json.get('CI')  # 置信区间
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

        # 2.拼接需要下载的参数
        if element == 'snow':
            monthly_elements = 'Snow_Depth_Max'
        elif element == 'frs':
            monthly_elements = 'FRS_Depth_Max'
        
        # 4.数据获取
        if cfg.INFO.READ_LOCAL:
            month_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,' + monthly_elements).split(',')
            monthly_df = pd.read_csv(cfg.FILES.QH_DATA_MONTH, low_memory=False)
            monthly_df = get_local_data(monthly_df, main_station, month_eles, years, 'Month')
        else:
            try:  # 天擎数据下载 and 数据前处理
                monthly_df = get_cmadaas_monthly_data(years, monthly_elements, main_station)
                monthly_df = monthly_data_processing(monthly_df, years)
            except Exception as e:
                logging.exception(e)
                raise Exception('天擎数据获取失败')

        # 5.生成结果
        # 新增月数据转年数据
        yearly_df = monthly_df.resample('1A').max()

        try:
            calc = calc_return_period_snow(yearly_df, return_years, CI, fitting_method, data_dir, element)

            if element == 'snow':
                snow_result = calc.run_snow()
            elif element == 'frs':
                snow_result = calc.run_frs()
            snow_result['uuid'] = uuid4

            try:
                if element == 'snow':
                    if len(fitting_method)==2:              
                        report_path = re_snow_report(snow_result,yearly_df,data_dir)
                        report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                        snow_result['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
                    else:
                        report_path = re_snow_report_pg(snow_result,yearly_df,fitting_method[0],data_dir)
                        report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                        snow_result['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
                        
                elif element == 'frs':
                    if len(fitting_method)==2:              
                        report_path = re_frs_report(snow_result,yearly_df,data_dir)
                        report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                        snow_result['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
                    else:
                        report_path = re_frs_report_pg(snow_result,yearly_df,fitting_method[0],data_dir)
                        report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                        snow_result['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
                    
            except Exception as e:
                print(f"{element}:重现期报告 发生了错误：{e}")
                snow_result['report'] = None

            # url替换
            for key, sub_dict in snow_result.items():
                if key == 'img_save_path':
                    try:
                        for name, path in sub_dict.items():
                            path = path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)  # 图片容器内转容器外路径
                            sub_dict[name] = path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
                    except:
                        pass
            
            # module00完整率统计
            years_split = years.split(',')
            snow_result.check_result = edict()
            if monthly_df is not None and len(monthly_df) != 0:
                checker = check(monthly_df, 'MS', monthly_elements.split(','), [main_station], years_split[0], years_split[1])
                snow_result.check_result['使用的天擎月要素'] = checker.run()
                
            # 6.结果保存
            if cfg.INFO.SAVE_RESULT:
                snow_result['csv'] = save_cmadaas_data(data_dir, mon_data=monthly_df)

        except Exception as e:
            logging.exception(e)
            raise Exception('现有获取的数据不能满足重现期计算条件，无法得到计算结果')

        # 转成JSON字符串
        return_data = simplejson.dumps({'code': code, 'msg': msg, 'data': snow_result}, ensure_ascii=False, ignore_nan=True)
        callback(callback_url, result_id, return_data)

        # return_data保存pickle
        # with open(data_dir+'/return_data.txt', 'wb') as f:
        #     pickle.dump(return_data, f)

        return return_data


if __name__ == '__main__':
    
    data_json={
      "element":'frs',
      "years": "2000,2020",
      "main_station": "52874",
      "staValueName": [
        "青海省",
        "海东市",
        "乐都区",
        "52874"
      ],
      "stationName": "[52874]乐都",
      "staValue": "国家站",
      "return_period_flag": 0,
      "return_period": [
        2,
        3,
        5,
        10,
        20,
        30,
        50,
        100
      ],
      "CI": [],
      "fitting_method": [
        "Gumbel",
        "P3"
      ],
      "fmethod": [
        "耿贝尔法",
        "皮尔逊Ⅲ型"
      ],
      "checkeddMethod": "重现期",
      "checkedEle": [
        "气压",
        "风速"
      ]
    }