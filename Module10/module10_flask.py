# -*- coding: utf-8 -*-
"""
Created on Thu Feb 22 14:34:49 2024

@author: EDY
"""

import os
import json
import time
import simplejson
import logging
from flask import Blueprint, request, jsonify
from tasks.dispatcher_worker import celery_submit, celery_task_status
from Module10.module10_handler import light_disater_deal, light_risk_deal, light_statistics_deal

module10 = Blueprint('module10', __name__)


@module10.route('/v1/statistics', methods=['post'])
def run_statistics():
    '''
    雷电统计
    同步/异步
    '''
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    data_json = json.loads(json_str)
    is_async = data_json.get('is_async')

    if is_async == 1 or is_async is True or is_async == '1':
        result = celery_submit.delay('workerStatistics', json_str)
        return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})
    else:  # 同步
        result_dict = light_statistics_deal(data_json)
        return_data = simplejson.dumps({'code': 200, 'msg': 'success', 'data': result_dict}, ensure_ascii=False, ignore_nan=True)
        return return_data


@module10.route('/v1/risk', methods=['post'])
def run_risk():
    '''
    区域雷电灾害风险评估

    '''
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    data_json = json.loads(json_str)
    is_async = data_json.get('is_async')

    if is_async == 1 or is_async is True or is_async == '1':
        result = celery_submit.delay('workerRisk', json_str)
        return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})
    else:  # 同步
        result_dict = light_risk_deal(data_json)
        return_data = simplejson.dumps({'code': 200, 'msg': 'success', 'data': result_dict}, ensure_ascii=False, ignore_nan=True)
        return return_data


# @module10.route('/v1/disater', methods=['post'])
# def run_disater():
#     '''
#     雷电灾害风险等级
#     同步/异步
#     '''
#     json_str = request.get_data(as_text=True)  # 获取JSON字符串
#     data_json = json.loads(json_str)
#     is_async = data_json.get('is_async')

#     if is_async == 1 or is_async is True or is_async == '1':
#         result = celery_submit.delay('workerDisater', json_str)
#         return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})
#     else:  # 同步
#         result_dict = light_disater_deal(data_json)
#         return_data = simplejson.dumps({'code': 200, 'msg': 'success', 'data': result_dict}, ensure_ascii=False, ignore_nan=True)
#         return return_data
