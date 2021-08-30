import sys,os

def send_feishu(title=None,link=None):
    cmd = """curl --header "Content-Type: application/json" --request POST --data '%s' https://www.feishu.cn/flow/api/trigger-webhook/a02be1e4229390baad907861213cd4c3"""
    content = """{"events":[{"id":"%s","name":"%s"}]}"""%(link,title)
    print(cmd % content)
    os.system(cmd%content)

send_feishu("ttttt","https://www.qq.com")