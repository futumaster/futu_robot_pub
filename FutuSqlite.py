import sqlite3,datetime
import psycopg2, sqlite3, sys

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

    def convert_to_pg(self):
        sqlike = 'ai_history'
        pgdb = 'futu_db'
        pguser = 'dbuser'
        pgpswd = 'Zz102938'
        pghost = 'localhost'
        pgport = '5432'
        pgschema = 'public'

        consq = self.conn
        cursq = self.cursor

        tabnames = []

        cursq.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%s'" % sqlike)
        tabgrab = cursq.fetchall()
        for item in tabgrab:
            tabnames.append(item[0])

        for table in tabnames:
            cursq.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name = ?;", (table,))
            create = cursq.fetchone()[0]
            create = create.replace("DATETIME", "TIMESTAMPTZ").replace("DOUBLE","FLOAT")
            cursq.execute("SELECT * FROM %s where TIME_DAY > '%s';" % (table, '2021-02-23'))
            rows = cursq.fetchall()
            colcount = len(rows[0])
            pholder = '%s,' * colcount
            newholder = pholder[:-1]

            try:

                conpg = psycopg2.connect(database=pgdb, user=pguser, password=pgpswd,
                                         host=pghost, port=pgport)
                curpg = conpg.cursor()
                curpg.execute("SET search_path TO %s;" % pgschema)
                #curpg.execute("DROP TABLE IF EXISTS %s;" % table)
                #curpg.execute(create)
                ##处理数据
                newrows = []
                for row in rows:
                    newrow = []
                    for item in row:
                        if type(item) is str and "-" in item:
                            time_item = datetime.datetime.strptime(item, '%Y-%m-%d %H-%M-%S')
                            item = time_item.strftime('%Y-%m-%d %H:%M:%S') + " +8:00"
                        newrow.append(item)
                    newrows.append(tuple(newrow))
                    #print(row)
                    #newrows.append((row[0],row[1].replace("-",""),row[2],row[3])
                curpg.executemany("INSERT INTO %s VALUES (%s);" % (table, newholder), newrows)
                conpg.commit()
                print('Created', table)

            except psycopg2.DatabaseError as e:
                print('Error %s' % e)
                sys.exit(1)

            finally:
                if conpg:
                    conpg.close()

        consq.close()

    def insert_ai_data(self,stock,open,close,high,low,volumn,turnover,recover_price,recover_price_radio,recover_stock,street_rate,street_vol,type,is_buy,buy_price,buy_stock, order_vol_percent, order_vol):
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
          '%s',
        ); 
        """%(datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S"),stock,open,close,high,low,volumn,turnover,recover_price,recover_price_radio,recover_stock,street_rate,street_vol,type,is_buy,buy_price,buy_stock,order_vol_percent,order_vol)
        self.cursor.execute(insert_sql)
        self.conn.commit()

    def close(self):
        self.cursor.close()
        self.conn.close()

if __name__ == '__main__':
    """测试代码"""
    #futu = FutuSqlite()
    #futu.select_ai_data()
    #futu.insert_ai_data()
    #futu.select_ai_data()
    #futu.close()
    futu = FutuSqlite()
    futu.convert_to_pg()