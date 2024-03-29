##Done: 添加语音提醒，被kill的涡轮的价值是多少？
##TODO 20210220： 早上开盘的时候的波幅是完全不同的，需要验证策略，如果前15分钟往上杀，往下杀，可以考虑自动买入
##TODO 20210222:  如果发现连续下挫kill牛，有没有可能走买正股的方式， 加了，但是还是不对，会报错，数量不对
##TODO 20210226： snapshot请求次数过多
##TODO 20210308： 如果杀了一个涡轮，那么要看看下一阶段是不是马上接上，里面小于4%，是的话，就可以打小一点的价格，也影响正股票的反向买入
import time,sys
from futu import *
import csv
import platform
import FutuMysql
#import FutuSqlite
import requests
import smart_buy_and_sell
from subprocess import call
import computer_util
import stock_timer
import notification


def send_weixin(title=None,text=None):
    #send_feishu(title, "http://www.qq.com")
    if "Darwin" in platform.platform():
        cmd = 'display notification \"' + \
              "%s"%text + '\" with title \"%s\"'%title
        call(["osascript", "-e", cmd])
    if title == None and text == None:
        pass
    elif title!=None and text!=None:
        url='http://sc.ftqq.com/SCU65285T26329f59df97c83174fb42350f0df3e45db7db11b4f3a.send?text='+title+'&desp='+text
    else:
        url='http://sc.ftqq.com/SCU65285T26329f59df97c83174fb42350f0df3e45db7db11b4f3a.send?text='+title

    r=requests.get(url)

def get_focus_stock(quote_ctx):
    ret, data = quote_ctx.get_user_security("focus")
    if ret == RET_OK:
        print(data['code'].values.tolist())  # 转为list
    else:
        print('error:', data)
    focus = data['code'].values.tolist()
    return focus



def get_subscribe_stock(quote_ctx, stocks,street_min=8):
    # 选出有街货大于x%，接近x%回收价的正股与伴生反向操作涡轮，回收价位，正股做key
    res = {}
    remove_sockets = []
    buy_warrents = []
    for stock_num in stocks:
        req = WarrantRequest()
        req.sort_field = SortField.RECOVERY_PRICE

        req.type_list = [WrtType.BULL, WrtType.BEAR]
        req.street_min = street_min
        req.price_recovery_ratio_max = 5
        req.price_recovery_ratio_min = -5
        req.status = "NORMAL"
        ret, ls = quote_ctx.get_warrant(stock_owner=stock_num, req=req)
        time.sleep(0.3)
        if ret == RET_OK:  # 先判断接口返回是否正常，再取数据
            kill_warrant_data_list, last_page, all_count = ls

            if len(kill_warrant_data_list) > 0:
                filter_warrant_list = kill_warrant_data_list[
                    ["name", "stock", "recovery_price", "street_rate", "street_vol", "price_recovery_ratio","type"]].to_dict("records")
                print(filter_warrant_list)
                ##TODO:如果距离一样，或者相差不超过x，则街货的属性相加，选择最贴近的那个
                if kill_warrant_data_list["type"][0] == "BEAR":
                    res[stock_num] = filter_warrant_list[0]
                else:
                    res[stock_num] = filter_warrant_list[-1]
                print("获取贴价窝轮:",res[stock_num])

                req1 = WarrantRequest()
                req1.sort_field = SortField.VOLUME
                if kill_warrant_data_list["type"][0] == "BEAR":
                    req1.type_list = [WrtType.BULL, ]
                    req1.price_recovery_ratio_min = 5
                    req1.price_recovery_ratio_max = 15
                else:
                    req1.type_list = [WrtType.BEAR, ]
                    req1.price_recovery_ratio_max = -5
                    req1.price_recovery_ratio_min = -15
                req1.street_max = 1
                time_min = datetime.now() + timedelta(120)
                req1.maturity_timemin = time_min.strftime("%Y-%m-%d")
                req1.status = "NORMAL"
                ret, ls = quote_ctx.get_warrant(stock_owner=stock_num, req=req1)
                if ret == RET_OK:
                    warrant_data_list, last_page, all_count = ls
                    ##TODO：计算敏感度  正股最低买卖价位 x 对冲值delta(对冲值，仅认购认沽支持此字段) / 兌换比率（conversion_ratio） x 窝轮最低买卖价位
                    highscore_warrants = warrant_data_list.loc[
                        warrant_data_list["score"] > 70].to_dict("records")

                    if len(highscore_warrants) > 0:
                        res[stock_num]["buy"] = highscore_warrants[-1]
                    else:
                        if len(warrant_data_list.to_dict("records")) < 1:
                            req2 = WarrantRequest()
                            req2.sort_field = SortField.VOLUME
                            if kill_warrant_data_list["type"][0] == "BEAR":
                                req2.type_list = [WrtType.BULL, WrtType.CALL]
                            else:
                                req2.type_list = [WrtType.BEAR, WrtType.PUT]
                            req2.street_max = 3
                            req2.status = "NORMAL"
                            ret1, ls1 = quote_ctx.get_warrant(stock_owner=stock_num, req=req2)
                            if ret1 == RET_OK:
                                warrant_data_list1, last_page1, all_count1 = ls1
                                res[stock_num]["buy"] = warrant_data_list1.to_dict("records")[-1]
                        else:
                            res[stock_num]["buy"] = warrant_data_list.to_dict("records")[-1]
                    print("获取高分的窝轮:", res[stock_num]["buy"])
                    buy_warrents.append(res[stock_num]["buy"]["stock"])
                else:
                    print(ret,ls)
            else:
                print("no warrent data with", stock_num)
                #remove_sockets.append(stock_num)

    #if remove_sockets:
    #    quote_ctx.modify_user_security("focus", ModifyUserSecurityOp.DEL, remove_sockets)

    return res,buy_warrents

