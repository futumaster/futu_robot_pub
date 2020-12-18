import time,sys
from futu import *
import csv

class TradeHelper():
    # API parameter setting
    api_svr_ip = '127.0.0.1'  # 账户登录的牛牛客户端PC的IP, 本机默认为127.0.0.1
    api_svr_port = 11111  # 富途牛牛端口，默认为11111
    unlock_password = "198466"  # 美股和港股交易解锁密码
    trade_env = TrdEnv.SIMULATE

    def __init__(self):
        """
        Constructor
        """
        self.quote_ctx, self.trade_ctx = self.context_setting()

    def close(self):
        self.trade_ctx.close()

    def context_setting(self):
        """
        API trading and quote context setting
        :returns: trade context, quote context
        """
        if self.unlock_password == "":
            raise Exception("请先配置交易解锁密码! password: {}".format(
                self.unlock_password))

        if 'HK.' in self.stock:
            trade_ctx = OpenHKTradeContext(host=self.api_svr_ip, port=self.api_svr_port)
        elif 'US.' in self.stock:
            trade_ctx = OpenUSTradeContext(host=self.api_svr_ip, port=self.api_svr_port)
        else:
            raise Exception("不支持的stock: {}".format(self.stock))

        if self.trade_env == ft.TrdEnv.REAL:
            ret_code, ret_data = trade_ctx.unlock_trade(
                self.unlock_password)
            if ret_code == ft.RET_OK:
                print('解锁交易成功!')
            else:
                raise Exception("请求交易解锁失败: {}".format(ret_data))
        else:
            print('解锁交易成功!')

        return quote_ctx, trade_ctx

    def handle_data(self):
        """
        handle stock data for trading signal, and make order
        """
        # 读取历史数据，使用sma方式计算均线准确度和数据长度无关，但是在使用ema方式计算均线时建议将历史数据窗口适当放大，结果会更加准确
        today = datetime.datetime.today()
        pre_day = (today - datetime.timedelta(days=self.observation)
                   ).strftime('%Y-%m-%d')
        end_dt = today.strftime('%Y-%m-%d')
        ret_code, prices, page_req_key = self.quote_ctx.request_history_kline(self.stock, start=pre_day, end=end_dt)
        if ret_code != ft.RET_OK:
            print("request_history_kline fail: {}".format(prices))
            return

        # 用talib计算MACD取值，得到三个时间序列数组，分别为 macd, signal 和 hist
        # macd 是长短均线的差值，signal 是 macd 的均线
        # 使用 macd 策略有几种不同的方法，我们这里采用 macd 线突破 signal 线的判断方法
        macd, signal, hist = talib.MACD(prices['close'].values,
                                        self.short_period, self.long_period,
                                        self.smooth_period)

        # 如果macd从上往下跌破macd_signal
        if macd[-1] < signal[-1] and macd[-2] > signal[-2]:
            # 计算现在portfolio中股票的仓位
            ret_code, data = self.trade_ctx.position_list_query(
                trd_env=self.trade_env)

            if ret_code != ft.RET_OK:
                raise Exception('账户信息获取失败: {}'.format(data))
            pos_info = data.set_index('code')

            cur_pos = int(pos_info['qty'][self.stock])
            # 进行清仓
            if cur_pos > 0:
                ret_code, data = self.quote_ctx.get_market_snapshot(
                    [self.stock])
                if ret_code != 0:
                    raise Exception('市场快照数据获取异常 {}'.format(data))
                cur_price = data['last_price'][0]
                ret_code, ret_data = self.trade_ctx.place_order(
                    price=cur_price,
                    qty=cur_pos,
                    code=self.stock,
                    trd_side=ft.TrdSide.SELL,
                    order_type=ft.OrderType.NORMAL,
                    trd_env=self.trade_env)
                if ret_code == ft.RET_OK:
                    print('stop_loss MAKE SELL ORDER\n\tcode = {} price = {} quantity = {}'
                          .format(self.stock, cur_price, cur_pos))
                else:
                    print('stop_loss: MAKE SELL ORDER FAILURE: {}'.format(ret_data))

        # 如果短均线从下往上突破长均线，为入场信号
        if macd[-1] > signal[-1] and macd[-2] < signal[-2]:
            # 满仓入股
            ret_code, acc_info = self.trade_ctx.accinfo_query(
                trd_env=self.trade_env)
            if ret_code != 0:
                raise Exception('账户信息获取失败! 请重试: {}'.format(acc_info))

            ret_code, snapshot = self.quote_ctx.get_market_snapshot(
                [self.stock])
            if ret_code != 0:
                raise Exception('市场快照数据获取异常 {}'.format(snapshot))
            lot_size = snapshot['lot_size'][0]
            cur_price = snapshot['last_price'][0]
            cash = acc_info['power'][0]  # 购买力
            qty = int(math.floor(cash / cur_price))
            qty = qty // lot_size * lot_size

            ret_code, ret_data = self.trade_ctx.place_order(
                price=cur_price,
                qty=qty,
                code=self.stock,
                trd_side=ft.TrdSide.BUY,
                order_type=ft.OrderType.NORMAL,
                trd_env=self.trade_env)
            if not ret_code:
                print(
                    'stop_loss MAKE BUY ORDER\n\tcode = {} price = {} quantity = {}'
                    .format(self.stock, cur_price, qty))
            else:
                print('stop_loss: MAKE BUY ORDER FAILURE: {}'.format(ret_data))

