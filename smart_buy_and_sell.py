# -*- coding: utf-8 -*-
import talib
import math
import datetime
import logging
import futu as ft


class SimpleBuyAndSell(object):
    """
    A simple MACD strategy
    """
    # API parameter setting
    api_svr_ip = '127.0.0.1'  # 账户登录的牛牛客户端PC的IP, 本机默认为127.0.0.1
    api_svr_port = 11111  # 富途牛牛端口，默认为11111
    unlock_password = "440105"  # 美股和港股交易解锁密码
    trade_env = ft.TrdEnv.SIMULATE

    def __init__(self, quote_ctx):
        """
        Constructor
        """
        self.quote_ctx = quote_ctx
        self.context_setting()
        self.buy_records = {}

    def close(self):
        self.quote_ctx.close()
        self.trade_ctx.close()

    def context_setting(self):
        """
        API trading and quote context setting
        :returns: trade context, quote context
        """
        if self.unlock_password == "":
            raise Exception("请先配置交易解锁密码! password: {}".format(
                self.unlock_password))

        self.hk_trade_ctx = ft.OpenHKTradeContext(host=self.api_svr_ip, port=self.api_svr_port)
        self.us_trade_ctx = ft.OpenUSTradeContext(host=self.api_svr_ip, port=self.api_svr_port)

        if self.trade_env == ft.TrdEnv.REAL:
            ret_code, ret_data = self.hk_trade_ctx.unlock_trade(
                self.unlock_password)
            if ret_code == ft.RET_OK:
                print('hk解锁交易成功!')
            else:
                raise Exception("hk请求交易解锁失败: {}".format(ret_data))
        else:
            print('hk解锁交易成功!')

        if self.trade_env == ft.TrdEnv.REAL:
            ret_code, ret_data = self.us_trade_ctx.unlock_trade(
                self.unlock_password)
            if ret_code == ft.RET_OK:
                print('us解锁交易成功!')
            else:
                raise Exception("us请求交易解锁失败: {}".format(ret_data))
        else:
            print('us解锁交易成功!')


    def sell(self, stock):
        trade_ctx = None
        if 'HK.' in stock:
            trade_ctx = self.hk_trade_ctx
        elif 'US.' in stock:
            trade_ctx = self.us_trade_ctx

        # 计算现在portfolio中股票的仓位
        ret_code, data = trade_ctx.position_list_query(
            trd_env=self.trade_env)

        if ret_code != ft.RET_OK:
            raise Exception('账户信息获取失败: {}'.format(data))
        pos_info = data.set_index('code')
        try:
            cur_pos = int(pos_info['qty'][stock])
        except:
            print("没买进",stock)
            return
        cur_price = 0
        ret, data = self.quote_ctx.get_order_book(stock, num=1)
        if ret == ft.RET_OK:
            print(data)
            cur_price = data['Bid'][0][0]

        ret_code, ret_data = trade_ctx.place_order(
            price=cur_price,
            qty=cur_pos,
            code=stock,
            trd_side=ft.TrdSide.SELL,
            order_type=ft.OrderType.NORMAL,
            trd_env=self.trade_env)
        if ret_code == ft.RET_OK:
            print('stop_loss MAKE SELL ORDER\n\tcode = {} price = {} quantity = {}'
                  .format(stock, cur_price, cur_pos))
            self.buy_records.pop(stock)
        else:
            print('stop_loss: MAKE SELL ORDER FAILURE: {}'.format(ret_data))
        self.quote_ctx.unsubscribe([stock], [ft.SubType.ORDER_BOOK])

    def buy(self, stock, lot_size, stock_type, percentage=0.1):
        self.quote_ctx.subscribe([stock], [ft.SubType.ORDER_BOOK], subscribe_push=False)
        trade_ctx = None
        if 'HK.' in stock:
            trade_ctx = self.hk_trade_ctx
        elif 'US.' in stock:
            trade_ctx = self.us_trade_ctx
        # 满仓入股
        ret_code, acc_info = trade_ctx.accinfo_query(
            trd_env=self.trade_env)
        if ret_code != 0:
            raise Exception('账户信息获取失败! 请重试: {}'.format(acc_info))

        if lot_size == 0:
            ret_code, snapshot = self.quote_ctx.get_market_snapshot([stock])
            if ret_code != 0:
                raise Exception('市场快照数据获取异常 {}'.format(snapshot))
            lot_size = snapshot['lot_size'][0]

        cur_price = 0
        ###返回数据：{'code': 'HK.00700', 'svr_recv_time_bid': '', 'svr_recv_time_ask': '', 'Bid': [(384.2, 15400, 6, {}),], 'Ask': [(384.4, 3000, 9, {}),]}
        ret, data = self.quote_ctx.get_order_book(stock, num=1)
        if ret == ft.RET_OK:
            print(data)
            cur_price = data['Ask'][0][0]


        cash = acc_info['power'][0]*percentage  # 购买力
        qty = int(math.floor(cash / cur_price))
        qty = qty // lot_size * lot_size

        ret_code, ret_data = trade_ctx.place_order(
            price=cur_price,
            qty=qty,
            code=stock,
            trd_side=ft.TrdSide.BUY,
            order_type=ft.OrderType.NORMAL,
            trd_env=self.trade_env)
        if not ret_code:
            print(
                'stop_loss MAKE BUY ORDER\n\tcode = {} price = {} quantity = {}'
                .format(stock, cur_price, qty))
        else:
            print('stop_loss: MAKE BUY ORDER FAILURE: {}'.format(ret_data))
            print('qty',qty)
            if stock not in self.buy_records.keys():
                self.buy_records[stock] = {"buy_price":cur_price,"type":stock_type}



if __name__ == "__main__":
    STOCK = "HK.00123"
    quote_ctx = ft.OpenQuoteContext(host='127.0.0.1', port=11111)

    test = SimpleBuyAndSell(quote_ctx)
    test.sell(STOCK)