def subscribe_stock(quote_ctx, focus, buy_warrents):
    quote_ctx.subscribe(focus+buy_warrents, [SubType.ORDER_BOOK], subscribe_push=False)
    res = quote_ctx.subscribe(focus, [SubType.K_1M])
    return res

class CurKlineCallback(CurKlineHandlerBase):
    def get_lot_size(self,stock):
        for cache in self.caches:
            if cache['code'] == stock:
                return cache['lot_size']

    def __init__(self, subscribe_warrants, quote_ctx, caches, is_open_csv_logger=False):
        CurKlineHandlerBase.__init__(self)
        self.quote_ctx = quote_ctx
        self.subscribe_warrants = subscribe_warrants
        self.call_dict = {}
        self.is_stop = False
        self.futu_sqlite = None
        self.is_open_csv_logger = is_open_csv_logger
        self.caches = caches
        self.trigelist = []

        self.buyer = smart_buy_and_sell.SimpleBuyAndSell(quote_ctx)
        if self.is_open_csv_logger:
            self.logger = open("res%s.csv" % datetime.now().strftime('%H%M%S'), "w", newline='')
            self.logger_writer = csv.DictWriter(logger,
                                        fieldnames=['stock', 'open', 'close',
                                                    'high', 'low', 'volume',
                                                    'turnover', 'recover_price', 'recover_price_radio',
                                                    'recover_stock', 'street_rate', 'street_vol', 'type', 'isbuy',
                                                    'buyprice', 'buysocket'])
            self.logger_writer.writeheader()

    def state(self):
        return self.is_stop

    def real_log(self, cur_code, recover_price_radio, is_buy, buy_price, cur_kline, subscribe_warrant,order_vol_percent,order_vol):
        self.futu_sqlite.insert_ai_data(
            cur_code,
            cur_kline['open'],
            cur_kline['close'],
            cur_kline['high'],
            cur_kline['low'],
            cur_kline['volume'],
            cur_kline['turnover'],
            subscribe_warrant["recovery_price"],
            recover_price_radio,
            subscribe_warrant['stock'],
            subscribe_warrant['street_rate'],
            subscribe_warrant['street_vol'],
            subscribe_warrant["type"],
            is_buy,
            buy_price,
            subscribe_warrant["buy"]["stock"],
            order_vol_percent,
            order_vol
        )
        if self.is_open_csv_logger:
            self.logger_writer.writerow({'stock': cur_code,
                                         'open': cur_kline['open'],
                                         'close': cur_kline['close'],
                                         'high': cur_kline['high'],
                                         'low': cur_kline['low'],
                                         'volume': cur_kline['volume'],
                                         'turnover': cur_kline['turnover'],
                                         'recover_price': subscribe_warrant["recovery_price"],
                                         'recover_price_radio': recover_price_radio,
                                         'recover_stock': subscribe_warrant['stock'],
                                         'street_rate': subscribe_warrant['street_rate'],
                                         'street_vol': subscribe_warrant['street_vol'],
                                         'type': subscribe_warrant["type"], 'isbuy': 'true',
                                         'buyprice': buy_price,
                                         'buysocket': subscribe_warrant["buy"]["stock"]})

    def on_recv_rsp(self, rsp_str):
        ###初始化
        recover_price_radio = 1.0
        order_vol_percent, total_volumn, order_vol = 0,0,0
        if not self.futu_sqlite:
            self.futu_sqlite = FutuMysql.FutuMysql()

        ret_code, data = super(CurKlineCallback,self).on_recv_rsp(rsp_str)
        if ret_code != RET_OK:
            print("CurKlineTest: error, msg: %s" % data)
            return RET_ERROR, data

        cur_kline = data.to_dict("records")[0]
        cur_code = cur_kline["code"]
        if cur_code not in self.subscribe_warrants:
            print("没有要回收的涡轮 for",cur_code)
            return

        ret, cur_order_book = self.quote_ctx.get_order_book(cur_code, num=10)
        if ret != RET_OK:
            print("CurKlineTest: error, msg: %s" % cur_order_book)

        subscribe_warrant = self.subscribe_warrants[cur_code]
        if subscribe_warrant["type"] == "BEAR":
            #如果被杀的是熊，则用回收价-最高价值
            recover_price_radio = float(subscribe_warrant["recovery_price"] - cur_kline["high"])/float(subscribe_warrant["recovery_price"])
            #print("BEAR 回收价相距", recover_price_radio, subscribe_warrant["recovery_price"], cur_kline["high"])
            order_book = cur_order_book["Ask"]
            order_vol_percent, total_volumn, order_vol = computer_util.count_recover_price_hardnum(order_book,subscribe_warrant["recovery_price"])
        else:
            recover_price_radio = float(cur_kline["low"] - subscribe_warrant["recovery_price"]) / float(
                subscribe_warrant["recovery_price"])
            #print("or",cur_order_book)
            order_book = cur_order_book["Bid"]
            order_vol_percent, total_volumn, order_vol = computer_util.count_recover_price_hardnum(order_book, subscribe_warrant["recovery_price"])

        ###距离回收价0.5%
        if recover_price_radio < 0.005:
            """
            ###判断是否已经进入过0.5%
            if subscribe_warrant["buy"]["stock"] in self.call_dict.keys():
                self.call_dict[subscribe_warrant["buy"]["stock"]] = self.call_dict[subscribe_warrant["buy"]["stock"]] + 1
                if self.call_dict[subscribe_warrant["buy"]["stock"]] < 3:
                    log = "距离%s,回收价%s,回收量%s,建议购买%s %s"%(str(round(float(recover_price_radio*100),3)),
                                                                       str(subscribe_warrant["recovery_price"]),
                                                                       str(subscribe_warrant["street_vol"]),
                                                                       str(subscribe_warrant["buy"]["name"]),
                                                                       subscribe_warrant["buy"]['stock'])
                    if self.call_dict[subscribe_warrant["buy"]["stock"]] <= 2:
                        self.buyer.buy(subscribe_warrant["buy"]['stock'],subscribe_warrant["buy"]["lot_size"],subscribe_warrant["type"],0.05)
                    print("** "+log)
                    send_weixin("** "+log)
                    os.system("say " + log)"""
            if subscribe_warrant["buy"]["stock"] not in self.call_dict.keys():
                ret, ls_data = self.quote_ctx.get_order_book(subscribe_warrant["buy"]["stock"], num=1)
                if ret == RET_OK:
                    log = "dist%s,reprice%s,revol%s,suggestbuy%s %s"%(str(round(float(recover_price_radio*100),3)),
                                                                       str(subscribe_warrant["recovery_price"]),
                                                                       str(subscribe_warrant["street_vol"]),
                                                                       str(subscribe_warrant["buy"]["name"]),
                                                                       subscribe_warrant["buy"]['stock'])
                    print("**",log)
                    notification.send_feishu(log, "http://www.qq.com")

                    self.real_log(cur_code, recover_price_radio, 'true',ls_data['Bid'][0][0],cur_kline, subscribe_warrant, order_vol_percent, order_vol)
                    #send_weixin("购买:"+subscribe_warrant["buy"]["stock"], "距离回收价: %f"%round(float(recover_price_radio*100),3))
                    self.buyer.buy(subscribe_warrant["buy"]['stock'], subscribe_warrant["buy"]["lot_size"],
                                   subscribe_warrant["type"], 0.05)
                    self.call_dict[subscribe_warrant["buy"]["stock"]] = 1
                else:
                    print("获取snapshot错误, 休息10s",ls_data)
                    time.sleep(10)

            if recover_price_radio <= 0:
                log = "%s trige %s reprice"%(cur_code, str(subscribe_warrant["recovery_price"]))
                ##卖涡轮
                if log not in self.trigelist:
                    self.trigelist.append(log)
                    self.buyer.sell(subscribe_warrant["buy"]['stock'])
                    ##买正股票
                    self.buyer.buy(cur_code, self.get_lot_size(cur_code),"normal",percentage=0.1)

                    notification.send_feishu("** " + log, "https://www.qq.com")
                    #os.system("say " + log)

                self.is_stop = True
        else:
            self.call_dict.pop(subscribe_warrant["buy"]["stock"], None)
            if cur_code in self.buyer.buy_records and self.buyer.buy_records[cur_code]["type"] == "normal":
                ###差距大于零，且是正股票，卖出
                if cur_kline["low"] - self.buyer.buy_records[cur_code]["buy_price"] > 0 and \
                   (cur_kline["low"] - self.buyer.buy_records[cur_code]["buy_price"])/cur_kline["low"] > 0.01:
                    self.buyer.sell(cur_code)
            if recover_price_radio < 0.02:
                ret, ls_data = self.quote_ctx.get_order_book(subscribe_warrant["buy"]["stock"], num=1)
                self.real_log(cur_code, recover_price_radio, 'false',ls_data['Bid'][0][0],cur_kline, subscribe_warrant, order_vol_percent, order_vol)

        return RET_OK, data