import requests

def send_weixin(title=None,text=None):
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
    for stock_num in stocks:
        req = WarrantRequest()
        req.sort_field = SortField.RECOVERY_PRICE

        req.type_list = [WrtType.BULL, WrtType.BEAR]
        req.street_min = street_min
        req.price_recovery_ratio_max = 4.9
        req.price_recovery_ratio_min = -4.9
        req.status = "NORMAL"
        ret, ls = quote_ctx.get_warrant(stock_owner=stock_num, req=req)
        if ret == RET_OK:  # 先判断接口返回是否正常，再取数据
            warrant_data_list, last_page, all_count = ls

            if len(warrant_data_list) > 0:
                filter_warrant_list = warrant_data_list[
                    ["name", "stock", "recovery_price", "street_rate", "street_vol", "price_recovery_ratio","type"]].to_dict("records")
                print(filter_warrant_list)
                ##TODO:如果距离一样，或者相差不超过x，则街货的属性相加，选择最贴近的那个
                if warrant_data_list["type"][0] == "BEAR":
                    res[stock_num] = filter_warrant_list[0]
                else:
                    res[stock_num] = filter_warrant_list[-1]
                print("获取贴价窝轮:",res[stock_num])

                req1 = WarrantRequest()
                req1.sort_field = SortField.VOLUME
                if warrant_data_list["type"][0] == "BEAR":
                    req1.type_list = WrtType.BULL
                else:
                    req1.type_list = WrtType.BEAR
                req1.street_max = 1
                time_min = datetime.now() + timedelta(90)
                req1.maturity_timemin = time_min.strftime("%Y-%m-%d")
                req1.status = "NORMAL"
                ret, ls = quote_ctx.get_warrant(stock_owner=stock_num, req=req1)
                warrant_data_list, last_page, all_count = ls
                highscore_warrants = warrant_data_list.loc[
                    warrant_data_list["score"] > 70].to_dict("records")
                print("获取高分的窝轮:", highscore_warrants)
                if len(highscore_warrants) > 0:
                    res[stock_num]["buy"] = highscore_warrants[-1]
                else:
                    res[stock_num]["buy"] = warrant_data_list.to_dict("records")[-1]
    return res

def subscribe_stock(quote_ctx, focus, callback):
    quote_ctx.set_handler(callback)  # 设置实时报价回调
    res = quote_ctx.subscribe(focus, [SubType.K_1M])
    return res

