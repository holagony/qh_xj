# -*- coding: utf-8 -*-
"""
Created on Thu Feb 22 15:28:40 2024

@author: EDY
"""

import json
import simplejson
import requests
from Module14.base_element_handler import feature_stats_handler


def callback(url, result_id, result):
    header = {'Content-Type': 'application/json'}
    _json = {"id": result_id, "status": "finish", "results": result}
    if url is None:
        return
    requests.put(url, headers=header, data=json.dumps(_json))


class workerBase:

    def act(self, json_str):
        data_json = json.loads(json_str)
        result_dict = feature_stats_handler(data_json)
        return_data = simplejson.dumps({'code': 200, 'msg': 'success', 'data': result_dict}, ensure_ascii=False, ignore_nan=True)
        result_id = data_json.get('id')
        callback_url = data_json.get('callback')
        callback(callback_url, result_id, return_data)

        return return_data
