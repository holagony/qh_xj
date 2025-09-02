import logging
import os
import json
import simplejson
from flask import Blueprint, request, jsonify, current_app
from tasks.dispatcher_worker import celery_submit, celery_task_status
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Module04.wrapped.p3_change_params import p3_calc

module04 = Blueprint('module04', __name__)


@module04.route('/v1/return_period_pre', methods=['POST'])
def rp_pre():
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    result = celery_submit.delay("workerReturnPre", json_str)
    return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})


@module04.route('/v1/return_period_snow', methods=['POST'])
def rp_snow():
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    result = celery_submit.delay("workerReturnSnow", json_str)
    return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})


@module04.route('/v1/return_period_tem', methods=['POST'])
def rp_tem():
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    result = celery_submit.delay("workerReturnTem", json_str)
    return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})


@module04.route('/v1/rp_wind_entrypoint', methods=['POST'])
def rp_wind():
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    result = celery_submit.delay("workerReturnWind", json_str)
    return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})

@module04.route('/v1/return_period_day', methods=['POST'])
def rp_day():
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    result = celery_submit.delay("workerReturnDays", json_str)
    return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})

@module04.route('/v1/p3', methods=['POST'])
def p3p3():
    json_str = request.get_data(as_text=True)  # 获取JSON字符串

    if json_str:
        code = 200
        msg = '获取数据成功'

        # 1.读取json中的信息
        data_json = json.loads(json_str)
        filename = data_json.get('id')
        element = data_json['element']
        mode = data_json['mode']
        cs_cv = data_json.get('cs_cv')

        # 生成结果
        p3_result = p3_calc(filename, element, mode, cs_cv)
        p3_result['input'] = edict()
        p3_result['input']['id'] = filename
        p3_result['input']['element'] = element
        p3_result['input']['mode'] = mode
        p3_result['input']['cs_cv'] = cs_cv

        for name, path in p3_result.items():
            if name == 'img_save_path':
                p3_result['img_save_path'] = path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_URL)
    else:
        code = 500
        msg = '获取数据失败'
        p3_result = None

    # 转成JSON字符串
    return_data = simplejson.dumps({'code': code, 'msg': msg, 'data': p3_result}, ensure_ascii=False, ignore_nan=True)

    return return_data
