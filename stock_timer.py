import datetime

d_time1 = datetime.datetime.strptime(str(datetime.datetime.now().date())+'9:30', '%Y-%m-%d%H:%M')
d_time2 = datetime.datetime.strptime(str(datetime.datetime.now().date())+'16:00', '%Y-%m-%d%H:%M')

def need_stop():
    n_time = datetime.datetime.now()
    ##print('当前时间：'+str(n_time))
    if n_time > d_time1 and n_time < d_time2:
        return False
    return True


if __name__ == '__main__':
    print(need_stop())

