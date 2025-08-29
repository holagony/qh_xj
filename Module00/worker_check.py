import json
import logging
import os
import numpy as np
import pandas as pd
import requests
import simplejson

from Module00.wrapped.check import check
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict


def callback(url, result_id, result):
    header = {'Content-Type': 'application/json'}
    _json = {"id": result_id, "status": "finish", "results": result}

    if url is None:
        return
    requests.put(url, headers=header, data=json.dumps(_json))


class workerCheck:

    def act(self, jsons):
        json_str = jsons
        code = 200
        msg = '获取数据成功'

        # 1.读取json中的信息
        data_json = json.loads(json_str)

        result_id = data_json.get('id')
        callback_url = data_json.get('callback')
        data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, result_id)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        date_type = data_json['date_type']
        elements = data_json['elements']
        sta_ids = data_json['sta_ids']
        start_date = data_json['start_date']
        end_date = data_json['end_date']
        df = pd.read_csv(f'data_dir')
        check_day = check(df, date_type, elements, sta_ids, start_date, end_date)
        result = check_day.run()

        return_data = simplejson.dumps({'code': code, 'msg': 'check', 'data': result}, ensure_ascii=False, ignore_nan=True)
        callback(callback_url, result_id, return_data)

        # return_data保存pickle
        # with open(data_dir + '/return_data.txt', 'wb') as f:
        #     pickle.dump(return_data, f)

        return return_data
