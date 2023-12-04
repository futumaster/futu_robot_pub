import datetime
import pymysql, pymysql.cursors, sys
import traceback

class FutuMysql:
    def __init__(self):
        try:
            self.conn = pymysql.connect(host='10.0.4.4',
                                 user='root',
                                 password='Zz102938',
                                 database='futu_data',
                                 cursorclass=pymysql.cursors.DictCursor)
            self.cursor = self.conn.cursor()
        except:
            self.conn = None
            self.cursor = None


    def select_ai_data(self):
        self.cursor.execute('select * from ai_history limit 10')
        values = self.cursor.fetchall()
        print(values)

    def insert_coinmarketcap_data(self,stock,price,twopercentplus,twopercentdeplus,volumn,volumnpercent):
        """
        交易对
        价格
        +2% Depth
        -2% Depth
        交易量
        交易量(%)"""
        if not self.conn and not self.cursor:
            return

        insert_sql = """
        INSERT INTO ai_coinmarketcap (stock,price,twopercentplus,twopercentdeplus,volumn,volumnpercent) VALUES (
          '%s',
          '%s',
          '%s',
          '%s',
          '%s',
          %s
        ); 
        """%(stock,price,twopercentplus,twopercentdeplus,volumn,volumnpercent)
        #print("insert_sql",insert_sql)
        try:
            self.cursor.execute(insert_sql)
            self.conn.commit()
        except Exception as e:
            print(datetime.datetime.now().strftime("%H:%M:%S"),"handel ai_coinmarket sql error")
            traceback.print_exc()

    def insert_ai_data(self,stock,open,close,high,low,volumn,turnover,recover_price,recover_price_radio,recover_stock,street_rate,street_vol,type,is_buy,buy_price,buy_stock, order_vol_percent, order_vol):
        if not self.conn and not self.cursor:
            return
        insert_sql = """
        INSERT INTO ai_history (TIME_DAY,STOCK,OPEN_PRICE,CLOSE_PRICE,HIGH,LOW,VOLUMN,TURNOVER,RECOVER_PRICE,RECOVER_PRICE_RADIO,RECOVER_STOCK,STREET_RATE,STREET_VOL,TYPE,IS_BUY,BUY_PRICE,BUY_STOCK,ORDER_VOL_PERCENT,ORDER_VOL) VALUES (
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
          '%s',
          '%s',
          '%s'
        ); 
        """%(datetime.datetime.now(),stock,open,close,high,low,volumn,turnover,recover_price,recover_price_radio,recover_stock,street_rate,street_vol,type,is_buy,buy_price,buy_stock,order_vol_percent,order_vol)
        #print("insert_sql",insert_sql)
        try:
            self.cursor.execute(insert_sql)
            self.conn.commit()
        except Exception as e:
            print(datetime.datetime.now().strftime("%H:%M:%S"),"handel ai sql error")
            traceback.print_exc()


    def close(self):
        self.cursor.close()
        self.conn.close()

if __name__ == '__main__':
    """测试代码"""
    futu = FutuMysql()

    #futu.select_ai_data()
    #futu.insert_ai_data()
    futu.close()
