import sys

import requests
from bs4 import BeautifulSoup
import csv
import time,json
import datetime,glob,os
import FutuMysql
MAX_HISTORY_LENGTH = 3000

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
        if len(cols) >= 5:
            ##['ARDR', '0.8561', '2,019,069.96', '3,803,650.48', '1,170,700,323', '9.64%']
            rows.append([cols[2].text.strip().replace("/KRW",""), float(cols[3].text.strip().replace("¥","").replace(",", "")),float(cols[4].text.strip().replace("¥","").replace(",", "")),float(cols[5].text.strip().replace("¥","").replace(",", "")),float(cols[6].text.strip().replace("¥","").replace(",", "")),float(cols[7].text.strip().replace("¥","").replace("%", ""))])
        #if len(cols) >= 3:
        #    rows.append([cols[2].text.strip().replace("/KRW",""), cols[-2].text.strip()])
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
    try:
        response = requests.post(url, data=json.dumps(data), headers=headers)
        return response.status_code == 200
    except:
        print("error post and sleep 60s")
        time.sleep(60)
        try:
            response = requests.post(url, data=json.dumps(data), headers=headers)
            return response.status_code == 200
        except:
            print("error post")
            return 0

def compare_data(old_data, new_data):
    if not old_data:
        return True
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

def initialize_stock(stock, volumnpercent):
    return {
        'data': [],
        'volumnpercent_increase_count': 0,
        'twopercent_difference_negative_count': 0,
        'volumnpercent_decrease_count': 0,
        'twopercent_difference_positive_count': 0,
        'prev_volumnpercent': volumnpercent,
        'eq_volumn':0,
        'acc_positive': False,
        'acc_negative': False
    }

def process_row(stock_history, row):
    try:
        stock, price, twopercentplus, twopercentdeplus, volumn, volumnpercent = row
        twopercentplus, twopercentdeplus, volumn, volumnpercent = map(float, [twopercentplus, twopercentdeplus, volumn, volumnpercent])
    except ValueError:
        print("Invalid row data:", row)
        return
    except TypeError:
        print("Row does not contain six elements:", row)
        return

    if stock not in stock_history and volumnpercent > 0.5:
        stock_history[stock] = initialize_stock(stock, volumnpercent)

    if stock in stock_history:
        stock_history[stock]['data'].append(row)
        if len(stock_history[stock]['data']) > 30:
            del stock_history[stock]['data'][:10]
        update_counts(stock_history[stock], twopercentplus, twopercentdeplus, volumnpercent)
        check_opportunities(stock_history[stock], stock)

def update_counts(stock_info, twopercentplus, twopercentdeplus, volumnpercent):
    if volumnpercent > stock_info['prev_volumnpercent']:
        stock_info['volumnpercent_increase_count'] += 1
        stock_info['volumnpercent_decrease_count'] = 0
        stock_info['eq_volumn'] = 0
    elif volumnpercent < stock_info['prev_volumnpercent']:
        stock_info['volumnpercent_increase_count'] = 0
        stock_info['volumnpercent_decrease_count'] += 1
        stock_info['eq_volumn'] = 0
    else:
        stock_info['eq_volumn'] += 1
        if stock_info['eq_volumn'] > 3:
            stock_info['volumnpercent_decrease_count'] = 0
            stock_info['volumnpercent_increase_count'] = 0
    stock_info['prev_volumnpercent'] = volumnpercent

    if twopercentdeplus - twopercentplus < -10000:
        if stock_info["acc_negative"]:
            stock_info["acc_negative"] = False
        if stock_info['twopercent_difference_positive_count'] > 9:
            stock_info["acc_positive"] = True
            stock_info["acc_negative"] = False
        stock_info['twopercent_difference_negative_count'] += 1
        stock_info['twopercent_difference_positive_count'] = 0

    elif twopercentdeplus - twopercentplus > 0:
        if stock_info["acc_positive"]:
            stock_info["acc_positive"] = False
        if stock_info['twopercent_difference_negative_count'] > 9:
            stock_info["acc_positive"] = False
            stock_info["acc_negative"] = True
        stock_info['twopercent_difference_negative_count'] = 0
        stock_info['twopercent_difference_positive_count'] += 1

def check_opportunities(stock_info, stock):
    print(stock_info)
    if stock_info['volumnpercent_increase_count'] >= 3 and stock_info['twopercent_difference_negative_count'] >= 2 and stock_info["acc_positive"]:
        print(datetime.datetime.now().strftime("%Y%m%d%H%M%S"),"发现做多机会",stock_info)
        print("股票: ", stock + ','.join(map(str, [data[1] for data in stock_info['data'][-2:]])))
        send_push_notification("做多:"+stock, "最近三次volumnpercent:" + ', '.join(map(str, [data[5] for data in stock_info['data'][-3:]])) +
                       " 最近三次deep: " + ', '.join(map(str, [data[3] - data[2] for data in stock_info['data'][-3:]])))

    if stock_info['volumnpercent_decrease_count'] >= 3 and stock_info['twopercent_difference_positive_count'] >= 3 and stock_info["acc_negative"]:
        print(datetime.datetime.now().strftime("%Y%m%d%H%M%S"),"发现做空机会",stock_info)
        print("股票: ", stock + ','.join(map(str, [data[1] for data in stock_info['data'][-2:]])))
        send_push_notification("做空:" + stock, "最近三次volumnpercent:" + ', '.join(map(str, [data[5] for data in stock_info['data'][-3:]])) +
                       " 最近三次deep: " + ', '.join(map(str, [data[3] - data[2] for data in stock_info['data'][-3:]])))

url = "https://coinmarketcap.com/zh/exchanges/upbit/"
last_rows =[]# fetch_and_parse(url)
send_push_notification("begin to monitor",datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
futu_sqlite = FutuMysql.FutuMysql()
stock_history = {}
while True:
    rows = fetch_and_parse(url)

    if compare_data(last_rows, rows):  # 检查是否有超过5%的变化
        for row in rows:
            futu_sqlite.insert_coinmarketcap_data(str(row[0]),str(row[1]),str(row[2]),str(row[3]),str(row[4]),str(row[5]))
            process_row(stock_history, row)

        #send_push_notification(
        #    rows[0][0] + " %.2f"%rows[0][-1] + "|" + rows[1][0] + " %.2f"%rows[1][-1] + "|" + rows[2][0] + " %.2f"%rows[2][-1],
        #    str(rows[0:5]))

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        save_to_csv(f'table_{timestamp}.csv', rows)
        delete_oldest_csv()
        last_rows = rows
    time.sleep(20)  # 每20秒执行一次