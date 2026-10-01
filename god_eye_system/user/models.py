# -*- coding: utf-8 -*-
"""User models."""
import datetime as dt

from flask_login import UserMixin
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import text
from sqlalchemy.dialects.mysql import LONGTEXT

from god_eye_system.database import Column, PkModel, db, reference_col, relationship
from god_eye_system.extensions import bcrypt

from urllib.parse import quote


class Role(PkModel):
    """A role for a user."""

    __tablename__ = "roles"
    name = Column(db.String(80), unique=True, nullable=False)
    value = Column(db.String(256),nullable=True)
    user_id = reference_col("users", nullable=True)
    user = relationship("User", backref="roles")

    def __init__(self, name, **kwargs):
        """Create instance."""
        super().__init__(name=name, **kwargs)

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<Role({self.name})>"


class User(UserMixin, PkModel):
    """A user of the app."""

    __tablename__ = "users"
    username = Column(db.String(80), unique=True, nullable=False)
    email = Column(db.String(80), unique=True, nullable=False)
    _password = Column("password", db.LargeBinary(128), nullable=True)
    created_at = Column(
        db.DateTime, nullable=False, default=dt.datetime.now(dt.timezone.utc)
    )
    first_name = Column(db.String(30), nullable=True)
    last_name = Column(db.String(30), nullable=True)
    active = Column(db.Boolean(), default=False)
    is_admin = Column(db.Boolean(), default=False)
    gonggao = Column(db.String(30), nullable=True)

    @hybrid_property
    def password(self):
        """Hashed password."""
        return self._password

    @password.setter
    def password(self, value):
        """Set password."""
        self._password = bcrypt.generate_password_hash(value)

    def check_password(self, value):
        """Check password."""
        return bcrypt.check_password_hash(self._password, value)

    @property
    def full_name(self):
        """Full user name."""
        return f"{self.first_name} {self.last_name}"
    
    def get_role_value(self,role_name):
        for r in self.roles:
            if role_name == r.name:
                return r.value
        return ''
    
    def have_role(self,role_name):
        for r in self.roles:
            if role_name == r.name:
                return True
        return False
    
    def get_topology_list(self,obj_list=False):
        tps = []
        if self.is_admin:
            tps = Topology.query.order_by(Topology.name).all()
        elif self.get_role_value('g_or_u') == 'bg':
            tps = []
            bg_list = self.get_role_value('bg_fanwei').split(',')
            for bg in bg_list:
                p_tps = Topology.query.filter_by(bg=bg).all()
                tps.extend(p_tps)
        elif self.get_role_value('g_or_u') == 'bu':
            tps = []
            bg = self.get_role_value('bg_fanwei')
            bu_list = self.get_role_value('bu_fanwei').split(',')
            for bu in bu_list:
                p_tps = Topology.query.filter(text('bg="{}" and bu="{}"'.format(bg,bu))).all()
                tps.extend(p_tps)
        elif self.get_role_value('g_or_u') == 'one_top':
            tps = []
            topology_name = self.get_role_value('has_one_topology').split(',')
            for t in topology_name:
                p_tps = Topology.query.filter(text('name="{}"'.format(t))).all()
                tps.extend(p_tps)
        if obj_list:
            return tps
        topology_list = [t.name for t in tps]
        return topology_list

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<User({self.username!r})>"

class Configuration(PkModel):
    ''' 系统参数配置表 '''

    __tablename__ = "configurations"
    config_name = Column(db.String(64),unique=True, nullable=False)
    config_value = Column(db.String(128))

    def __init__(self, config_name, **kwargs):
        """Create instance."""
        super().__init__(config_name=config_name, **kwargs)

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<Configuration({self.config_name!r})>"
    
