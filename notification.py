import sys,os
import requests
from requests.structures import CaseInsensitiveDict

def send_feishu(title=None,link=None):
    url = "https://www.feishu.cn/flow/api/trigger-webhook/a02be1e4229390baad907861213cd4c3"

    headers = CaseInsensitiveDict()
    headers["Content-Type"] = "application/json"

    data = '{"events":[{"id":"%s","name":"%s"}]}'%(link,title)
    resp = requests.post(url, headers=headers, data=data)
    print(resp)

send_feishu("ttt222tt","https://www.qq22.com")