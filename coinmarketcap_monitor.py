import sys

import requests
from bs4 import BeautifulSoup
import csv
import time,json
import datetime,glob,os


def fetch_and_parse(url):
    # 请求网页
    response = requests.get(url)

    # 使用 BeautifulSoup 解析网页
    soup = BeautifulSoup(response.text, 'html.parser')

    # 如果网页上有多个表格，通过调整这个索引来选择正确的一个
    table_index = 0

    # 找到所有的表格
    tables = soup.find_all('table')

    # 解析表格，只保留“交易对”和“交易量 %”列
    rows = []
    table = tables[table_index]
    for row in table.find_all('tr'):
        cols = row.find_all('td')
        if len(cols) >= 3:
            rows.append([cols[2].text.strip().replace("/KRW",""), cols[-2].text.strip()])

    return rows


def save_to_csv(filename, rows):
    # 写入 CSV 文件
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['交易对', '交易量 %'])
        writer.writerows(rows)

def send_push_notification(title, text):
    # 发送推送通知
    uuid = "5d39a06ab000bfc"
    uids = "UID_orEZQ6VndpKe46Tt-CIVFxqPR4iY_N"
    url = "https://courier.toptopn.com/api/v1/cui/notify/push"
    data = {
        'uuid': uuid,
        'title': title,
        'text': text,
        'uids': uids
    }
    headers = {'Content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    return response.status_code == 200

def compare_data(old_data, new_data):
    # 检查两个数据集之间是否有超过5%的变化
    change_count = 0
    for row in new_data:
        if row not in old_data:
            change_count += 1
    for row in old_data:
        if row not in new_data:
            change_count += 1
    print("begin to compare,change_count",change_count,len(old_data))
    return change_count / len(old_data) > 0.05

def delete_oldest_csv():
    files = glob.glob("*.csv")
    if len(files) > 100:
        files.sort(key=os.path.getmtime)
        os.remove(files[0])

url = "https://coinmarketcap.com/zh/exchanges/upbit/"
last_rows = fetch_and_parse(url)
send_push_notification("begin to monitor",datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
while True:
    rows = fetch_and_parse(url)

    if compare_data(last_rows, rows):  # 检查是否有超过5%的变化
        send_push_notification(
            rows[0][0] + " " + rows[0][1] + "|" + rows[1][0] + " " + rows[1][1] + "|" + rows[2][0] + " " + rows[2][1],
            str(rows[0:5]))
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        save_to_csv(f'table_{timestamp}.csv', rows)
        delete_oldest_csv()
        last_rows = rows
    time.sleep(20)  # 每20秒执行一次