import sys,os
import requests,json
from requests.structures import CaseInsensitiveDict

def send_feishu(title=None,link=None):
    url = "https://www.feishu.cn/flow/api/trigger-webhook/a02be1e4229390baad907861213cd4c3"

    headers = CaseInsensitiveDict()
    headers["Content-Type"] = "application/json"
    data = '{"events":[{"id":"%s","name":"%s"}]}'%(link,title)
    #data = json.dumps(data)
    data = data.encode("utf-8")
    resp = requests.post(url, headers=headers, data=data, verify=False)
    print(resp.content)

#send_feishu("** dist0.387,reprice56.88,revol5052000,suggestbuy平安法兴二二熊A.P HK.53497","https://www.qq22.com")
