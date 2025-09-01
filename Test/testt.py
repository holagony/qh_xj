import requests
import json

# 服务器地址
BASE_URL = "http://localhost:5050"  # 根据实际地址修改

# 请求数据
data = {
    "sta_ids": '52866',
    "years": "1993,2020",
    "elements": "PRS"}

# 发送POST请求
url = f"{BASE_URL}/module02/v1/feature_stats"
headers = {'Content-Type': 'application/json'}

try:
    response = requests.post(url, json=data, headers=headers, timeout=30)
    response.raise_for_status()
    
    result = response.json()
    print("请求成功:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
except requests.exceptions.RequestException as e:
    print(f"请求失败: {e}")
except json.JSONDecodeError as e:
    print(f"JSON解析失败: {e}")
    print(f"响应内容: {response.text}")