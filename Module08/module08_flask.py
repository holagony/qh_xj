import json
import simplejson
from flask import Blueprint, request, jsonify
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from tasks.dispatcher_worker import celery_submit, celery_task_status
from Module08.module08_handler import airport_wind_ds_handler, airport_wind_loading_handler

module08 = Blueprint('module08', __name__)


@module08.route('/v1/airport_wind_ds', methods=['POST'])
def airport_wind_ds():
    '''
    计算机场-统计不同风速区间的风向接口
    '''
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    data_json = json.loads(json_str)
    is_async = data_json.get('is_async')
    if is_async == 1 or is_async is True or is_async == '1':
        result = celery_submit.delay('workerAirportWind', json_str)
        return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})

    result_dict = airport_wind_ds_handler(data_json)
    return_data = simplejson.dumps({'code': 200, 'msg': 'success', 'data': result_dict}, ensure_ascii=False, ignore_nan=True)
    return return_data


@module08.route('/v1/airport_wind_loading', methods=['POST'])
def airport_wind_loading():
    '''
    计算满足最大允许侧风值的侧风数，和相应的风保障率接口
    不用数据前处理
    '''
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    data_json = json.loads(json_str)
    is_async = data_json.get('is_async')
    if is_async == 1 or is_async is True or is_async == '1':
        result = celery_submit.delay('workerAirportWindLoading', json_str)
        return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})

    result_dict = airport_wind_loading_handler(data_json)
    return_data = simplejson.dumps({'code': 200, 'msg': 'success', 'data': result_dict}, ensure_ascii=False, ignore_nan=True)
    return return_data
