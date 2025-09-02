# -*- coding: utf-8 -*-
"""
Created on Mon Sep  1 15:57:50 2025

@author: hx
"""

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
from Utils.data_loader_with_threads import get_cmadaas_monthly_data,get_cmadaas_daily_data
from Utils.data_processing import monthly_data_processing,daily_data_processing
from Utils.get_local_data import get_local_data
from Module00.wrapped.check import check
from Module04.wrapped.return_period_days import calc_return_period_days
from Report.code.Module04.re_day import re_day_report,re_day_report_pg
from Utils.get_url_path import save_cmadaas_data

def callback(url, result_id, result):
    header = {'Content-Type': 'application/json'}
    _json = {"id": result_id, "status": "finish", "results": result}

    if url is None:
        return
    requests.put(url, headers=header, data=json.dumps(_json))


class workerReturnDays:

    def act(self, jsons):
        json_str = jsons
        code = 200
        msg = '获取数据成功'

        # 1.读取json中的信息
        data_json = json.loads(json_str)
        element = data_json.get('element', 'PRE_Time_2020')
        years = data_json['years']
        main_station = data_json['main_station']  # 参证站
        return_period_flag = data_json.get('return_period_flag',0)  # 重现期/频率 0 or 1
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
        if element == 'Thund_Days':
            monthly_elements = 'Thund_Days,'
        elif element == 'SaSt_Days':
            monthly_elements = 'SaSt_Days,'
        elif element == 'FISa_Days':
            monthly_elements = 'FISa_Days,'
        elif element == 'FIDu_Days':
            monthly_elements = 'FIDu_Days,'
        elif element == 'Hail_Days':
            monthly_elements = 'Hail_Days,'
        elif element == 'GSS_Days':
            monthly_elements = 'GSS_Days,'
        elif element == 'Snow_Days':
            monthly_elements = 'Snow_Days,'
        elif element == 'PRE_Time_2020':
            monthly_elements = 'PRE_Time_2020,'

        
        # 4.数据获取
        if cfg.INFO.READ_LOCAL:
            if element in ['Thund_Days','SaSt_Days','FISa_Days','FIDu_Days','Hail_Days','GSS_Days','Snow_Days']:
                month_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,' + monthly_elements[:-1]).split(',')
                monthly_df = pd.read_csv(cfg.FILES.QH_DATA_MONTH, low_memory=False)
                monthly_df = get_local_data(monthly_df, main_station, month_eles, years, 'Month')
            else:
                day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,' + monthly_elements[:-1]).split(',')
                daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY, low_memory=False)
                daily_df = get_local_data(daily_df, main_station, day_eles, years, 'Day')

        else:
            try:  # 天擎数据下载 and 数据前处理
                if element in ['Thund_Days','SaSt_Days','FISa_Days','FIDu_Days','Hail_Days','GSS_Days','Snow_Days']:
                    monthly_df = get_cmadaas_monthly_data(years, monthly_elements, main_station)
                    monthly_df = monthly_data_processing(monthly_df, years)
                else:
                    daily_df = get_cmadaas_daily_data(years, monthly_elements, main_station)
                    daily_df = daily_data_processing(daily_df, years)
                    
            except Exception as e:
                logging.exception(e)
                raise Exception('天擎数据获取失败')

        # 5.生成结果
        # 新增月数据转年数据
        if element in ['Thund_Days','SaSt_Days','FISa_Days','FIDu_Days','Hail_Days','GSS_Days','Snow_Days']:
            
            yearly_df = monthly_df.resample('1A').sum()
            yearly_df['Station_Name'] = monthly_df['Station_Name'].iloc[0]
            yearly_df['Station_Id_C'] = monthly_df['Station_Id_C'].iloc[0]
        else:
            daily_df[element]=(daily_df[element]>= 24.1).astype(int)
            yearly_df = daily_df.resample('1A').sum()
            yearly_df['Station_Name'] = daily_df['Station_Name'].iloc[0]
            yearly_df['Station_Id_C'] = daily_df['Station_Id_C'].iloc[0]


            
        try:
            calc = calc_return_period_days(yearly_df, return_years, CI, fitting_method, data_dir, element)
            day_result = calc.run_days()
  
            try:
                if len(fitting_method)==2:              
                    report_path = re_day_report(element,day_result,yearly_df,data_dir)
                    report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                    day_result['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
                else:
                    report_path = re_day_report_pg(element,day_result,yearly_df,fitting_method[0],data_dir)
                    report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                    day_result['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)

            except Exception as e:
                print(f"{element}:重现期报告 发生了错误：{e}")
                day_result['report'] = None

            # url替换
            for key, sub_dict in day_result.items():
                if key == 'img_save_path':
                    try:
                        for name, path in sub_dict.items():
                            path = path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)  # 图片容器内转容器外路径
                            sub_dict[name] = path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
                    except:
                        pass
            
            # module00完整率统计
            years_split = years.split(',')
            day_result.check_result = edict()
            try:
                if monthly_df is not None and len(monthly_df) != 0:
                    checker = check(monthly_df, 'MS', monthly_elements.split(','), [main_station], years_split[0], years_split[1])
                    day_result.check_result['使用的天擎月要素'] = checker.run()
            except:
                pass
            
            try:
                if daily_df is not None and len(daily_df) != 0:
                    checker = check(daily_df, 'D', monthly_elements.split(','), [main_station], years_split[0], years_split[1])
                    check_result = checker.run()
                    day_result.check_result['使用的天擎日要素'] = check_result
            except:
                pass
                
            # 6.结果保存
            if cfg.INFO.SAVE_RESULT:
                try:
                    day_result['csv'] = save_cmadaas_data(data_dir, mon_data=monthly_df)
                except:
                    day_result['csv'] = save_cmadaas_data(data_dir, day_data=daily_df)


        except Exception as e:
            logging.exception(e)
            raise Exception('现有获取的数据不能满足重现期计算条件，无法得到计算结果')

        # 转成JSON字符串
        return_data = simplejson.dumps({'code': code, 'msg': msg, 'data': day_result}, ensure_ascii=False, ignore_nan=True)
        callback(callback_url, result_id, return_data)

        # return_data保存pickle
        # with open(data_dir+'/return_data.txt', 'wb') as f:
        #     pickle.dump(return_data, f)

        return return_data


if __name__ == '__main__':
    
    data_json={
      "element":'PRE_Time_2020',
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
        "Gumbel"
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