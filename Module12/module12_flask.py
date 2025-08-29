import os
import uuid
import json
import simplejson
import numpy as np
import pandas as pd
from datetime import timedelta
from flask import Blueprint, request, jsonify
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from tasks.dispatcher_worker import celery_submit, celery_task_status
from Module12.module12_handler import radiation_handler

module12 = Blueprint('module12', __name__)


@module12.route('/v1/radiation', methods=['POST'])
def radiation():
    '''
    辐射统计接口
    '''
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    data_json = json.loads(json_str)
    is_async = data_json.get('is_async')
    if is_async == 1 or is_async is True or is_async == '1':
        result = celery_submit.delay('workerRadiation', json_str)
        return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})

    result_dict = radiation_handler(data_json)
    return_data = simplejson.dumps({'code': 200, 'msg': 'success', 'data': result_dict}, ensure_ascii=False, ignore_nan=True)

    return return_data
