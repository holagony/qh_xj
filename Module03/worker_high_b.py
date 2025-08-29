import json
import simplejson
import requests
from Module03.module03_handler import init_and_end_days


def callback(url, result_id, result):
    header = {'Content-Type': 'application/json'}
    _json = {"id": result_id, "status": "finish", "results": result}
    if url is None:
        return
    requests.put(url, headers=header, data=json.dumps(_json))


class workerHighB:

    def act(self, json_str):
        data_json = json.loads(json_str)
        result_id = data_json.get('id')
        callback_url = data_json.get('callback')
        result_dict = init_and_end_days(data_json)
        return_data = simplejson.dumps({'code': 200, 'msg': 'success', 'data': result_dict}, ensure_ascii=False, ignore_nan=True)
        callback(callback_url, result_id, return_data)
        return return_data
