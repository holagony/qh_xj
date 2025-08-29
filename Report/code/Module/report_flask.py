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
from Report.code.Module.report_handler import combine_deal

module09 = Blueprint('module_report', __name__)


@module09.route('/v1/combine_report', methods=['post'])
def run_report():
    '''
    
    同步/异步
    '''
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    data_json = json.loads(json_str)
    is_async = data_json.get('is_async')

    if is_async == 1 or is_async is True or is_async == '1':
        result = celery_submit.delay('workerReport', json_str)
        return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})

    else:  # 同步
        result_dict = combine_deal(data_json)
        return_data = simplejson.dumps({'code': 200, 'msg': 'success', 'data': result_dict}, ensure_ascii=False, ignore_nan=True)
        return return_data


