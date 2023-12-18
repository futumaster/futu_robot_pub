import pandas as pd
from datetime import timedelta

# 假设你的CSV文件名为data.csv，并且包含'stock', 'date', 'price'三列。
# 'date'列的格式应该能被pandas的to_datetime函数正确解析。
data = pd.read_csv('cache.csv')
data['date'] = pd.to_datetime(data['date'])
data.sort_values(by=['stock', 'date'], inplace=True)

# 初始化字典用于跟踪每个股票的信息
rising_dict = {}

# 遍历每个股票
for stock in data['stock'].unique():
    stock_data = data[data['stock'] == stock]
    # 初始化时间窗口的起始索引和结束索引
    start_index = 0
    end_index = 0

    # 不断移动时间窗口直到结束索引达到数据的末尾
    while end_index < len(stock_data):
        # 设置时间窗口的长度为1小时
        start_time = stock_data.iloc[start_index]['date']
        end_time = start_time + timedelta(hours=1)

        # 找到在这个时间窗口内的所有数据
        while end_index < len(stock_data) and stock_data.iloc[end_index]['date'] <= end_time:
            end_index += 1

        # 计算在这个时间窗口内的价格上涨次数
        window_data = stock_data.iloc[start_index:end_index]
        rises = sum(window_data['price'].diff().fillna(0) > 0)

        # 确保时间窗口内80%的时间点价格是上涨的
        if rises >= round(0.8 * len(window_data)):
            # 计算整体价格上涨百分比
            price_increase_percent = ((window_data.iloc[-1]['price'] - window_data.iloc[0]['price']) / window_data.iloc[0]['price']) * 100
            # 如果价格上涨超过8%，将这个时间段记录到字典中
            if price_increase_percent >= 8:
                if stock not in rising_dict:
                    rising_dict[stock] = []
                rising_dict[stock].append({
                    'start_time': start_time,
                    'end_time': window_data.iloc[-1]['date'],
                    'price_increase_percent': price_increase_percent
                })

        # 移动时间窗口的起始索引
        start_index += 1

# 打印结果
for stock, periods in rising_dict.items():
    for period in periods:
        print(f"Stock: {stock}, Start: {period['start_time']}, End: {period['end_time']}, Price Increase: {period['price_increase_percent']:.2f}%")