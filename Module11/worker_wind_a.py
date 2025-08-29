import json
import simplejson
import requests
from Module11.module11_handler import data_upload_handler


def callback(url, result_id, result):
    header = {'Content-Type': 'application/json'}
    _json = {"id": result_id, "status": "finish", "results": result}
    if url is None:
        return
    requests.put(url, headers=header, data=json.dumps(_json))


class workerWindA:

    def act(self, json_str):
        data_json = json.loads(json_str)
        result_id = data_json.get('id')
        callback_url = data_json.get('callback')
        _, _ = data_upload_handler(data_json)
        return_data = simplejson.dumps({'code': 200, 'msg': 'success'}, ensure_ascii=False, ignore_nan=True)
        callback(callback_url, result_id, return_data)
        return return_data
