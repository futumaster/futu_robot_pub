"""
Summary: 从港交所和富途的数据中找符合条件的，可以short的股票并存放到股票列表中
"""
####可空地址：
# https://www.hkex.com.hk/-/media/HKEX-Market/Services/Trading/Securities/Securities-Lists/Designated-Securities-Eligible-for-Short-Selling/ds_list20201223_c.csv?la=zh-HK
# https://www.hkex.com.hk/-/media/HKEX-Market/Services/Trading/Securities/Securities-Lists/Designated-Securities-Eligible-for-Short-Selling/ds_list20201224_c.csv?la=zh-HK

import time,sys
from futu import *
import pickle
import talib
import datetime
import urllib.request
import csv

def get_socket_list(quote_ctx, market=Market.US):
    """
    找监控符合条件的美股/港股
    :param quote_ctx: 基础context
    :param market: 选择市场，Market.US, Market.HK
    :return: 全部符合条件的股票snapshot
    """
    socket_list = []
    ##10亿市值以下
    simple_filter = SimpleFilter()
    simple_filter.filter_max = 2000000000
    simple_filter.stock_field = StockField.MARKET_VAL
    simple_filter.is_no_filter = False
    simple_filter.sort = SortDir.ASCEND
    ##56周距离最高价格-20%
    price_filter = SimpleFilter()
    price_filter.filter_max = -10
    price_filter.stock_field = StockField.CUR_PRICE_TO_HIGHEST52_WEEKS_RATIO
    price_filter.is_no_filter = False
    ##亏损的烂货
    ttm_filter = SimpleFilter()
    ttm_filter.filter_max = 0
    ttm_filter.stock_field = StockField.PE_TTM
    ttm_filter.is_no_filter = False
    #仅200日有-10%的跌幅
    change_filter = AccumulateFilter()
    change_filter.is_no_filter = False
    change_filter.stock_field = StockField.CHANGE_RATE
    change_filter.filter_max = -20
    change_filter.days = 90
    ##最近2天只有-2%～2%的涨跌幅
    #change2_filter = AccumulateFilter()
    #change2_filter.is_no_filter = False
    #change2_filter.stock_field = StockField.CHANGE_RATE
    #change2_filter.filter_max = 2
    #change2_filter.filter_min = -2
    #change2_filter.days = 2
    ##最近250日振幅12%以上
    change1_filter = AccumulateFilter()
    change1_filter.is_no_filter = False
    change1_filter.stock_field = StockField.AMPLITUDE
    change1_filter.filter_max = 8
    change1_filter.days = 2

    start_page = 0
    while True:
        ret, ls = quote_ctx.get_stock_filter(market, [simple_filter,price_filter,ttm_filter,change1_filter,change_filter],begin=start_page, num=200)
        if ret == RET_OK:
            last_page, all_count, ret_list = ls
            print(len(ret_list), all_count, ret_list)
            for item in ret_list:
                #print(item.stock_code)  # 取其中的股票代码
                socket_list.append(item.stock_code)
            if all_count-start_page > 0:
                start_page = start_page + 200
            else:
                return socket_list
        else:
            print('error: ', ls)

def read_cache(cache_name):
    cache_dict = []
    if os.path.exists(cache_name + '.pkl'):
        with open(cache_name + '.pkl','rb') as f:
            cache_dict = pickle.load(f)
            if not cache_dict:
                cache_dict = []
    return cache_dict

def save_cache(cache_name, cache):
    with open(cache_name + '.pkl', 'wb') as f:
        pickle.dump(cache, f, pickle.HIGHEST_PROTOCOL)

def list_of_groups(init_list, childern_list_len):
    list_of_group = zip(*(iter(init_list),) *childern_list_len)
    end_list = [list(i) for i in list_of_group]
    count = len(init_list) % childern_list_len
    end_list.append(init_list[-count:]) if count !=0 else end_list
    return end_list

