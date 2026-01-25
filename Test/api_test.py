import os
import requests
import json

# 接口地址
url1 = "http://127.0.0.1:5000/module14/v1/base"

# 请求头，指定内容类型为JSON
headers = {
    "Content-Type": "application/json"
}

# 请求参数
data={
  "years": "1985,2009",
  "station_ids": "52754",
  "sub_sta_ids": "52863,52866",
  "elements": ["TEM","WIND","PRE","FRS","SNOW"],
  "is_async": 0
}

# 发送POST请求
response1 = requests.post(url1, headers=headers, data=json.dumps(data))
file_path = os.path.join(os.path.dirname(__file__), "response1.json")
with open(file_path, "w", encoding="utf-8") as f:
    json.dump(response1.json(), f, ensure_ascii=False, indent=2)

# 打印响应状态码和响应内容
print(f"Status Code: {response1.status_code}")
print(f"Response Body: {response1.json()}")
