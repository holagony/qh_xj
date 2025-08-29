import json
import logging
import simplejson
from flask import Blueprint, request, jsonify
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from tasks.dispatcher_worker import celery_submit
from Module11.module11_handler import data_upload_handler, data_set_height_handler, data_quality_check_handler, data_params_stats1_handler, data_params_stats2_handler

module11 = Blueprint('module11', __name__)


@module11.route('/v1/data_upload', methods=['POST'])
def data_upload():
    '''
    测风塔数据读取解析入库接口
    '''
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    data_json = json.loads(json_str)
    is_async = data_json.get('is_async')
    if is_async == 1 or is_async is True or is_async == '1':
        result = celery_submit.delay('workerWindA', json_str)
        return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})

    data_upload_handler(data_json)
    return_data = simplejson.dumps({'code': 200, 'msg': '数据入库成功'}, ensure_ascii=False, ignore_nan=True)
    return return_data


@module11.route('/v1/data_set_height', methods=['POST'])
def data_set_height():
    '''
    测风塔数据修改高度接口
    '''
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    data_json = json.loads(json_str)
    is_async = data_json.get('is_async')
    if is_async == 1 or is_async is True or is_async == '1':
        result = celery_submit.delay('workerWindB', json_str)
        return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})

    data_set_height_handler(data_json)
    return_data = simplejson.dumps({'code': 200, 'msg': '修改高度成功'}, ensure_ascii=False, ignore_nan=True)
    return return_data


@module11.route('/v1/data_quality_check', methods=['POST'])
def data_quality_check():
    '''
    子页面1接口
    测风塔数据质量检验(缺测时间统计+有效数据完整率)
    '''
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    data_json = json.loads(json_str)
    is_async = data_json.get('is_async')
    if is_async == 1 or is_async is True or is_async == '1':
        result = celery_submit.delay('workerWindC', json_str)
        return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})

    result_dict = data_quality_check_handler(data_json)
    return_data = simplejson.dumps({'code': 200, 'msg': 'success', 'data': result_dict}, ensure_ascii=False, ignore_nan=True)
    return return_data


@module11.route('/v1/data_params_stats1', methods=['POST'])
def data_params_stats1():
    '''
    子页面2接口
    数据选择(从数据库)
    风速&风功率参数统计
    '''
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    data_json = json.loads(json_str)
    is_async = data_json.get('is_async')
    if is_async == 1 or is_async is True or is_async == '1':
        result = celery_submit.delay('workerWindD', json_str)
        return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})

    result_dict = data_params_stats1_handler(data_json)
    return_data = simplejson.dumps({'code': 200, 'msg': 'success', 'data': result_dict}, ensure_ascii=False, ignore_nan=True)
    return return_data


@module11.route('/v1/data_params_stats2', methods=['POST'])
def data_params_stats2():
    '''
    子页面3接口
    数据选择(从数据库)
    风能参数&风频率曲线统计
    '''
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    data_json = json.loads(json_str)
    is_async = data_json.get('is_async')
    if is_async == 1 or is_async is True or is_async == '1':
        result = celery_submit.delay('workerWindE', json_str)
        return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})

    result_dict = data_params_stats2_handler(data_json)
    return_data = simplejson.dumps({'code': 200, 'msg': 'success', 'data': result_dict}, ensure_ascii=False, ignore_nan=True)
    return return_data