class Node(PkModel):
    ''' D3拓扑结构的节点表 '''

    __tablename__ = "nodes"
    name = Column(db.String(64),nullable=False,default="")
    ip = Column(db.String(128),nullable=False,default="")
    topology_name = Column(db.String(64),nullable=False,default="",index=True)
    fx = Column(db.Float,nullable=False,default=200.0)
    fy = Column(db.Float,nullable=False,default=200.0)
    node_type = Column(db.String(64),nullable=False,default="")
    color = Column(db.String(64),nullable=False,default="transparent")
    alert = Column(db.String(2048),nullable=False,default="正常")
    group_name = Column(db.String(64),nullable=True)
    group_color = Column(db.String(64),nullable=True)
    current_alert_id = Column(db.String(64),nullable=True)

    def __init__(self,topology_name , name, **kwargs):
        """Create instance."""
        super().__init__(topology_name=topology_name, name=name, **kwargs)

    def node_type_cn_name(self):
        cn_name = db.session.execute(text("select cn_name from node_types where name='{}'".format(self.node_type))).fetchone()
        if cn_name is None:
            return "未设置"
        return cn_name[0]

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<Node({self.name!r}) in {self.topology_name!r}>"

class Link(PkModel):
    '''D3拓扑结构的连接线表'''

    __tablename__ = "links"
    source = Column(db.Integer,nullable=False)
    target = Column(db.Integer,nullable=False)
    color = Column(db.String(32),nullable=False,default="green")
    topology_name = Column(db.String(64),nullable=False,default="")
    smokeping_path = Column(db.String(128),nullable=True,index=True)
    source_port = Column(db.String(64),nullable=True)
    target_port = Column(db.String(64),nullable=True)
    need_alert = Column(db.Integer,nullable=False,default=0)
    alert_inerval = Column(db.Integer,nullable=False,default=60)
    last_alert_time = Column(db.DateTime, nullable=True)
    topology_id = Column(db.Integer,nullable=True)
    avg_rtt = Column(db.String(16),nullable=True)
    alert_custom_name = Column(db.String(64),nullable=True)
    path_type = Column(db.Integer,nullable=False,default=0) # 0-按照系统默认执行 1-直线类型 2-折线类型

    def __init__(self, topology_name , source, target, **kwargs):
        """Create instance."""
        super().__init__(topology_name=topology_name, source=source, target=target, **kwargs)

    def get_source_name(self):
        data = db.session.execute(text('select name from nodes where id={}'.format(self.source))).fetchone()
        if data is None:
            return ''
        return data.name

    def get_target_name(self):
        data = db.session.execute(text('select name from nodes where id={}'.format(self.target))).fetchone()
        if data is None:
            return ''
        return data.name

    def get_link_name(self):
        return "Link{}:{}->{}".format(self.id,self.get_source_name(),self.get_target_name())

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<Link({self.source!r}->{self.target!r}) in {self.topology_name!r}>"

class NodeMetric(PkModel):
    '''D3拓扑结构的grafana指标表'''

    __tablename__ = "node_metrics"
    node_id = Column(db.Integer,nullable=False)
    name = Column(db.String(32),nullable=False,default="")
    grafana_src = Column(db.String(1024),nullable=False,default="")
    metric_type = Column(db.Integer,nullable=True,default=0) #0-节点，1-线路
    
    def __init__(self, node_id, name, **kwargs):
        """Create instance."""
        super().__init__(node_id=node_id, name=name, **kwargs)

    def get_node_name(self):
        name = ""
        if self.metric_type == 0:
            data = db.session.execute(text('select name from nodes where id={}'.format(self.node_id))).fetchone()
            name = data["name"]
        else:
            link = Link.query.filter_by(id=self.node_id).first()
            name = link.get_link_name()
        return name

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<NodeMetric({self.name!r})>"

