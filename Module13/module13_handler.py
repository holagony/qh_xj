import os
import uuid
import platform
import logging
import glob
import json
import simplejson
import numpy as np
import pandas as pd
from flask import Blueprint, request, jsonify
from tasks.dispatcher_worker import celery_submit, celery_task_status
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Module13.wrapped.step1_divide_rain import step1_run, get_minute_rain_seq
from Module13.wrapped.step2_rain_strength import step2_run
from Module13.wrapped.step3_return_period import step3_run
from Module13.wrapped.step4_rain_formula import step4_run
from Module13.wrapped.step5_chicago import step5_run_chicago
from Module13.wrapped.step5_samefreq import step5_run_samefreq
from Report.code.Module13.step_1_report import step_1_report
from Report.code.Module13.step_2_report import step_2_report
from Report.code.Module13.step_3_report import step_3_report


def rain_step1(data_json):
    '''
    暴雨公式步骤1
    场雨划分 样本推求
    '''
    input_path = data_json['input_path']
    pre_threshold = data_json['pre_threshold']
    start_year = data_json.get('start_year')
    end_year = data_json.get('end_year')

    # 参数处理
    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)  # 保存文件路径，容器内
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    logging.info(input_path)
    print('初始输入路径是：' + input_path)
    print('-----------')

    input_path = input_path.replace(cfg.INFO.OUT_UPLOAD_FILE, cfg.INFO.IN_UPLOAD_FILE)  # inupt_path要转换为容器内的路径

    if '\\' in input_path:
        input_path = input_path.replace('\\', '/') # windows to linux

    print('容器内路径是: ' + input_path)

    # if os.path.isfile(input_path):  #.dat
    #     input_path = {'R': input_path}
    # elif os.path.isdir(input_path):
        # input_path = {'J': os.path.join(input_path, 'J'), 'R': glob.glob(os.path.join(input_path,'R','*.DAT'))[0]}
    # input_path = {'J': os.path.join(input_path, 'J')}
    
    J_path = os.path.join(input_path, 'J')
    R_path = os.path.join(input_path, 'R')

    input_path = dict()
    if os.path.exists(J_path):
        input_path['J'] = J_path
        
    if os.path.exists(R_path):
        R_path = glob.glob(os.path.join(R_path, '*.DAT'))[0]
        input_path['R'] = R_path

    print('处理后的分钟数据路径是:')
    print(input_path)

    # 生成结果
    # 输出的给后续步骤计算的pickle和csv文件路径都在容器内，不用改动
    try:
        result_1, start_year_out, end_year_out, st_id = step1_run(input_path, data_dir, pre_threshold, start_year, end_year)  # 划分场雨
        result_2, _ = step2_run(result_1['pickle'], data_dir, start_year_out, end_year_out)  # 最大值/年多样本计算
        report_path = step_1_report(result_1, start_year_out, end_year_out, result_2, data_dir)

        # 结果保存
        result_dict = edict()
        result_dict['uuid'] = uuid4
        result_dict['part1'] = result_1
        result_dict['part2'] = result_2
        result_dict['report'] = report_path  # 不用url转换

        # 新增返回信息
        info = '站点' + str(st_id) + '-起始年份' + str(start_year_out) + '-结束年份' + str(end_year_out) + ',' + uuid4
        result_dict['info'] = info

    except Exception as e:
        logging.exception(e)
        raise

    return result_dict


