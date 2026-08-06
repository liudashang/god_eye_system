from flask import Flask, request, current_app
from flask_sqlalchemy import SQLAlchemy
import datetime as dt
import json
import logging
import sys
from pathlib import Path

# 项目根目录 god_eye_system
root_path = Path(__file__).parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from clickhouse_driver import connect
from god_eye_system.settings import CLICKHOUSE_HOST, CLICKHOUSE_USER, CLICKHOUSE_PASSWORD, CLICKHOUSE_PORT, CLICKHOUSE_DATABASE, SQLALCHEMY_DATABASE_URI

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
db = SQLAlchemy(app)

#app.logger.setLevel(logging.DEBUG)
#handler = logging.StreamHandler(sys.stdout)
#if not app.logger.handlers:
#    app.logger.addHandler(handler)
gunicorn_logger = logging.getLogger('gunicorn.error')
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(gunicorn_logger.level)
app.logger.propagate = True
root_logger = logging.getLogger()
root_logger.addHandler(logging.StreamHandler(sys.stdout))  # 兜底输出
root_logger.setLevel(logging.DEBUG)


class LinkSmokePingEvent(db.Model):
    __tablename__ = "link_smokeping_events"
    id = db.Column(db.Integer, primary_key=True)
    alert_name = db.Column(db.String(32),nullable=False,default="")
    node_path = db.Column(db.String(64),nullable=False,default="")
    alert_info = db.Column(db.String(64),nullable=False,default="")
    host_ip = db.Column(db.String(32),nullable=False,default="")
    alert_time = db.Column(db.DateTime, nullable=False, default=dt.datetime.now)

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<LinkSmokePingEvent({self.alert_name!r}-{self.host_ip!r})>"

class AlertCenterCache(db.Model):
    __tablename__ = 'alert_center_caches'
    id = db.Column(db.Integer, primary_key=True)
    alert_host = db.Column(db.String(256),nullable=False)
    alert_info = db.Column(db.String(1024),nullable=False,default='')
    alert_time = db.Column(db.DateTime,nullable=False)
    alert_level = db.Column(db.String(64),nullable=False,default='')
    eventid = db.Column(db.BigInteger,nullable=False,default=0)
    
    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<AlertCenterCache({self.alert_host!r})>"


@app.route('/',methods=['POST'])
def index():
    data = request.form.to_dict()
    lspe = LinkSmokePingEvent(alert_name=data['alert_name'],node_path=data["node_path"],alert_info=data["alert_info"],host_ip=data["host_ip"])
    db.session.add(lspe)
    db.session.commit()
    return {"info":"接收成功"}

@app.route('/clickhouse_data',methods=['POST'])
def clickhouse_data():
    ping_data_str = request.form.get('ping_data')
    ping_data = json.loads(ping_data_str)
    for data in ping_data:
        data['timestamp'] = dt.datetime.strptime(data['timestamp'],'%Y-%m-%d %H:%M:%S')
    if not isinstance(ping_data,list) or len(ping_data) == 0:
        return {'info':'数据存储失败'}
    app.logger.info(f"{ping_data[0]['host']}发送了数据")
    click_conn = connect(f'clickhouse://{CLICKHOUSE_USER}:{CLICKHOUSE_PASSWORD}@{CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}/{CLICKHOUSE_DATABASE}?dial_timeout=1s&compress=true')
    click_cursor = click_conn.cursor()
    click_cursor.executemany(f'INSERT into {CLICKHOUSE_DATABASE}.fping_metrics (host,loss_now,med_now,node_path,`timestamp`) values',ping_data)
    click_conn.close()
    return {'info':'数据存储成功'}

@app.route('/multi_alerts',methods=['POST'])
def multi_alerts():
    alert_data_str = request.form.get('alert_data')
    alert_data = json.loads(alert_data_str)
    app.logger.info(f"{alert_data[0]['node_path']}发送了告警")
    for data in alert_data:
        lspe = LinkSmokePingEvent(alert_name=data['alert_name'],node_path=data["node_path"],alert_info=data["alert_info"],host_ip=data["host_ip"])
        db.session.add(lspe)
    db.session.commit()
    return {"info":"接收成功"}

@app.route('/node_alerts',methods=['POST'])
def node_alerts():
    '''form格式的数据'''
    data = request.form.to_dict()
    alert_center_cache = AlertCenterCache(alert_host=data['alert_host'],alert_info=data['alert_info'],alert_time=data['alert_time'],alert_level=data['alert_level'],eventid=data['eventid'])
    db.session.add(alert_center_cache)
    db.session.commit()
    return {"info":"接收成功"}

@app.route('/node_alerts_for_json',methods=['POST'])
def node_alerts_for_json():
    '''json格式的数据'''
    data = request.json
    alert_center_cache = AlertCenterCache(alert_host=data['alert_host'],alert_info=data['alert_info'],alert_time=data['alert_time'],alert_level=data['alert_level'],eventid=data['eventid'])
    db.session.add(alert_center_cache)
    db.session.commit()
    return {"info":"接收成功"}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