class ZabbixTemplate(PkModel):
    __tablename__ = "zabbix_template"
    node_type = Column(db.String(64),nullable=False,default="")
    item = Column(db.String(256),nullable=False,default="")
    zabbix_type = Column(db.Integer,nullable=False,default=0) # 0-数值图表 1-文本表格
    grafana_src = Column(db.String(1024),nullable=False,default="")

    def get_item(self):
        return quote(self.item)
    
    def node_type_cn_name(self):
        cn_name = db.session.execute(text("select cn_name from node_types where name='{}'".format(self.node_type))).fetchone()
        return cn_name[0]

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<ZabbixTemplate({self.node_type!r}-{self.item!r})>"

class NodeEvent(PkModel):
    __tablename__ = "node_events"
    name = Column(db.String(128),nullable=False,default="",index=True)
    host = Column(db.String(64),nullable=False,default="")
    eventid = Column(db.String(64),nullable=False,default="")
    value = Column(db.Integer,nullable=True)
    triggerid = Column(db.String(64),nullable=False,default="")
    description = Column(db.String(256),nullable=False,default="")
    priority = Column(db.Integer,nullable=True)

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<NodeEvent({self.eventid!r})>"

class LinkSmokePingEvent(PkModel):
    __tablename__ = "link_smokeping_events"
    alert_name = Column(db.String(32),nullable=False,default="")
    node_path = Column(db.String(64),nullable=False,default="", index=True)
    alert_info = Column(db.String(64),nullable=False,default="")
    host_ip = Column(db.String(128),nullable=False,default="")
    alert_time = Column(db.DateTime, nullable=False, default=dt.datetime.now, index=True)

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<LinkSmokePingEvent({self.alert_name!r}-{self.host_ip!r})>"

class NodeNetworkEvent(PkModel):
    __tablename__ = "node_network_events"
    alert_name = Column(db.String(32),nullable=False,default="")
    host_ip = Column(db.String(128),nullable=False,default="",index=True)
    alert_info = Column(db.String(256),nullable=False,default="")
    alert_time = Column(db.DateTime, nullable=False, default=dt.datetime.now,index=True)

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<NodeNetworkEvent({self.alert_name!r}-{self.host_ip!r})>"

class NodeType(PkModel):
    __tablename__ = "node_types"
    name = Column(db.String(64),nullable=False,default="")
    img_url = Column(db.String(128),nullable=False,default="")
    cn_name = Column(db.String(32),nullable=False,default="")
    keyword = Column(db.String(64),nullable=False,default="")
    cmdb_class = Column(db.String(64),nullable=False,default="")

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<NodeType({self.name!r})>"

class AlertCache(PkModel):
    __tablename__ = "alert_caches"
    topology_name = Column(db.String(64),nullable=False,default="")
    alert_string = Column(db.Text,nullable=False,default="")
    expire_time = Column(db.DateTime, nullable=False, default=dt.datetime.now)

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<AlertCache({self.topology_name!r}-{self.expire_time!r})>"

class SmokepingTarget(PkModel):
    __tablename__ = "smokeping_targets"
    topology_name = Column(db.String(64),nullable=False,default="")
    host = Column(db.String(64),nullable=False,default="")
    target_id = Column(db.Integer,nullable=True)
    link_id = Column(db.Integer,nullable=True)
    slave = Column(db.String(64),nullable=False,default="")
    is_add_path = Column(db.Boolean(),nullable=False,default=False)
    smokeping_path = Column(db.String(64),nullable=False,default="")
    multi_slave = Column(db.Integer,nullable=False,default=0) #1时存在多个相同host的监控
    is_gtk_client = Column(db.Integer,nullable=False,default=0) #0时smokeping,1时为自研客户端
    avg_rtt = Column(db.String(16),nullable=True)

    def get_link_name(self):
        link = Link.query.filter_by(id=self.link_id).first()
        if self.link_id is None or link is None:
            return "无"
        return link.get_link_name()
    
    def get_avg_rtt(self,client_avg_rtt):
        if self.avg_rtt is not None and self.avg_rtt != '' and 'ms' in self.avg_rtt:
            return self.avg_rtt
        else:
            return client_avg_rtt

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<SmokepingTarget({self.host!r})>"