class SysNotifyTest(SysNotifyHandlerBase):
    def on_recv_rsp(self, rsp_str):
        ret_code, data = super(SysNotifyTest, self).on_recv_rsp(rsp_str)
        notify_type, sub_type, msg = data
        if ret_code != RET_OK:
            logger.debug("SysNotifyTest: error, msg: {}".format(msg))
            return RET_ERROR, data
        if (notify_type == SysNotifyType.GTW_EVENT):  # FutuOpenD 事件通知
            print("GTW_EVENT, type: {} msg: {}".format(sub_type, msg))
        elif (notify_type == SysNotifyType.PROGRAM_STATUS):  # 程序状态变化通知
            print("PROGRAM_STATUS, type: {} msg: {}".format(sub_type, msg))
        elif (notify_type == SysNotifyType.CONN_STATUS):  ## 连接状态变化通知
            print("CONN_STATUS, qot: {}".format(msg['qot_logined']))
            print("CONN_STATUS, trd: {}".format(msg['trd_logined']))
        elif (notify_type == SysNotifyType.QOT_RIGHT):  # 行情权限变化通知
            print("QOT_RIGHT, hk: {}".format(msg['hk_qot_right']))
            print("QOT_RIGHT, hk_option: {}".format(msg['hk_option_qot_right']))
            print("QOT_RIGHT, hk_future: {}".format(msg['hk_future_qot_right']))
            print("QOT_RIGHT, us: {}".format(msg['us_qot_right']))
            print("QOT_RIGHT, us_option: {}".format(msg['us_option_qot_right']))
            print("QOT_RIGHT, us_future: {}".format(msg['us_future_qot_right']))
            print("QOT_RIGHT, cn: {}".format(msg['cn_qot_right']))
        return RET_OK, data

