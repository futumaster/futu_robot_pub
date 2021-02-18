import sqlite3,datetime

class FutuSqlite:
    """def create_db(self):
        # 连接到SQLite数据库
        # 数据库文件是test.db
        # 如果文件不存在，会自动在当前目录创建:
        conn = sqlite3.connect('test.db')
        # 创建一个Cursor:
        cursor = conn.cursor()
        # 执行一条SQL语句，创建user表:
        #['stock', 'open', 'close',
        # 'high', 'low', 'volume',
        # 'turnover', 'recover_price', 'recover_price_radio',
        # 'recover_stock', 'street_rate', 'street_vol', 'type', 'isbuy', 'buyprice', 'buysocket']
        cursor.execute('create table user (id varchar(20) primary key, name varchar(20))')
        cursor.execute('insert into user (id, name) values (\'1\', \'Michael\')')

        print(cursor.rowcount)
        cursor.close()
        # 提交事务:
        conn.commit()
        # 关闭Connection:
        conn.close()"""
    def __init__(self):
        self.conn = sqlite3.connect('sqlite.db')
        self.cursor = self.conn.cursor()

    def select_ai_data(self):
        self.cursor.execute('select * from ai_history')
        values = self.cursor.fetchall()
        print(values)

    def insert_ai_data(self,stock,open,close,high,low,volumn,turnover,recover_price,recover_price_radio,recover_stock,street_rate,street_vol,type,is_buy,buy_price,buy_stock):
        insert_sql = """
        INSERT INTO ai_history (TIME_DAY,STOCK,OPEN_PRICE,CLOSE_PRICE,HIGH,LOW,VOLUMN,TURNOVER,RECOVER_PRICE,RECOVER_PRICE_RADIO,RECOVER_STOCK,STREET_RATE,STREET_VOL,TYPE,IS_BUY,BUY_PRICE,BUY_STOCK) VALUES (
          '%s',
          '%s',
          '%s',
          '%s',
          '%s',
          '%s',
          '%s',
          '%s',
          '%s',
          '%s',
          '%s',
          '%s',
          '%s',
          '%s',
          '%s',
          '%s',
          '%s'
        ); 
        """%(datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S"),stock,open,close,high,low,volumn,turnover,recover_price,recover_price_radio,recover_stock,street_rate,street_vol,type,is_buy,buy_price,buy_stock)
        self.cursor.execute(insert_sql)
        self.conn.commit()

    def close(self):
        self.cursor.close()
        self.conn.close()


#futu = FutuSqlite()
#futu.select_ai_data()
#futu.insert_ai_data()
#futu.select_ai_data()
#futu.close()

"""
INSERT INTO ai_history (TIME_DAY,STOCK,OPEN_PRICE,CLOSE_PRICE,HIGH,LOW,VOLUMN,TURNOVER,RECOVER_PRICE,RECOVER_PRICE_RADIO,RECOVER_STOCK,STREET_RATE,STREET_VOL,TYPE,IS_BUY,BUY_PRICE,BUY_STOCK) VALUES (
  '%s',
  '%s',
  '5.91',
  '5.33',
  '2.33',
  '0.99',
  '271000',
  '4473570',
  '5.99',
  '0.00510204',
  'HK.51129',
  '10.48',
  '8384000',
  'BULL',
  'FALSE',
  '0.073',
  'HK.64187'
); 
"""



