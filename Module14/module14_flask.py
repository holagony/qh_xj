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
from Module14.base_element_handler import feature_stats_handler
from Module14.return_element_handler import workerReturnWind

module14 = Blueprint('module14', __name__)


@module14.route('/v1/base', methods=['post'])
def run_base():
    '''
    基本气象条件分析
    '''
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    data_json = json.loads(json_str)
    is_async = data_json.get('is_async')

    if is_async == 1 or is_async is True or is_async == '1':
        result = celery_submit.delay('workerBase', json_str)
        return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})
    else:  # 同步
        result_dict = feature_stats_handler(data_json)
        return_data = simplejson.dumps({'code': 200, 'msg': 'success', 'data': result_dict}, ensure_ascii=False, ignore_nan=True)
        return return_data


@module14.route('/v1/return', methods=['post'])
def run_return():
    '''
    极端气象参数推算

    '''
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    data_json = json.loads(json_str)
    is_async = data_json.get('is_async')

    if is_async == 1 or is_async is True or is_async == '1':
        result = celery_submit.delay('workerReturn', json_str)
        return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})
    else:  # 同步
        result_dict = workerReturnWind(data_json)
        return_data = simplejson.dumps({'code': 200, 'msg': 'success', 'data': result_dict}, ensure_ascii=False, ignore_nan=True)
        return return_data