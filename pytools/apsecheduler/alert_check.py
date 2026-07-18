#!/usr/bin/python3
from sqlalchemy import create_engine, Table, text
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session


from concurrent.futures import ThreadPoolExecutor

import json
import time
import datetime
import queue

import traceback

import sys
sys.path.append('../')
from utils import send_alert
sys.path.append('../../')
from god_eye_system.settings import SQLALCHEMY_DATABASE_URI


ALERT_LEVEL = {'Not classified': 0, 'Information': 1,
               'Warning': 2, 'Error': 3, 'High': 4, 'Disaster': 5}
ALERT_LEVEL_CN_DICT = {'Not classified': '未分类', 'Information': '信息',
                       'Warning': '警告', 'Error': '错误', 'High': '严重', 'Disaster': '灾难'}

engine = create_engine(SQLALCHEMY_DATABASE_URI)
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

Base = declarative_base()

workQueue = queue.Queue()
nodeEventQueue = queue.Queue()


class AlertCache(Base):
    __table__ = Table(
        'alert_caches',
        Base.metadata,
        autoload_with=engine
    )


class Node(Base):
    __table__ = Table(
        'nodes',
        Base.metadata,
        autoload_with=engine
    )


class Link(Base):
    __table__ = Table(
        'links',
        Base.metadata,
        autoload_with=engine
    )


class LinkSmokePingEvent(Base):
    __table__ = Table(
        'link_smokeping_events',
        Base.metadata,
        autoload_with=engine
    )


class VirtualCluster(Base):
    __table__ = Table(
        'virtual_clusters',
        Base.metadata,
        autoload_with=engine
    )


class AlertCenterCache(Base):
    __table__ = Table(
        'alert_center_caches',
        Base.metadata,
        autoload_with=engine
    )


def check_alert_center_cache():
    session = Session()
    pass
    session.commit()
    Session.remove()


