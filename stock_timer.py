import datetime,time

def need_stop():
    d_time1 = datetime.datetime.strptime(str(datetime.datetime.now().date()) + '9:30', '%Y-%m-%d%H:%M')
    d_time2 = datetime.datetime.strptime(str(datetime.datetime.now().date()) + '16:00', '%Y-%m-%d%H:%M')
    n_time = datetime.datetime.now()
    print('当前时间：'+str(n_time))
    if n_time > d_time1 and n_time < d_time2:
        return False
    return True

def wait_to_begin():
    while need_stop():
        time.sleep(20)
        print(datetime.datetime.now(),"等待开市")

if __name__ == '__main__':
    print(need_stop())

