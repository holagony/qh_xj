import json
import simplejson
from flask import Blueprint, request, jsonify
from tasks.dispatcher_worker import celery_submit, celery_task_status
from Module02.module02_handler import feature_stats_handler

module02 = Blueprint('module02', __name__)

@module02.route('/v1/feature_stats', methods=['POST'])
def feature_stats():
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    data_json = json.loads(json_str)
    is_async = data_json.get('is_async')

    if is_async == 1 or is_async is True or is_async == '1':  # 异步
        result = celery_submit.delay('workerBasic', json_str)
        return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})

    else:  # 同步
        result_dict = feature_stats_handler(data_json)
        return_data = simplejson.dumps({'code': 200, 'msg': 'success', 'data': result_dict}, ensure_ascii=False, ignore_nan=True)
        return return_data


@module02.route('/ip')
def get_ip():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    return f"Client IP: {client_ip}\n"
