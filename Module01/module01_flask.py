import os
import json
import logging
import simplejson
from flask import Blueprint, request, jsonify, current_app
from tasks.dispatcher_worker import celery_submit, celery_task_status
from Module01.module01_handler import time_consistency_handler, spatial_consistency_handler, calc_correlation_daily_data_handler

module01 = Blueprint('module01', __name__)


# 时间一致性分析
@module01.route('/v1/time_consistency', methods=['POST'])
def time_consistency():
    '''
    mk突变检验和滑动T检验接口
    '''
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    data_json = json.loads(json_str)
    is_async = data_json.get('is_async')
    if is_async == 1 or is_async is True or is_async == '1':
        result = celery_submit.delay('workerTime', json_str)
        return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})

    result_dict = time_consistency_handler(data_json)
    return_data = simplejson.dumps({'code': 200, 'msg': 'success', 'data': result_dict}, ensure_ascii=False, ignore_nan=True)
    return return_data


# 空间一致性分析
@module01.route('/v1/spatial_consistency', methods=['POST'])
def spatial_consistency():
    '''
    独立T检验和F检验接口，年/月数据
    '''
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    data_json = json.loads(json_str)
    is_async = data_json.get('is_async')
    if is_async == 1 or is_async is True or is_async == '1':
        result = celery_submit.delay('workerSpace', json_str)
        return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})

    result_dict = spatial_consistency_handler(data_json)
    return_data = simplejson.dumps({'code': 200, 'msg': 'success', 'data': result_dict}, ensure_ascii=False, ignore_nan=True)
    return return_data


# 要素相关性分析
@module01.route('/v1/calc_correlation', methods=['POST'])
def calc_correlation_daily_data():
    '''
    相关性分析接口，小时和日数据
    '''
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    data_json = json.loads(json_str)
    is_async = data_json.get('is_async')
    if is_async == 1 or is_async is True or is_async == '1':
        result = celery_submit.delay('workerCorrelation', json_str)
        return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})

    result_dict = calc_correlation_daily_data_handler(data_json)
    return_data = simplejson.dumps({'code': 200, 'msg': 'success', 'data': result_dict}, ensure_ascii=False, ignore_nan=True)
    return return_data
