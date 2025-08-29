import os
import json
import simplejson
from collections import OrderedDict
from flask import Blueprint, request, jsonify
from tasks.dispatcher_worker import celery_submit, celery_task_status
from Module07.module07_handler import garden_city_handler, heat_island_handler


module07 = Blueprint('module07', __name__)


@module07.route('/v1/garden_city', methods=['POST'])
def garden_city():
    '''
    园林城市热岛接口
    主站和副站排列组合，如果所有主站或所有副站都没数据，则结果表全是nan
    '''
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    data_json = json.loads(json_str)
    is_async = data_json.get('is_async')
    if is_async == 1 or is_async is True or is_async == '1':
        result = celery_submit.delay('workerGardenCity', json_str)
        return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})

    result_dict = garden_city_handler(data_json)
    return_data = simplejson.dumps({'code': 200, 'msg': 'success', 'data': result_dict}, ensure_ascii=False, ignore_nan=True)
    return return_data


@module07.route('/v1/heat_island', methods=['POST'])
def heat_island():
    '''
    气象站热岛接口
    主站和副站排列组合，如果所有主站或所有副站都没数据，则结果表全是nan
    '''
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    data_json = json.loads(json_str)
    is_async = data_json.get('is_async')
    if is_async == 1 or is_async is True or is_async == '1':
        result = celery_submit.delay('workerHeatIsland', json_str)
        return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})

    result_dict = heat_island_handler(data_json)
    return_data = simplejson.dumps({'code': 200, 'msg': 'success', 'data': result_dict}, ensure_ascii=False, ignore_nan=True)
    return return_data