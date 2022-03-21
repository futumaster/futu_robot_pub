### (收盘价-（最高价+最低价）/2）的平方 * 成交量 = 新成交量
###（某日/3日的新成交量求和）=重新计算成交量比重
### 然后计算三日收盘价*成加量比重，然后三日求和=筹码平均价）   每日的股价成成加量比重
from futu import *

def cyq(quote_ctx, stock, start='2019-09-11', end='2019-09-18'):
    ret, data, page_req_key = quote_ctx.request_history_kline(stock, start=start, end=end,max_count=1000)  # 每页5个，请求第一页
    if ret == RET_OK:
        print(data)
        print(data['code'][0])  # 取第一条的股票代码
        print(data['close'].values.tolist())  # 第一页收盘价转为list
    else:
        print('error:', data)
    while page_req_key != None:  # 请求后面的所有结果
        print('*************************************')
        ret, data, page_req_key = quote_ctx.request_history_kline('HK.00700', start='2019-09-11', end='2019-09-18',
                                                                  max_count=5, page_req_key=page_req_key)  # 请求翻页后的数据
        if ret == RET_OK:
            print(data)
        else:
            print('error:', data)
    print('All pages are finished!')
    quote_ctx.close()  # 结束后记得关闭当条连接，防止连接条数用尽
