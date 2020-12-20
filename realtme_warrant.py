
import time,sys
from futu import *
import pickle

def get_change_rate_preweek(stocknum, quote_ctx):
    cache_dict = {}
    if os.path.exists('cache.pkl'):
        with open('cache.pkl','rb') as f:
            cache_dict = pickle.load(f)
            if not cache_dict:
                cache_dict = {}
    premonday = (datetime.today()- timedelta(days=time.localtime().tm_wday+7)).strftime("%Y-%m-%d")
    prefriday = (datetime.today()- timedelta(days=time.localtime().tm_wday+3)).strftime("%Y-%m-%d")
    print(premonday,prefriday)
    if "%s-%s-%s"%(premonday,prefriday,stocknum) in cache_dict.keys():
        return cache_dict["%s-%s-%s"%(premonday,prefriday,stocknum)]
    ##cache_dict["%s-%s-%s"%(premonday,prefriday,stocknum] =
    ret, data, page = quote_ctx.request_history_kline(stocknum, start=premonday, end=prefriday, ktype=KLType.K_WEEK)
    if ret == RET_OK:
        records = data.to_dict("records")
        cache_dict["%s-%s-%s" % (premonday, prefriday, stocknum)] = records[0]['change_rate']
        with open('cache.pkl','wb') as f:
            pickle.dump(cache_dict, f, pickle.HIGHEST_PROTOCOL)
        return records[0]['change_rate']
    else:
        return 0

quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
change_rate = get_change_rate_preweek('HK.03033', quote_ctx)
##获取当前价格
current_price = 0
##下注比例 10%
buy_percent = 10
##本金池
full = 1000
##下注金额
buy_price = (change_rate/100) * current_price/ (buy_percent/100)
##下注股数
buy_vol = full/buy_price



quote_ctx.close()   # 关闭当条连接，FutuOpenD会在1分钟后自动取消相应股票相应类型的订阅