class VirtualCluster(PkModel):
    __tablename__ = "virtual_clusters"
    name = Column(db.String(128),nullable=False,default="")
    ip = Column(db.String(128),nullable=False,default="")
    zabbix_name = Column(db.String(128),nullable=False,default="")

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<VirtualCluster({self.zabbix_name!r})>"

class BU(PkModel):
    __tablename__ = "bus"
    name = Column(db.String(64),nullable=False,default="")
    bu_type = Column(db.Integer,nullable=False,default=1) #1-BG,2-BU
    bu_parent = Column(db.String(64),nullable=False,default="")
    status = Column(db.Integer,nullable=False,default=1) #1-正常，0-撤销

    def __repr__(self):
        """Represent instance as a unique string."""
        if self.bu_type == 1:
            return f"<BG({self.name!r})>"
        else:
            return f"<BU({self.bu_parent!r}-{self.name!r})>"

class Topology(PkModel):
    __tablename__ = "topologys"
    name = Column(db.String(64),nullable=False,default="",index=True)
    bg = Column(db.String(64),nullable=False,default="")
    bu = Column(db.String(64),nullable=False,default="")
    is_tingxian = Column(db.Boolean(), default=False,index=True)
    is_eol = Column(db.Boolean(), default=False,index=True)
    alert_status = Column(db.String(256),nullable=False,default="")
    playlist_url = Column(db.String(512),nullable=False,default="")
    ping_status = Column(db.Integer,nullable=False,default=1)
    alert_level = Column(db.String(32), nullable=False, default="")
    igoer_group_id = Column(db.String(128),nullable=False,default="")
    location = Column(db.String(64),nullable=False,default="wf") #wf-潍坊 vn-越南
    db.Index('topologys_name_IDX',name, is_tingxian, is_eol)

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<Topology({self.name!r})>"

class GtkPingClient(PkModel):
    __tablename__ = "gtk_ping_clients"
    hostname = Column(db.String(256),nullable=False,default="")
    description = Column(db.String(256),nullable=False,default="")
    ip = Column(db.String(128),nullable=False,default="")
    enabled = Column(db.Integer,nullable=False,default=0) #1为启用，0为停用
    time_out = Column(db.String(16),nullable=False,default="1m")
    time_interval = Column(db.String(16),nullable=False,default="3s")
    ping_count = Column(db.Integer,nullable=False,default=20)
    avg_rtt = Column(db.String(16),nullable=False,default="10ms")
    packet_loss = Column(db.Float,nullable=False,default=0)

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<GtkPingClient({self.hostname!r})>"

class AlertRecord(PkModel):
    __tablename__ = "alert_records"
    alert = Column(db.Text,nullable=False,default="")
    last_time = Column(db.DateTime, nullable=False, default=dt.datetime.now)
    topology_name = Column(db.String(64),nullable=False,default="")

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<AlertRecord({self.alert!r})>"

class SmokePingClient(PkModel):
    __tablename__ = "smokeping_clients"
    name = Column(db.String(64),nullable=False,default="")
    description = Column(db.String(256),nullable=False,default="")
    ip = Column(db.String(128),nullable=False,default="")

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<SmokePingClient({self.name!r})>"

class AlertSuggestion(PkModel):
    __tablename__ = 'alert_suggestions'
    node_type = Column(db.String(64),nullable=False,default="")
    name = Column(db.String(64),nullable=False,default="")
    regexp_string = Column(db.String(256),nullable=False,default="")
    reason = Column(db.String(256),nullable=False,default="")
    suggestion = Column(db.String(256),nullable=False,default="")

    def node_type_cn_name(self):
        cn_name = db.session.execute(text("select cn_name from node_types where name='{}'".format(self.node_type))).fetchone()
        return cn_name[0]

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<AlertSuggestion({self.name!r})>"

class ApToAruba(PkModel):
    __tablename__ = 'ap_to_arubas'
    node_id = Column(db.Integer,nullable=False)
    aruba_id = Column(db.Integer,nullable=False)

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<ApToAruba({self.node_id!r})>"

