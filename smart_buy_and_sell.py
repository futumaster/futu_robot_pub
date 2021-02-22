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

    def __init__(self, stock, quote_ctx):
        """
        Constructor
        """
        self.stock = stock
        self.quote_ctx = quote_ctx
        self.trade_ctx = self.context_setting()

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

        if 'HK.' in self.stock:
            trade_ctx = ft.OpenHKTradeContext(host=self.api_svr_ip, port=self.api_svr_port)
        elif 'US.' in self.stock:
            trade_ctx = ft.OpenUSTradeContext(host=self.api_svr_ip, port=self.api_svr_port)
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

        return trade_ctx

    def buy(self):
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


if __name__ == "__main__":
    STOCK = "HK.00123"

    test = SimpleBuyAndSell(STOCK)
    test.handle_data()
    test.close()