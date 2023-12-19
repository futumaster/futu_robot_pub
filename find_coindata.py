import pandas as pd

# 假设你的CSV文件名为data.csv，并且包含'stock', 'date', 'price', 'twopercentdeplus', 'twopercentplus'等列。
data = pd.read_csv('cache.csv', parse_dates=['date'])

# 确保数据按照股票和日期排序
data.sort_values(by=['stock', 'date'], inplace=True)

# 避免在循环中操作 DataFrame
data.set_index('date', inplace=True)

# 计算'twopercentdeplus'和'twopercentplus'的差值并直接添加为新列
data['difference'] = data['twopercentdeplus'] - data['twopercentplus']

# 初始化用于存储结果的列表
rising_data = []

# 使用groupby优化，一次性计算每只股票
for stock, stock_data in data.groupby('stock'):

    # 计算价格上涨百分比，这里使用了shift来对齐数据
    stock_data['price_increase_percent'] = stock_data['price'].pct_change(periods=-1) * -100

    # 筛选出价格上涨超过8%的数据
    high_increase = stock_data[stock_data['price_increase_percent'] >= 8]

    # 通过rolling和sum计算正差值的比率
    windowed_data = stock_data.rolling('2h').agg({
        'difference': lambda x: (x > 0).sum() / len(x) if len(x) > 0 else 0
    }).rename(columns={'difference': 'positive_difference_ratio'})

    # 合并高增长数据和窗口统计数据
    merged_data = high_increase.join(windowed_data, how='left')

    # 记录每只股票的相关数据
    for date, row in merged_data.iterrows():
        rising_data.append({
            'stock': stock,
            'start_time': date,
            'end_time': date + pd.Timedelta(hours=1),
            'price_increase_percent': row['price_increase_percent'],
            'positive_difference_ratio': row['positive_difference_ratio']
        })

# 将结果转换为DataFrame
rising_df = pd.DataFrame(rising_data)

# 打印结果
print(rising_df)