def rain_step2(data_json):
    '''
    暴雨公式步骤2 
    频率曲线推求 暴雨强度公式计算
    '''
    mode = data_json['mode']  # gumbel--0 p3--4 指数--6
    data_flag = data_json['data_flag']  # 0--短历时/1--长历时
    sample_flag = data_json['sample_flag']  # 0--年最大值/1--年多样本
    uuid_step1 = data_json['uuid_step1']

    # doc_dir = data_json['doc_dir']  # step 1 ：报告生成路径
    # step2_csv = data_json['step2_csv']  # 年最大值 or 年多样本

    # 参数处理
    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)  # 保存文件路径，容器内
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    if sample_flag == 0:
        step2_csv = os.path.join(cfg.INFO.IN_DATA_DIR, uuid_step1, 'single_sample.csv')
    else:
        step2_csv = os.path.join(cfg.INFO.IN_DATA_DIR, uuid_step1, 'multi_sample.csv')

    step1_doc = os.path.join(cfg.INFO.IN_DATA_DIR, uuid_step1, 'rain_step_1.docx')

    # 结果生成
    try:
        result, pre_data = step3_run(data_flag, data_dir, mode, manual_cs_cv=None, step2_csv=step2_csv)  # 频率曲线拟合
        table = result['return_table']
        result_formula = step4_run(table)
        report_path = step_2_report(data_flag, step2_csv, mode, step1_doc, result, pre_data, result_formula, data_dir)  # 暴雨强度公式计算

        for key, sub_dict in result.items():
            if 'min' in key:
                for key1, path in sub_dict.items():
                    if key1 == 'img_save_path':
                        path = path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)  # 图片容器内转容器外路径
                        sub_dict[key1] = path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)  # 容器外路径转url
            if key == 'all_in_one':
                sub_dict = sub_dict.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                result[key] = sub_dict.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)

        # 结果保存
        result_dict = edict()
        result_dict['uuid'] = uuid4
        result_dict['part1'] = result
        result_dict['part2'] = result_formula
        result_dict['data_flag'] = data_flag
        result_dict['report'] = report_path  # 不用url转换

        # 新增返回信息
        if sample_flag == 0:
            info1 = '年最大值样本'
        elif sample_flag == 1:
            info1 = '年多个样本'

        if mode == 0:
            info2 = '耿贝尔法'
        elif mode == 2:
            info2 = '皮尔逊III型法'
        elif mode == 6:
            info2 = '指数法'
        
        if data_flag == 0:
            info3 = '短历时'
        elif data_flag == 1:
            info3 = '长历时'

        info = info1 + '-' + info2 + '-' + info3 + ',' + uuid4
        result_dict['info'] = info

    except Exception as e:
        logging.exception(e)
        raise

    return result_dict


def rain_step3(data_json):
    '''
    暴雨公式步骤3
    芝加哥/同频率雨型计算
    '''
    rain_type = data_json['rain_type']  # 0芝加哥/1同频率
    uuid_step1 = data_json['uuid_step1']
    uuid_step2 = data_json['uuid_step2']

    # 以下参数界面没有 通过uuid_step2定位到相应返回结果
    param_A = data_json['param_A']
    param_b = data_json['param_b']
    param_C = data_json['param_C']
    param_n = data_json['param_n']
    data_flag = data_json['data_flag']

    # pickle_path = data_json['pickle_path']
    # doc_dir = data_json['doc_dir']  # step 2 ：报告生成路径

    # 参数处理
    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)  # 保存文件路径，容器内
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    pickle_path = os.path.join(cfg.INFO.IN_DATA_DIR, uuid_step1, 'step1_result.txt')
    step2_doc = os.path.join(cfg.INFO.IN_DATA_DIR, uuid_step2, 'rain_step_2.docx')

    # 结果生成
    if rain_type == 0:
        chicago_times = [60, 90, 120, 150, 180]
        result_dict = step5_run_chicago(pickle_path, chicago_times, param_A, param_b, param_C, param_n, data_dir)

        try:
            report_path = step_3_report(data_flag, step2_doc, result_dict, data_dir)
            report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
            result_dict['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
        except Exception as e:
            logging.exception(e)
            result_dict['report'] = None

    elif rain_type == 1:
        rain10_path = os.path.join(data_dir, 'rain10')  # 同频率雨型10场1440雨保存路径，容器内
        if not os.path.exists(rain10_path):
            os.makedirs(rain10_path)
        result_dict, _ = step5_run_samefreq(pickle_path, rain10_path, param_A, param_b, param_C, param_n, data_dir)
        result_dict['report'] = None
        # todo 增加后续报告

    for key, path in result_dict['img_save_path'].items():
        path = path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)  # 图片容器内转容器外路径
        result_dict['img_save_path'][key] = path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)  # 容器外路径转url

    result_dict['uuid'] = uuid4

    return result_dict


def rain_step1_1(json_str):
    '''
    暴雨公式步骤1_1，读取步骤1输出的pickle文件，
    输入年份/间隔/第几场雨，输出该场雨的分钟级序列变化表
    '''
    if json_str:
        code = 200
        msg = '获取数据成功'

        # 1.读取json中的信息
        data_json = json.loads(json_str)
        pickle_path = data_json['pickle_path']
        year = data_json['year']
        inr = data_json['rain_inr']
        num_idx = data_json['num_idx']

        # 2.得到结果 get_minute_rain_seq包含异常处理
        rain = get_minute_rain_seq(pickle_path, year, inr, num_idx)
        rain = rain.to_dict(orient='records')

    else:
        code = 500
        msg = '获取数据失败'
        rain = None

    # 转成JSON字符串
    return_data = simplejson.dumps({'code': code, 'msg': msg, 'data': rain}, ensure_ascii=False, ignore_nan=True)

    return return_data
