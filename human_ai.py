import pandas as pd

# 读取数据
df = pd.read_csv('preprocessed_data.csv')

# 确保数据按日期排序
df.sort_values(by='date', inplace=True)

# 计算差值
df['diff'] = df['twopercentdeplus'] - df['twopercentplus']

# 找出连续30次以上diff > 0后跟着的diff < 0
# 这里我们创建一个新列来记录连续次数
df['consecutive_count'] = (df['diff'] > 0).astype(int).groupby(df['diff'] <= 0).cumsum()

# 只有在连续30次以上之后的第一次diff < 0，我们将consecutive_count重置为-30
df.loc[df['consecutive_count'] > 30, 'consecutive_count'] = -30

# 找出符合条件的时间点
change_points = df.loc[df['consecutive_count'] == -30, 'date']

# 初始化上涨次数
up_count = 0
# 总次数
total_count = 0

# 检查后续3小时内价格的变化
for change_point in change_points:
    end_time = pd.to_datetime(change_point) + pd.Timedelta(hours=3)
    # 确保date列是datetime类型
    df['date'] = pd.to_datetime(df['date'])
    # 获取变化点价格
    start_price = df.loc[df['date'] == change_point, 'price'].values[0]
    # 获取3小时后的数据点
    end_price = df.loc[df['date'] <= end_time, 'price'].iloc[-1]
    # 判断是否上涨
    if end_price > start_price:
        up_count += 1
    total_count += 1

# 计算概率
probability = up_count / total_count if total_count > 0 else 0
print(f'价格在特定条件下后续3小时内上涨的概率是: {probability:.2f}')