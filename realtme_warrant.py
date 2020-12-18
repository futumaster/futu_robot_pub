
import time,sys
from futu import *

premonday = (datetime.today()- timedelta(days=time.localtime().tm_wday+7)).strftime("%Y-%m-%d")

prefriday = (datetime.today()- timedelta(days=time.localtime().tm_wday+3)).strftime("%Y-%m-%d")
print(premonday,prefriday)

quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
ret, data, page = quote_ctx.request_history_kline('HK.00700', start=premonday, end=prefriday, ktype=KLType.K_WEEK)
if ret == RET_OK:
    print(data.to_dict("records"))
quote_ctx.close()   # 关闭当条连接，FutuOpenD会在1分钟后自动取消相应股票相应类型的订阅