def looper(quote_ctx, focus):
    sucess,data = quote_ctx.get_market_snapshot(focus)
    print(sucess,data)
    cache_records = data.to_dict("records")
    print(cache_records)

    res,buy_warrents = get_subscribe_stock(quote_ctx, focus)
    re_focus = list(res.keys())
    print("完整结果", res)
    print("需要关注的正股", re_focus)
    notification.send_feishu("begin:" + str(re_focus), "Subscribe")
    callback = CurKlineCallback(res, quote_ctx, cache_records)
    syscallback = SysNotifyTest()
    print("关注结果：", subscribe_stock(quote_ctx, re_focus, buy_warrents))
    quote_ctx.set_handlers([callback,syscallback])

    while True:
        time.sleep(20)
        if callback.is_stop or stock_timer.need_stop():
            print("looper",callback.is_stop, stock_timer.need_stop())
        if callback.is_stop:
            if stock_timer.need_stop():
                print("等待开市")
                continue
            print("反注册全部callback")
            os.system("say 反注册Callback")

            quote_ctx.unsubscribe_all()
            #quote_ctx.set_handler(None)
            time.sleep(5)
            res,buy_warrents = get_subscribe_stock(quote_ctx, focus)
            re_focus = list(res.keys())
            print("完整结果", res)
            print("需要关注的正股", re_focus)
            notification.send_feishu("begin:" + str(re_focus), "Subscribe")
            callback = CurKlineCallback(res, quote_ctx, cache_records)
            #syscallback = SysNotifyTest()
            print("关注结果：", subscribe_stock(quote_ctx, re_focus, buy_warrents))
            quote_ctx.set_handlers([callback,syscallback])

#time.sleep(11*60*60-40*60)
quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
stock_timer.wait_to_begin()
focus = get_focus_stock(quote_ctx)
looper(quote_ctx, focus)
#send_weixin("done","done")