def alert_task_v2():

    session = Session()
    data = {}

    alerts_dbobjs = session.execute(text(
        'select alert_info,alert_time,alert_level,alert_host from alert_center_caches')).fetchall()
    current_alerts = [{
        'alert_host': a.alert_host,
        'alert_info': a.alert_info,
        'alert_level': a.alert_level,
        'alert_time': a.alert_time
    } for a in alerts_dbobjs]

    node_dbs = session.execute(text('''
                                  select nfac.topology_name,nfac.node_id,nfac.alertcenter_name,n.node_type from node_for_alert_centers nfac join
                                    nodes n on nfac.node_id=n.id'''
                                    )).fetchall()
    node_dict = {}
    for n in node_dbs:
        if n.alertcenter_name not in node_dict:
            node_dict[n.alertcenter_name] = []
        node_dict[n.alertcenter_name].append(
            {'topology_name': n.topology_name, 'node_id': n.node_id, 'node_type': n.node_type})

    # print(node_dict)
    node_events = {}

    for ca in current_alerts:
        if ca['alert_host'] not in node_dict:
            continue
        for nd in node_dict[ca['alert_host']]:
            node_id = nd['node_id']
            topology_name = nd['topology_name']
            if ('Oracle' in ca['alert_host'] or 'Mongo' in ca['alert_host']) and 'DBServer' not in nd['node_type']:
                continue
            if 'DBServer' in nd['node_type'] and not ('Oracle' in ca['alert_host'] or 'Mongo' in ca['alert_host']):
                continue
            if topology_name not in data:
                data[topology_name] = {}
            if node_id not in data[topology_name]:
                data[topology_name][node_id] = {}

            if 'alert_count' not in data[topology_name][node_id]:
                data[topology_name][node_id]['alert'] = []
                data[topology_name][node_id]['alert_count'] = 0
            if "Farm" in nd["node_type"]:
                data[topology_name][node_id]['alert'].append(
                    "{}--[{}]{}".format(ca["alert_host"], ALERT_LEVEL_CN_DICT[ca["alert_level"]], ca["alert_info"]))
            else:
                data[topology_name][node_id]['alert'].append(
                    f'[{ALERT_LEVEL_CN_DICT[ca["alert_level"]]}]{ca["alert_info"]}')
            data[topology_name][node_id]['color'] = 'red'
            data[topology_name][node_id]['alert_count'] += 1

        if ALERT_LEVEL[ca['alert_level']] not in node_events:
            node_events[ALERT_LEVEL[ca['alert_level']]] = {}
        if ca['alert_host'] not in node_events[ALERT_LEVEL[ca['alert_level']]]:
            node_events[ALERT_LEVEL[ca['alert_level']]][ca['alert_host']] = []
        if ca['alert_info'] not in node_events[ALERT_LEVEL[ca['alert_level']]][ca['alert_host']]:
            node_events[ALERT_LEVEL[ca['alert_level']]
                        ][ca['alert_host']].append(ca['alert_info'])

    nodeEventQueue.put(node_events)

    # 链路关联smokeping告警的检查
    link_data = {}

    lses = session.execute(text('''
        select l.id, lse.alert_name, lse.alert_info, lse.alert_time,
            l.topology_name, l.need_alert, l.alert_inerval, 
            l.last_alert_time, lse.host_ip, l.topology_id, l.alert_custom_name
        from links l 
        inner join (
            select *,
                row_number() over (partition by node_path order by alert_time desc) as rn
            from link_smokeping_events
            where alert_time > date_sub(now(), interval 2 minute)
        ) lse on l.smokeping_path = lse.node_path and lse.rn = 1
        order by lse.alert_time desc
    ''')).fetchall()

    alert_notify_dict = {}

    for l in lses:
        topology_name = l["topology_name"]
        if topology_name not in link_data:
            link_data[topology_name] = {}
        if l["id"] not in link_data[topology_name]:
            link_data[topology_name][l["id"]] = {}
        if l["alert_name"] == "someloss" or l["alert_name"] == "linkslow":
            link_data[topology_name][l["id"]]["color"] = '#FF8C00'
        elif l["alert_name"] == "linkdown":
            link_data[topology_name][l["id"]]["color"] = 'red'

        if l['need_alert'] == 1 and (l['last_alert_time'] is None or l['alert_time'] > (l['last_alert_time'] + datetime.timedelta(minutes=l['alert_inerval']))):
            if topology_name not in alert_notify_dict:
                alert_notify_dict[topology_name] = {
                    'id': l['topology_id'], 'error_host': []}
            alert_info_host = l['host_ip']
            if l['alert_custom_name'] is not None and l['alert_custom_name'] != "":
                alert_info_host = l['alert_custom_name']
            alert_notify_dict[topology_name]['error_host'].append(
                {'host': alert_info_host, 'info': l['alert_info'], 'link_id': l['id']})

        link_data[topology_name][l["id"]]["alert"] = l["alert_info"]

    topologys = session.execute(text(
        "select name,ping_status from topologys where is_tingxian=0 and is_eol=0")).fetchall()
    session.execute(text("update topologys set alert_status=''"))
    session.commit()
    for t in topologys:
        topology_name = t[0]
        result1 = {}
        result2 = {}
        if topology_name in data:
            result1 = data[topology_name]
        if topology_name in link_data:
            result2 = link_data[topology_name]
        if result1 == {} and result2 == {}:
            continue
        if t[1] == 0:
            alert_status = "{}台设备告警".format(len(result1))
        else:
            alert_status = "{}台设备告警，{}条线路告警".format(len(result1), len(result2))
        session.execute(text("update topologys set alert_status='{}' where name='{}'".format(
            alert_status, topology_name)))
        result_string = json.dumps(
            {"node_alerts": result1, "link_alerts": result2}, ensure_ascii=False)
        ac = AlertCache(topology_name=topology_name, alert_string=result_string, expire_time=(
            datetime.datetime.now()+datetime.timedelta(seconds=120)))
        session.add(ac)

        if topology_name in alert_notify_dict:
            workQueue.put({'topology_id': alert_notify_dict[topology_name]['id'],
                          'info': alert_notify_dict[topology_name]['error_host'], 'name': topology_name})
        session.commit()

    Session.remove()


def main_loop():
    while True:
        try:
            check_alert_center_cache()
            alert_task_v2()
        except Exception as e:
            print(e)
            print(sys.exc_info())
            print(traceback.print_exc())
            Session.rollback()

        time.sleep(30)


def post_alert():
    while True:
        try:
            session = Session()
            if not workQueue.empty():
                data = workQueue.get()
                try:
                    send_alert(data['topology_id'], data['info'], data['name'])
                    for i in data['info']:
                        session.execute(text("update links set last_alert_time='{}' where id={}".format(
                            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), i['link_id'])))
                    session.commit()
                except Exception as e:
                    print(e)
                    print(sys.exc_info())
                    print(traceback.print_exc())

                    break
            Session.remove()
        except Exception as e:
            print(e)
            print(sys.exc_info())
            print(traceback.print_exc())

        time.sleep(30)


def insert_node_events():
    while True:
        try:
            session = Session()
            if not nodeEventQueue.empty():
                data = nodeEventQueue.get()
                session.execute(text('truncate table node_events'))
                for priority, alert_dict in data.items():
                    for host, infos in alert_dict.items():
                        for info in infos:
                            session.execute(text(f'''insert into node_events (name,host,eventid,triggerid,description,priority)
                                                values ('{host}','','','','{info}','{priority}')
                                            '''))
            session.commit()
            Session.remove()
        except Exception as e:
            print(e)
            print(sys.exc_info())
            print(traceback.print_exc())


if __name__ == '__main__':
    tongbu_flag = False
    pool = ThreadPoolExecutor(max_workers=3)
    futures = []
    futures.append(pool.submit(insert_node_events,))
    futures.append(pool.submit(main_loop,))
    futures.append(pool.submit(post_alert,))
    for future in futures:
        future.done()
    print("多线程开启")
