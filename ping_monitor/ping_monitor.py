from clickhouse_driver import connect
import datetime
import pymysql
import re
import time
import sys
from pathlib import Path

# 项目根目录 god_eye_system
root_path = Path(__file__).parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))
from god_eye_system.settings import DATABASE_NAME, DATABASE_USER, DATABASE_PASSWORD, DATABASE_HOST, CLICKHOUSE_HOST, CLICKHOUSE_USER, CLICKHOUSE_PASSWORD, CLICKHOUSE_PORT, CLICKHOUSE_DATABASE

db = pymysql.connect(host=DATABASE_HOST,
                     user=DATABASE_USER,
                     password=DATABASE_PASSWORD,
                     database=DATABASE_NAME)
 
# 使用 cursor() 方法创建一个游标对象 cursor
cursor = db.cursor()

regx = re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+\-\s+\-\s+\[(\S+)\s+\S+\]\s+\"POST /smokeping/sm\.cgi HTTP/1\.1\" 200 3 \"-\" \"smokeping\-slave/1\.0\"')


def get_clickhouse_status():
    click_conn = connect(f'clickhouse://{CLICKHOUSE_USER}:{CLICKHOUSE_PASSWORD}@{CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}/{CLICKHOUSE_DATABASE}?dial_timeout=1s&compress=true')
    click_cursor = click_conn.cursor()
    click_cursor.execute('select host,max(`timestamp`) as last_time from mes_log.mes_ping mp group by host having last_time >=\'{}\'  '.format((datetime.datetime.now()-datetime.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")))
    datas = click_cursor.fetchall()
    active_goerteck_ping_clients = [d[0] for d in datas]
    return active_goerteck_ping_clients

def check_pingclients(warn_clients):
    cursor.execute('select hostname from gtk_ping_clients where enabled=1')
    datas = cursor.fetchall()
    normal_clients = get_clickhouse_status()
    for d in datas:
        if d[0] not in normal_clients:
            warn_clients.append(d[0])
    return warn_clients

def analisys_httpd_log():
    normal_smokepings = {}
    with open('/var/log/httpd/access_log','r') as f:
        for line in f:
            matchObj = regx.match(line)
            if matchObj:
                ip = matchObj.group(1)
                log_time_str = matchObj.group(2)
                log_time = datetime.datetime.strptime(log_time_str,'%d/%b/%Y:%H:%M:%S')
                if ip not in normal_smokepings:
                    normal_smokepings[ip] = log_time_str
                else:
                    if datetime.datetime.strptime(normal_smokepings[ip],'%d/%b/%Y:%H:%M:%S') < log_time:
                        normal_smokepings[ip] = log_time_str
    last_permit_time = datetime.datetime.now()-datetime.timedelta(hours=1)
    for k in list(normal_smokepings.keys()):
        if datetime.datetime.strptime(normal_smokepings[k],'%d/%b/%Y:%H:%M:%S') < last_permit_time:
            del normal_smokepings[k]
    return normal_smokepings

def check_smokepings(warn_clients):
    cursor.execute('select ip,name from smokeping_clients')
    datas = cursor.fetchall()
    normal_clients = analisys_httpd_log()
    for d in datas:
        if d[0] not in normal_clients:
            warn_clients.append(d[1])
    return warn_clients

def task():
    cursor.execute('update topologys set ping_status=1')
    db.commit()
    warninfo = {}
    warn_clients = []
    warn_clients = check_pingclients(warn_clients)
    warn_clients = check_smokepings(warn_clients)
    for w in warn_clients:
        cursor.execute('select distinct topology_name from links where smokeping_path like \'%{}\''.format(w))
        datas = cursor.fetchall()
        warninfo[w] = [d[0] for d in datas]
        for d in datas:
            cursor.execute('update topologys set ping_status=0 where name="{}"'.format(d[0]))
            db.commit()
    print(warninfo)

if __name__ == '__main__':
    while True:
        print("开始检查ping状态")
        task()
        time.sleep(600)