"""******** 购买熊: {'stock': 'HK.68926', 'name': '美团高盛一七熊K.P', 'stock_owner': 'HK.03690', 'type': 'BEAR', 'issuer': 'GS', 'maturity_time': '2021-07-30', 'list_time': '2020-11-30', 'last_trade_time': '2021-07-29', 'recovery_price': 310.88, 'conversion_ratio': 500.0, 'lot_size': 5000, 'strike_price': 313.88, 'last_close_price': 0.04, 'cur_price': 0.04, 'price_change_val': 0.0, 'change_rate': 0.0, 'status': 'NORMAL', 'bid_price': 0.04, 'ask_price': 0.042, 'bid_vol': 15000000, 'ask_vol': 15000000, 'volume': 34480000, 'turnover': 1301545.0, 'score': 72.764, 'premium': 1.183, 'break_even_point': 293.88, 'leverage': 14.87, 'ipop': 5.25, 'price_recovery_ratio': -4.336078229541951, 'conversion_price': 20.0, 'street_rate': 0.0, 'street_vol': 0, 'amplitude': 0.0, 'issue_size': 100000000, 'high_price': 0.042, 'low_price': 0.029, 'implied_volatility': nan, 'delta': nan, 'effective_leverage': 14.87, 'list_timestamp': 1606665600.0, 'last_trade_timestamp': 1627488000.0, 'maturity_timestamp': 1627574400.0, 'upper_strike_price': nan, 'lower_strike_price': nan, 'inline_price_status': nan}
k线回调  {'code': 'HK.00941', 'time_key': '2020-11-30 14:46:00', 'open': 46.65, 'close': 46.7, 'high': 46.7, 'low': 46.65, 'volume': 4000, 'turnover': 186725.0, 'k_type': 'K_1M', 'last_close': 0.0}
BULL 回收价相距 0.02123467600700523 45.68 46.65
k线回调  {'code': 'HK.03690', 'time_key': '2020-11-30 14:46:00', 'open': 297.4, 'close': 297.6, 'high': 297.6, 'low': 297.4, 'volume': 9200, 'turnover': 2736200.0, 'k_type': 'K_1M', 'last_close': 0.0}
BULL 回收价相距 0.004729729729729653 296.0 297.4
******** 购买熊: {'stock': 'HK.68926', 'name': '美团高盛一七熊K.P', 'stock_owner': 'HK.03690', 'type': 'BEAR', 'issuer': 'GS', 'maturity_time': '2021-07-30', 'list_time': '2020-11-30', 'last_trade_time': '2021-07-29', 'recovery_price': 310.88, 'conversion_ratio': 500.0, 'lot_size': 5000, 'strike_price': 313.88, 'last_close_price': 0.04, 'cur_price': 0.04, 'price_change_val': 0.0, 'change_rate': 0.0, 'status': 'NORMAL', 'bid_price': 0.04, 'ask_price': 0.042, 'bid_vol': 15000000, 'ask_vol': 15000000, 'volume': 34480000, 'turnover': 1301545.0, 'score': 72.764, 'premium': 1.183, 'break_even_point': 293.88, 'leverage': 14.87, 'ipop': 5.25, 'price_recovery_ratio': -4.336078229541951, 'conversion_price': 20.0, 'street_rate': 0.0, 'street_vol': 0, 'amplitude': 0.0, 'issue_size': 100000000, 'high_price': 0.042, 'low_price': 0.029, 'implied_volatility': nan, 'delta': nan, 'effective_leverage': 14.87, 'list_timestamp': 1606665600.0, 'last_trade_timestamp': 1627488000.0, 'maturity_timestamp': 1627574400.0, 'upper_strike_price': nan, 'lower_strike_price': nan, 'inline_price_status': nan}
k线回调  {'code': 'HK.00700', 'time_key': '2020-11-30 14:46:00', 'open': 576.5, 'close': 577.0, 'high': 577.0, 'low': 576.5, 'volume': 29500, 'turnover': 17008800.0, 'k_type': 'K_1M', 'last_close': 0.0}
BULL 回收价相距 0.011403508771929825 570.0 576.5
k线回调  {'code': 'HK.00700', 'time_key': '2020-11-30 14:46:00', 'open': 576.5, 'close': 576.5, 'high': 577.0, 'low': 576.5, 'volume': 34300, 'turnover': 19776000.0, 'k_type': 'K_1M', 'last_close': 0.0}
BULL 回收价相距 0.011403508771929825 570.0 576.5
k线回调  {'code': 'HK.00175', 'time_key': '2020-11-30 14:46:00', 'open': 21.75, 'close': 21.8, 'high': 21.8, 'low': 21.75, 'volume': 25000, 'turnover': 544750.0, 'k_type': 'K_1M', 'last_close': 0.0}
BULL 回收价相距 0.0032287822878228913 21.68 21.75
******** 购买熊: {'stock': 'HK.66209', 'name': '吉利汇丰一七熊B.P', 'stock_owner': 'HK.00175', 'type': 'BEAR', 'issuer': 'HS', 'maturity_time': '2021-07-26', 'list_time': '2020-11-30', 'last_trade_time': '2021-07-23', 'recovery_price': 26.58, 'conversion_ratio': 50.0, 'lot_size': 50000, 'strike_price': 27.08, 'last_close_price': 0.116, 'cur_price': 0.116, 'price_change_val': 0.0, 'change_rate': 0.0, 'status': 'NORMAL', 'bid_price': 0.116, 'ask_price': 0.119, 'bid_vol': 6000000, 'ask_vol': 6000000, 'volume': 4000000, 'turnover': 440500.0, 'score': 48.8, 'premium': 2.385, 'break_even_point': 21.28, 'leverage': 3.758, 'ipop': 19.497, 'price_recovery_ratio': -17.983446200150482, 'conversion_price': 5.800000000000001, 'street_rate': 0.0, 'street_vol': 0, 'amplitude': 0.0, 'issue_size': 40000000, 'high_price': 0.115, 'low_price': 0.108, 'implied_volatility': nan, 'delta': nan, 'effective_leverage': 3.758, 'list_timestamp': 1606665600.0, 'last_trade_timestamp': 1626969600.0, 'maturity_timestamp': 1627228800.0, 'upper_strike_price': nan, 'lower_strike_price': nan, 'inline_price_status': nan}
k线回调  {'code': 'HK.00700', 'time_key': '2020-11-30 14:46:00', 'open': 576.5, 'close': 576.5, 'high': 577.0, 'low': 576.5, 'volume': 34400, 'turnover': 19833650.0, 'k_type': 'K_1M', 'last_close': 0.0}
BULL 回收价相距 0.011403508771929825 570.0 576.5
k线回调  {'code': 'HK.00941', 'time_key': '2020-11-30 14:46:00', 'open': 46.65, 'close': 46.65, 'high': 46.7, 'low': 46.65, 'volume': 5000, 'turnover': 233375.0, 'k_type': 'K_1M', 'last_close': 0.0}
BULL 回收价相距 0.02123467600700523 45.68 46.65
k线回调  {'code': 'HK.00700', 'time_key': '2020-11-30 14:46:00', 'open': 576.5, 'close': 576.5, 'high': 577.0, 'low': 576.5, 'volume': 35800, 'turnover': 20640750.0, 'k_type': 'K_1M', 'last_close': 0.0}
BULL 回收价相距 0.011403508771929825 570.0 576.5
k线回调  {'code': 'HK.00941', 'time_key': '2020-11-30 14:46:00', 'open': 46.65, 'close': 46.65, 'high': 46.7, 'low': 46.65, 'volume': 5500, 'turnover': 256700.0, 'k_type': 'K_1M', 'last_close': 0.0}
BULL 回收价相距 0.02123467600700523 45.68 46.65
k线回调  {'code': 'HK.00700', 'time_key': '2020-11-30 14:46:00', 'open': 576.5, 'close': 576.5, 'high': 577.0, 'low': 576.5, 'volume': 36600, 'turnover': 21101950.0, 'k_type': 'K_1M', 'last_close': 0.0}
BULL 回收价相距 0.011403508771929825 570.0 576.5
k线回调  {'code': 'HK.00941', 'time_key': '2020-11-30 14:46:00', 'open': 46.65, 'close': 46.65, 'high': 46.7, 'low': 46.65, 'volume': 6500, 'turnover': 303350.0, 'k_type': 'K_1M', 'last_close': 0.0}
BULL 回收价相距 0.02123467600700523 45.68 46.65
k线回调  {'code': 'HK.00700', 'time_key': '2020-11-30 14:46:00', 'open': 576.5, 'close': 576.5, 'high': 577.0, 'low': 576.5, 'volume': 36900, 'turnover': 21274900.0, 'k_type': 'K_1M', 'last_close': 0.0}
BULL 回收价相距 0.011403508771929825 570.0 576.5                         
k线回调  {'code': 'HK.00941', 'time_key': '2020-11-30 14:46:00', 'open': 46.65, 'close': 46.7, 'high': 46.7, 'low': 46.65, 'volume': 8000, 'turnover': 373400.0, 'k_type': 'K_1M', 'last_close': 0.0}
BULL 回收价相距 0.02123467600700523 45.68 46.65
k线回调  {'code': 'HK.00700', 'time_key': '2020-11-30 14:46:00', 'open': 576.5, 'close': 576.5, 'high': 577.0, 'low': 576.5, 'volume': 37100, 'turnover': 21390200.0, 'k_type': 'K_1M', 'last_close': 0.0}
BULL 回收价相距 0.011403508771929825 570.0 576.5
k线回调  {'code': 'HK.00941', 'time_key': '2020-11-30 14:46:00', 'open': 46.65, 'close': 46.65, 'high': 46.7, 'low': 46.65, 'volume': 11500, 'turnover': 536675.0, 'k_type': 'K_1M', 'last_close': 0.0}
BULL 回收价相距 0.02123467600700523 45.68 46.65
k线回调  {'code': 'HK.03690', 'time_key': '2020-11-30 14:46:00', 'open': 297.4, 'close': 297.6, 'high': 297.6, 'low': 297.4, 'volume': 9500, 'turnover': 2825480.0, 'k_type': 'K_1M', 'last_close': 0.0}
BULL 回收价相距 0.004729729729729653 296.0 297.4
******** 购买熊: {'stock': 'HK.68926', 'name': '美团高盛一七熊K.P', 'stock_owner': 'HK.03690', 'type': 'BEAR', 'issuer': 'GS', 'maturity_time': '2021-07-30', 'list_time': '2020-11-30', 'last_trade_time': '2021-07-29', 'recovery_price': 310.88, 'conversion_ratio': 500.0, 'lot_size': 5000, 'strike_price': 313.88, 'last_close_price': 0.04, 'cur_price': 0.04, 'price_change_val': 0.0, 'change_rate': 0.0, 'status': 'NORMAL', 'bid_price': 0.04, 'ask_price': 0.042, 'bid_vol': 15000000, 'ask_vol': 15000000, 'volume': 34480000, 'turnover': 1301545.0, 'score': 72.764, 'premium': 1.183, 'break_even_point': 293.88, 'leverage': 14.87, 'ipop': 5.25, 'price_recovery_ratio': -4.336078229541951, 'conversion_price': 20.0, 'street_rate': 0.0, 'street_vol': 0, 'amplitude': 0.0, 'issue_size': 100000000, 'high_price': 0.042, 'low_price': 0.029, 'implied_volatility': nan, 'delta': nan, 'effective_leverage': 14.87, 'list_timestamp': 1606665600.0, 'last_trade_timestamp': 1627488000.0, 'maturity_timestamp': 1627574400.0, 'upper_strike_price': nan, 'lower_strike_price': nan, 'inline_price_status': nan}
k线回调  {'code': 'HK.00981', 'time_key': '2020-11-30 14:46:00', 'open': 21.35, 'close': 21.3, 'high': 21.35, 'low': 21.3, 'volume': 23500, 'turnover': 501150.0, 'k_type': 'K_1M', 'last_close': 0.0}
BULL 回收价相距 0.01428571428571432 21.0 21.3
k线回调  {'code': 'HK.09988', 'time_key': '2020-11-30 14:46:00', 'open': 259.4, 'close': 259.6, 'high': 259.6, 'low': 259.4, 'volume': 11600, 'turnover': 3009340.0, 'k_type': 'K_1M', 'last_close': 0.0}
BULL 回收价相距 0.03186284259517082 251.39 259.4
k线回调  {'code': 'HK.03690', 'time_key': '2020-11-30 14:46:00', 'open': 297.4, 'close': 297.6, 'high': 297.6, 'low': 297.4, 'volume': 10500, 'turnover': 3123080.0, 'k_type': 'K_1M', 'last_close': 0.0}
BULL 回收价相距 0.004729729729729653 296.0 297.4
******** 购买熊: {'stock': 'HK.68926', 'name': '美团高盛一七熊K.P', 'stock_owner': 'HK.03690', 'type': 'BEAR', 'issuer': 'GS', 'maturity_time': '2021-07-30', 'list_time': '2020-11-30', 'last_trade_time': '2021-07-29', 'recovery_price': 310.88, 'conversion_ratio': 500.0, 'lot_size': 5000, 'strike_price': 313.88, 'last_close_price': 0.04, 'cur_price': 0.04, 'price_change_val': 0.0, 'change_rate': 0.0, 'status': 'NORMAL', 'bid_price': 0.04, 'ask_price': 0.042, 'bid_vol': 15000000, 'ask_vol': 15000000, 'volume': 34480000, 'turnover': 1301545.0, 'score': 72.764, 'premium': 1.183, 'break_even_point': 293.88, 'leverage': 14.87, 'ipop': 5.25, 'price_recovery_ratio': -4.336078229541951, 'conversion_price': 20.0, 'street_rate': 0.0, 'street_vol': 0, 'amplitude': 0.0, 'issue_size': 100000000, 'high_price': 0.042, 'low_price': 0.029, 'implied_volatility': nan, 'delta': nan, 'effective_leverage': 14.87, 'list_timestamp': 1606665600.0, 'last_trade_timestamp': 1627488000.0, 'maturity_timestamp': 1627574400.0, 'upper_strike_price': nan, 'lower_strike_price': nan, 'inline_price_status': nan}
k线回调  {'code': 'HK.00941', 'time_key': '2020-11-30 14:46:00', 'open': 46.65, 'close': 46.65, 'high': 46.7, 'low': 46.65, 'volume': 21000, 'turnover': 979850.0, 'k_type': 'K_1M', 'last_close': 0.0}
BULL 回收价相距 0.02123467600700523 45.68 46.65
k线回调  {'code': 'HK.00941', 'time_key': '2020-11-30 14:46:00', 'open': 46.65, 'close': 46.65, 'high': 46.7, 'low': 46.65, 'volume': 23500, 'turnover': 1096475.0, 'k_type': 'K_1M', 'last_close': 0.0}
BULL 回收价相距 0.02123467600700523 45.68 46.65
k线回调  {'code': 'HK.03690', 'time_key': '2020-11-30 14:46:00', 'open': 297.4, 'close': 297.4, 'high': 297.6, 'low': 297.4, 'volume': 10600, 'turnover': 3152820.0, 'k_type': 'K_1M', 'last_close': 0.0}
BULL 回收价相距 0.004729729729729653 296.0 297.4
******** 购买熊: {'stock': 'HK.68926', 'name': '美团高盛一七熊K.P', 'stock_owner': 'HK.03690', 'type': 'BEAR', 'issuer': 'GS', 'maturity_time': '2021-07-30', 'list_time': '2020-11-30', 'last_trade_time': '2021-07-29', 'recovery_price': 310.88, 'conversion_ratio': 500.0, 'lot_size': 5000, 'strike_price': 313.88, 'last_close_price': 0.04, 'cur_price': 0.04, 'price_change_val': 0.0, 'change_rate': 0.0, 'status': 'NORMAL', 'bid_price': 0.04, 'ask_price': 0.042, 'bid_vol': 15000000, 'ask_vol': 15000000, 'volume': 34480000, 'turnover': 1301545.0, 'score': 72.764, 'premium': 1.183, 'break_even_point': 293.88, 'leverage': 14.87, 'ipop': 5.25, 'price_recovery_ratio': -4.336078229541951, 'conversion_price': 20.0, 'street_rate': 0.0, 'street_vol': 0, 'amplitude': 0.0, 'issue_size': 100000000, 'high_price': 0.042, 'low_price': 0.029, 'implied_volatility': nan, 'delta': nan, 'effective_leverage': 14.87, 'list_timestamp': 1606665600.0, 'last_trade_timestamp': 1627488000.0, 'maturity_timestamp': 1627574400.0, 'upper_strike_price': nan, 'lower_strike_price': nan, 'inline_price_status': nan}
k线回调  {'code': 'HK.00388', 'time_key': '2020-11-30 14:46:00', 'open': 381.6, 'close': 381.6, 'high': 381.6, 'low': 381.6, 'volume': 500, 'turnover': 190800.0, 'k_type': 'K_1M', 'last_close': 0.0}
BULL 回收价相距 0.0369565217391305 368.0 381.6
k线回调  {'code': 'HK.01299', 'time_key': '2020-11-30 14:46:00', 'open': 86.1, 'close': 86.1, 'high': 86.1, 'low': 86.05, 'volume': 25000, 'turnover': 2152490.0, 'k_type': 'K_1M', 'last_close': 0.0}
BULL 回收价相距 0.0367469879518072 83.0 86.05"""

"""
反注册全部callback
没买进 HK.53058
{'code': 'HK.800700', 'svr_recv_time_bid': '', 'svr_recv_time_ask': '', 'Bid': [(0.0, 0, 0, {})], 'Ask': [(0.0, 0, 0, {})]}
买入失败 HK.800700
/Users/victorhuang/PycharmProjects/futu_robot_pub/smart_buy_and_sell.py:136: RuntimeWarning: divide by zero encountered in double_scalars
  qty = int(math.floor(cash / cur_price))
"""

#打开这些正股的报价监听

#通过回调的，计算与回收价差距，小于x则购买反响操作的论证；保存信息到csv记录；
