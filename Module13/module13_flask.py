import os
import json
import simplejson
from flask import Blueprint, request, jsonify
from tasks.dispatcher_worker import celery_submit, celery_task_status
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Module13.wrapped.step1_divide_rain import get_minute_rain_seq

module13 = Blueprint('module13', __name__)


def rain_step1_1(json_str):
    '''
    暴雨公式步骤1_1，读取步骤1输出的pickle文件，
    输入年份/间隔/第几场雨，输出该场雨的分钟级序列变化表
    '''
    if json_str:
        code = 200
        msg = '获取数据成功'

        # 1.读取json中的信息
        data_json = json.loads(json_str)
        pickle_path = data_json['pickle_path']
        year = data_json['year']
        inr = data_json['rain_inr']
        num_idx = data_json['num_idx']

        # 2.得到结果 get_minute_rain_seq包含异常处理
        rain = get_minute_rain_seq(pickle_path, year, inr, num_idx)
        rain = rain.to_dict(orient='records')

    else:
        code = 500
        msg = '获取数据失败'
        rain = None

    # 转成JSON字符串
    return_data = simplejson.dumps({'code': code, 'msg': msg, 'data': rain}, ensure_ascii=False, ignore_nan=True)

    return return_data


@module13.route('/v1/rf_entrypoint', methods=['POST'])
def rf_entrypoint():
    '''
    step=1 场雨划分 + 年最大值/多样本
    step=2 频率曲线 + 暴雨公式
    step=3 芝加哥 or 同频率
    step='detail' 输出场雨详情
    '''
    json_str = request.get_data(as_text=True)  # 获取JSON字符串
    data_json = json.loads(json_str)
    step = data_json['step']

    if step == 1:
        result = celery_submit.delay("workerRainA", json_str)
        return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})

    elif step == 2:
        result = celery_submit.delay("workerRainB", json_str)
        return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})

    elif step == 3:
        result = celery_submit.delay("workerRainC", json_str)
        return jsonify({'code': 202, 'msg': '任务提交成功，开始计算...', 'data': {'task_id': result.id}})

    elif step == 'detail':
        return rain_step1_1(json_str)
