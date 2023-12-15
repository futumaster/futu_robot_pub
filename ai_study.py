import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import pymysql
import os
import datetime
import joblib

# 数据库配置
DB_HOST = 'hk-cynosdbmysql-grp-ryjhhk5b.sql.tencentcdb.com'
DB_USER = 'root'
DB_PASSWORD = 'Zz102938'
DB_NAME = 'futu_data'

# CSV文件路径
CSV_PATH = 'cache.csv'

# 更新CSV文件的标志
UPDATE_CSV = False


# 连接数据库并更新CSV文件
def update_csv_from_db():
    # 连接数据库
    connection = pymysql.connect(host=DB_HOST, user=DB_USER,port=28497, password=DB_PASSWORD, db=DB_NAME)

    try:
        # 从数据库中查询数据
        with connection.cursor() as cursor:
            sql = "SELECT * FROM ai_coinmarketcap"
            cursor.execute(sql)
            result = cursor.fetchall()
            columns = [column[0] for column in cursor.description]
            df = pd.DataFrame(result,columns=columns)

            # 将查询结果写入CSV文件
            df.to_csv(CSV_PATH, index=False)
    finally:
        connection.close()


# 检查是否需要更新CSV
if UPDATE_CSV or not os.path.exists(CSV_PATH):
    update_csv_from_db()

# 读取CSV文件
df = pd.read_csv(CSV_PATH)

# 数据预处理
# 保留连续数据
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values(by=['stock', 'date'])
df['time_diff'] = df.groupby('stock')['date'].diff().dt.total_seconds().div(60).fillna(0)
df_continuous = df[df['time_diff'] <= 20]

# 增加新特征
df_continuous['twopercent_diff'] = df_continuous['twopercentdeplus'] - df_continuous['twopercentplus']

# 生成时序特征
for lag in range(1, 200):
    df_continuous[f'price_lag_{lag}'] = df_continuous.groupby('stock')['price'].shift(lag)
    df_continuous[f'twopercent_diff_lag_{lag}'] = df_continuous.groupby('stock')['twopercent_diff'].shift(lag)
    df_continuous[f'volumnpercent_lag_{lag}'] = df_continuous.groupby('stock')['volumnpercent'].shift(lag)
    # 你可以添加更多的时序特征...

# 去除含有NaN的行
df_continuous.dropna(inplace=True)

# 定义目标变量，这里简化为未来1小时价格上涨（1）或下跌（0）
df_continuous['target'] = np.where(df_continuous['price'].shift(-3) > df_continuous['price'], 1, 0)

# 拆分数据为训练集和测试集
X = df_continuous.drop(['date', 'stock', 'target'], axis=1)
y = df_continuous['target']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 模型训练与参数优化
clf = RandomForestClassifier()
param_grid = {
    'n_estimators': [100,],
    'max_depth': [50,]
}

grid_search = GridSearchCV(clf, param_grid, cv=2)
grid_search.fit(X_train, y_train)

# 保存训练好的模型
best_model = grid_search.best_estimator_
model_filename = f'model_{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}.joblib'
joblib.dump(best_model, model_filename)

# 使用测试集评估模型
predictions = best_model.predict(X_test)
print(f'Accuracy: {accuracy_score(y_test, predictions)}')

# 请确保安装了以下包：pandas, numpy, scikit-learn, pymysql, joblib