def get_short_sell_socket(quote_ctx, socket_list):
    short_sell_sockets = []
    print("socket_list len:", len(socket_list), "socket list", socket_list)
    groups = list_of_groups(socket_list, 400)
    for group in groups:
        ret, data = quote_ctx.get_market_snapshot(group)
        if ret == RET_OK:
            socket = data[(data["enable_short_sell"] == True) & (data["short_sell_rate"] < 8)].to_dict("records")
            if socket:
                short_sell_sockets = short_sell_sockets + socket
        else:
            print('error:', data)
    return short_sell_sockets

def get_short_socket(default_day = "20210126"):
    baseurl = "https://www.hkex.com.hk/-/media/HKEX-Market/Services/Trading/Securities/Securities-Lists/Designated-Securities-Eligible-for-Short-Selling/ds_list%s_c.csv?la=zh-HK"
    ###eg:20201223
    result = None
    try:
        today = datetime.datetime.today().strftime('%Y%m%d')
        print("获取空股：",baseurl%today)
        f = urllib.request.urlopen(
            baseurl%today)
        result = f.read().decode('utf-8')
        print("csv结果",result)
    except:
        print("当天获取失败，获取默认日期空股：",baseurl%default_day)
        f = urllib.request.urlopen(
            baseurl%default_day)
        result = f.read().decode('utf-8')
        print("csv结果",result)
    if result:
        sockets = []
        result = result.split("\r\n")
        for line in result:
            if "股本證券" not in line:
                continue
            args = line.split(",")
            sockets.append("HK.%05d" % int(args[1]))
        return sockets
    return None

def full_update_security(quote_ctx, new_code_list, user_security="short1224"):
    ret, data = quote_ctx.get_user_security(user_security)
    if ret != RET_OK:
        print('error:', data)
        sys.exit()
    code_list = data['code'].values.tolist()
    quote_ctx.modify_user_security(user_security, ModifyUserSecurityOp.DEL, code_list)
    ret, data = quote_ctx.modify_user_security(user_security, ModifyUserSecurityOp.ADD, new_code_list)
    print("修改",user_security,ret)

short1224 = get_short_socket()
quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
socket_list_groups = list_of_groups(short1224,400)
new_socket_list = []
for socket_list in socket_list_groups:
    ret, ls = quote_ctx.get_market_snapshot(socket_list)
    if ret == 0:
        short_dicts = ls[(ls["open_price"] < 5) & (ls["total_market_val"] < 100000000000) & (ls["pe_ttm_ratio"] < 0) & (ls["pe_ratio"] < 0)]
        new_socket_list = new_socket_list + short_dicts['code'].values.tolist()
full_update_security(quote_ctx,new_socket_list, "short1224")
quote_ctx.close()
sys.exit()
short_sell_sockets = read_cache("short_sell_sockets_15")
short_sell_sockets = []
quote_ctx = None
if not short_sell_sockets:
    quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
    socket_list = get_socket_list(quote_ctx)
    short_sell_sockets = get_short_sell_socket(quote_ctx, socket_list)
    save_cache("short_sell_sockets_15",short_sell_sockets)
print(short_sell_sockets)
print(len(short_sell_sockets))
all_code = []
for so in short_sell_sockets:
    print(so)
    code = so['code']
    all_code.append(code)
if not quote_ctx:
    quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
if True:
    ret, data = quote_ctx.get_user_security("ShortSale")
    if ret != RET_OK:
        print('error:', data)
        sys.exit()
    code_list = data['code'].values.tolist()
    quote_ctx.modify_user_security("ShortSale", ModifyUserSecurityOp.DEL, code_list)
    ret, data = quote_ctx.modify_user_security("ShortSale", ModifyUserSecurityOp.ADD, all_code)
    if ret == RET_OK:
        print(data)  # 返回success
    else:
        print('error:', data)

code = all_code[0]
today = datetime.datetime.today()
pre_day = (today - datetime.timedelta(days=90)
           ).strftime('%Y-%m-%d')
end_dt = today.strftime('%Y-%m-%d')
ret_code, prices, page_req_key = quote_ctx.request_history_kline(code, start=pre_day, end=end_dt)
print(prices)
quote_ctx.close()  # 结束后记得关闭当条连接，防止连接条数用尽