class IframeEmbedUrl(PkModel):
    __tablename__ = 'iframe_embed_urls'
    name = Column(db.String(64),nullable=False,default="")
    url = Column(db.String(1024),nullable=False,default="")
    width = Column(db.Float,nullable=False,default=200.0)
    height = Column(db.Float,nullable=False,default=100.0)
    top = Column(db.Float,nullable=False,default=0)
    left = Column(db.Float,nullable=False,default=0)
    topology_name = Column(db.String(64),nullable=False,default="")

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<IframeEmbedUrl({self.name!r})>"

class FavoriteTopology(PkModel):
    __tablename__ = 'favorite_topologys'
    topology_id = Column(db.Integer,nullable=False)
    username = Column(db.String(80), nullable=False)
    create_time = Column(db.DateTime, nullable=False, default=dt.datetime.now)
    group_name = Column(db.String(64),nullable=False, default='默认分组')

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<FavoriteTopology({self.topology_id!r})>"
    
class NodeForAlertCenter(PkModel):
    __tablename__ = 'node_for_alert_centers'
    topology_id = Column(db.Integer,nullable=False)
    topology_name = Column(db.String(64),nullable=False,default="")
    node_id = Column(db.Integer,nullable=False)
    alertcenter_name=Column(db.String(256),nullable=False,default="")

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<NodeForAlertCenter({self.topology_id!r})>"
    
class SystemRegister(PkModel):
    __tablename__ = 'system_registers'
    name = Column(db.String(255),nullable=False)
    sys_key = Column(db.String(255),nullable=False)
    sys_secret = Column(db.String(255),nullable=False)
    description = Column(db.String(512),nullable=False,default="")

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<SystemRegister({self.username!r})>"

class LLMAnswer(PkModel):
    __tablename__ = 'llm_answers'
    question_uuid = Column(db.String(64),nullable=False)
    topology_name = Column(db.String(64),nullable=False)
    answer_time = Column(db.DateTime, nullable=False, default=dt.datetime.now)
    metrics_content = Column(LONGTEXT,nullable=False,default='')
    llm_answer_content = Column(LONGTEXT,nullable=False,default='')
    history_report_time = Column(db.DateTime, nullable=False, default=dt.datetime.now)
    ask_user = Column(db.String(64),nullable=False,default='')
    
    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<LLMAnswer({self.question_uuid!r})>"

class LLMPrompt(PkModel):
    __tablename__ = 'llm_prompts'
    answer_name = Column(db.String(64), nullable=False)
    answer_content = Column(db.Text,nullable=False,default='')
    
    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<LLMPrompt({self.answer_name!r})>"

class AlertCenterNotify(PkModel):
    __tablename__ = 'alert_center_notifies'
    zabbix_host_name = Column(db.String(256),nullable=False)
    zabbix_host_id = Column(db.BigInteger,nullable=False)
    alert_info = Column(db.String(1024),nullable=False,default='')
    alert_time = Column(db.DateTime, nullable=False)
    alert_level = Column(db.String(64),nullable=False,default='')
    llm_answer_status = Column(db.Integer,nullable=False,default=0) #0 未回答 1 已回答
    ip = Column(db.String(64),nullable=False,default='')
    alert_uuid = Column(db.String(64),nullable=False,default='')
    
    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<AlertCenterNotify({self.zabbix_host_name!r})>"

class AlertCenterCache(PkModel):
    __tablename__ = 'alert_center_caches'
    alert_host = Column(db.String(256),nullable=False)
    alert_info = Column(db.String(1024),nullable=False,default='')
    alert_time = Column(db.DateTime,nullable=False)
    alert_level = Column(db.String(64),nullable=False,default='')
    eventid = Column(db.BigInteger,nullable=False,default=0)
    
    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<AlertCenterCache({self.alert_host!r})>"