class CurKlineCallback(CurKlineHandlerBase):
    def __init__(self, subscribe_warrants, quote_ctx):
        CurKlineHandlerBase.__init__(self)
        self.quote_ctx = quote_ctx
        self.subscribe_warrants = subscribe_warrants
        self.call_dict = {}
        self.logger = open("res%s.csv"%datetime.now().strftime('%H%M%S'), "w", newline='')
        self.logger_writer = csv.DictWriter(self.logger,
                                            fieldnames=['stock', 'open','close',
                                                        'high','low','volume',
                                                        'turnover','recover_price','recover_price_radio',
                                                        'recover_stock','street_rate','street_vol','type','isbuy','buyprice','buysocket'])
        self.logger_writer.writeheader()

    def on_recv_rsp(self, rsp_str):
        ret_code, data = super(CurKlineCallback,self).on_recv_rsp(rsp_str)
        if ret_code != RET_OK:
            print("CurKlineTest: error, msg: %s" % data)
            return RET_ERROR, data
        #time_key   open  close   high    low  volume    turnover k_type  last_close
        #        0  HK.00700  2020-04-01 15:55:00  375.2  375.4  375.4  375.2   39000  14639140.0   K_1M         0.0
        cur_kline = data.to_dict("records")[0]
        #print("k线回调 ", cur_kline) # CurKlineTest自己的处理逻辑
        cur_code = cur_kline["code"]
        subscribe_warrant = self.subscribe_warrants[cur_code]
        recover_price_radio = 1.0
        if subscribe_warrant["type"] == "BEAR":
            #如果被杀的是熊，则用回收价-最高价值
            recover_price_radio = float(subscribe_warrant["recovery_price"] - cur_kline["high"])/float(subscribe_warrant["recovery_price"])
            #print("BEAR 回收价相距", recover_price_radio, subscribe_warrant["recovery_price"], cur_kline["high"])
        else:
            recover_price_radio = float(cur_kline["low"] - subscribe_warrant["recovery_price"]) / float(
                subscribe_warrant["recovery_price"])
            #print("BULL 回收价相距", recover_price_radio, subscribe_warrant["recovery_price"], cur_kline["low"])
        if recover_price_radio < 0.005:
            ##buy bull
            if subscribe_warrant["buy"]["stock"] in self.call_dict.keys():
                self.call_dict[subscribe_warrant["buy"]["stock"]] = self.call_dict[subscribe_warrant["buy"]["stock"]] + 1
                if self.call_dict[subscribe_warrant["buy"]["stock"]] < 3:
                    print("********* 购买:", recover_price_radio, subscribe_warrant["buy"])
                    send_weixin("购买:" + subscribe_warrant["buy"]["stock"],
                                "距离回收价: %f" % (recover_price_radio * 100))
            else:
                ret, ls = self.quote_ctx.get_market_snapshot([subscribe_warrant["buy"]["stock"], ])
                self.logger_writer.writerow({'stock':cur_code,
                                             'open':cur_kline['open'],
                                             'close':cur_kline['close'],
                                             'high':cur_kline['high'],
                                             'low':cur_kline['low'],
                                             'volume':cur_kline['volume'],
                                             'turnover':cur_kline['turnover'],
                                             'recover_price':subscribe_warrant["recovery_price"],
                                             'recover_price_radio':recover_price_radio,
                                            'recover_stock':subscribe_warrant['stock'],
                                            'street_rate':subscribe_warrant['street_rate'],'street_vol':subscribe_warrant['street_vol'],
                                            'type':subscribe_warrant["type"],'isbuy':'true','buyprice': ls.to_dict("records")[0]['last_price'],'buysocket':subscribe_warrant["buy"]["stock"]})
                send_weixin("购买:"+subscribe_warrant["buy"]["stock"], "距离回收价: %f"%(recover_price_radio*100))
                self.call_dict[subscribe_warrant["buy"]["stock"]] = 1
        else:
            self.call_dict.pop(subscribe_warrant["buy"]["stock"], None)
            if recover_price_radio < 0.01:
                ret, ls = self.quote_ctx.get_market_snapshot([subscribe_warrant["buy"]["stock"], ])
                try:
                    self.logger_writer.writerow({'stock':cur_code,
                                             'open':cur_kline['open'],
                                             'close':cur_kline['close'],
                                             'high':cur_kline['high'],
                                             'low':cur_kline['low'],
                                             'volume':cur_kline['volume'],
                                             'turnover':cur_kline['turnover'],
                                             'recover_price':subscribe_warrant["recovery_price"],
                                             'recover_price_radio':recover_price_radio,
                                            'recover_stock':subscribe_warrant['stock'],
                                            'street_rate':subscribe_warrant['street_rate'],'street_vol':subscribe_warrant['street_vol'],
                                            'type':subscribe_warrant["type"],'isbuy':'false','buyprice': ls.to_dict("records")[0]['last_price'],'buysocket':subscribe_warrant["buy"]["stock"]})
                except:
                    pass
        self.logger.flush()
        return RET_OK, data

quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
focus = get_focus_stock(quote_ctx)
res = get_subscribe_stock(quote_ctx, focus)
re_focus = list(res.keys())
print("完整结果", res)
print("需要关注的正股", re_focus)
send_weixin("begin:"+str(re_focus),"Subscribe")
print("关注结果：",subscribe_stock(quote_ctx, re_focus, CurKlineCallback(res,quote_ctx)))
time.sleep(9999)
send_weixin("done","done")
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

#打开这些正股的报价监听

#通过回调的，计算与回收价差距，小于x则购买反响操作的论证；保存信息到csv记录；