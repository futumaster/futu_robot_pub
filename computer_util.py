def count_recover_price_hardnum(order_books, recover_price):
    founded = False
    total_volumn = 0
    total_order = 0
    re_total_volumn = 0
    re_total_order = 0
    for order_book in order_books:
        order_price = order_book[0]
        volumn = order_book[1]
        order = order_book[2]
        if order_price == recover_price:
            founded = True
        if not founded:
            re_total_volumn = volumn + re_total_volumn
            re_total_order = order + re_total_order
        total_order = order + total_order
        total_volumn = volumn + total_volumn
    return float(re_total_volumn) / float(total_volumn), total_volumn,  re_total_volumn


def test_count_recover_price_hardnum():
    """
    委托价格，委托数量，委托订单数
    买家Bid 从大到小
    卖家Ask 从小到大
    'Bid': [(50.9, 180000, 54, {}), (50.85, 266500, 49, {}), (50.8, 637500, 124, {}), (50.75, 115500, 23, {}), (50.7, 286000, 37, {}), (50.65, 200000, 31, {}), (50.6, 1625500, 106, {}), (50.55, 136000, 46, {}), (50.5, 675500, 329, {}), (50.45, 35500, 14, {})], 'Ask': [(50.95, 275000, 31, {}), (51.0, 932000, 59, {}), (51.05, 222500, 31, {}), (51.1, 90500, 8, {}), (51.15, 95000, 15, {}), (51.2, 171000, 35, {}), (51.25, 118500, 28, {}), (51.3, 202500, 43, {}), (51.35, 97000, 10, {}), (51.4, 72000, 14, {})]}
    """
    Bid = [(50.9, 180000, 54, {}), (50.85, 266500, 49, {}), (50.8, 637500, 124, {}), (50.75, 115500, 23, {}),
           (50.7, 286000, 37, {}), (50.65, 200000, 31, {}), (50.6, 1625500, 106, {}), (50.55, 136000, 46, {}),
           (50.5, 675500, 329, {}), (50.45, 35500, 14, {})]
    Ask = [(50.95, 275000, 31, {}), (51.0, 932000, 59, {}), (51.05, 222500, 31, {}), (51.1, 90500, 8, {}),
           (51.15, 95000, 15, {}), (51.2, 171000, 35, {}), (51.25, 118500, 28, {}), (51.3, 202500, 43, {}),
           (51.35, 97000, 10, {}), (51.4, 72000, 14, {})]
    ###测试熊证回收价 51.15, 熊证是看上升，上升看卖方Ask
    result, total_volumn, re_total_volumn = count_recover_price_hardnum(Ask, 51.15)
    if result == float(275000 + 932000 + 222500 + 90500) / float(total_volumn):
        print("ok",result)
    else:
        print("fail")
    ###测试牛证回收价 50.8, 牛证是看下跌，下跌看买方Bid
    result, total_volumn, re_total_volumn = count_recover_price_hardnum(Bid, 50.8)
    if result == float(180000 + 266500) / float(total_volumn):
        print("ok",result)
    else:
        print("fail")

if __name__ == '__main__':
    test_count_recover_price_hardnum()