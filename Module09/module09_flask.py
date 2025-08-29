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
from Module09.module09_handler import gaussian_plume_deal, gaussian_puff_deal,pollute_deal

module09 = Blueprint('module09', __name__)


@module09.route('/v1/gaussian_puff', methods=['post'])
def run_gaussian_puff():
    '''
    高斯烟团模型
    同步/异步
    '''
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    data_json = json.loads(json_str)
    is_async = data_json.get('is_async')

    if is_async == 1 or is_async is True or is_async == '1':
        result = celery_submit.delay('workerPuff', json_str)
        return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})

    else:  # 同步
        result_dict = gaussian_puff_deal(data_json)
        return_data = simplejson.dumps({'code': 200, 'msg': 'success', 'data': result_dict}, ensure_ascii=False, ignore_nan=True)
        return return_data


@module09.route('/v1/gaussian_plume', methods=['post'])
def run_gaussian_plume():
    '''
    高斯烟羽模型
    同步/异步
    '''
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    data_json = json.loads(json_str)
    is_async = data_json.get('is_async')

    if is_async == 1 or is_async is True or is_async == '1':
        result = celery_submit.delay('workerPlume', json_str)
        return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})

    else:  # 同步
        result_dict = gaussian_plume_deal(data_json)
        return_data = simplejson.dumps({'code': 200, 'msg': 'success', 'data': result_dict}, ensure_ascii=False, ignore_nan=True)
        return return_data

@module09.route('/v1/pollute', methods=['post'])
def run_pollute():
    '''
    大气自净能力

    '''
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    data_json = json.loads(json_str)
    is_async = data_json.get('is_async')

    if is_async == 1 or is_async is True or is_async == '1':
        result = celery_submit.delay('workerPollute', json_str)
        return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})

    else:  # 同步
        result_dict = pollute_deal(data_json)
        return_data = simplejson.dumps({'code': 200, 'msg': 'success', 'data': result_dict}, ensure_ascii=False, ignore_nan=True)
        return return_data