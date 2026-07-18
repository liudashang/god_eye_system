from flask import Blueprint, jsonify, render_template, request, Response, current_app, redirect, make_response
from flask_login import login_required, current_user

from god_eye_system.extensions import csrf_protect
from god_eye_system.user.models import Topology, NodeType, db, FavoriteTopology, AlertSuggestion, Node, Link, IframeEmbedUrl, SmokepingTarget, NodeForAlertCenter, ZabbixTemplate, NodeMetric, GtkPingClient, AlertCache
from god_eye_system.utils import check_admin, check_topology_get, check_topology_post
from god_eye_system.topology.utils import chech_topology_eol, delete_topology, copy_smokeping_path, jwt_generate
from god_eye_system.settings import GRAFANA_PING_DELAY_URL, GRAFANA_DROP_RATE_URL
from pytools.utils import alert_get_zabbix_hostname

from sqlalchemy import text, desc
import datetime
import json
import re

blueprint = Blueprint("topology", __name__,
                      url_prefix="/topology", static_folder="../static")


def recent_topology_check(username, topology_id):
    tops = FavoriteTopology.query.filter(
        text(f'''username='{username}' and group_name="最近访问"''')).all()
    check_flag = False
    old_top = None
    for t in tops:
        if old_top is None:
            old_top = t
        else:
            if old_top.create_time > t.create_time:
                old_top = t
        if t.topology_id == topology_id:
            t.update(create_time=datetime.datetime.now())
            check_flag = True

    if not check_flag:
        if len(tops) >= 5:
            old_top.update(topology_id=topology_id,
                           create_time=datetime.datetime.now(), username=username)
        else:
            FavoriteTopology.create(topology_id=topology_id, create_time=datetime.datetime.now(
            ), group_name='最近访问', username=username)


@blueprint.route('/topology_show')
@login_required
def topology_show():
    topology_name = request.args.get("topology_name", default="")
    open_link_mode = request.args.get("open_link_mode", default="关闭")
    need_ip = request.args.get("need_ip", default="yes")
    topology_list = current_user.get_topology_list()
    if topology_name == "":
        topology_name = topology_list[0]

    topology = Topology.query.filter_by(name=topology_name).first()
    recent_topology_check(current_user.username, topology.id)

    # svg面积自适应
    svg_size = db.session.execute(text(
        "select max(fx),max(fy) from nodes where topology_name='{}'".format(topology_name))).fetchone()
    width = 1600
    height = 900
    if svg_size[0] is None:
        width = 400
        height = 300
    else:
        if svg_size[0] > width-400:
            width = svg_size[0] + 400
        if svg_size[0] > height-300:
            height = svg_size[1] + 300

    node_edit_flag = "0"
    if current_user.is_admin or current_user.get_role_value('has_edit_node_info') == "1" or current_user.get_role_value('has_config') == "1":
        node_edit_flag = "1"

    node_types = NodeType.query.all()

    return render_template('topology/topology_show.html',
                           topology_name=topology_name,
                           topology_list=topology_list,
                           need_ip=need_ip,
                           width=width,
                           height=height,
                           playlist_url=topology.playlist_url,
                           ping_status=topology.ping_status,
                           node_edit_flag=node_edit_flag,
                           node_types=node_types,
                           open_link_mode=open_link_mode)


@blueprint.route("/admin_zabbix_template_config_page")
@login_required
@check_admin
def zabbix_template_config_page():
    topology_name = request.args.get("topology_name", default="")
    node_types = NodeType.query.all()
    return render_template("topology/zabbix_template_config_page.html", topology_name=topology_name, node_types=node_types)

@blueprint.route("/edit_zabbixtemplate_info")
@login_required
def edit_zabbixtemplate_info():
    id = request.args.get("id")
    zt = ZabbixTemplate.query.filter_by(id=id).first()
    zt.delete()
    return {'error':0,'info':'删除成功'}

@blueprint.route("/zabbixtemplate_list", methods=['GET', 'POST'])
@login_required
def zabbixtemplate_list():
    if request.method == 'POST':
        node_type = request.form.get('node_type')
        item = request.form.get('item')
        zabbix_type = request.form.get('zabbix_type', default=0, type=int)
        grafana_src = request.form.get('grafana_src', default="")
        zt = ZabbixTemplate.query.filter(
            text('node_type="{}" and item="{}"'.format(node_type, item))).first()
        if zt is not None:
            return {'error': 1, 'info': '节点不能重复添加！'}
        ZabbixTemplate.create(node_type=node_type,
                              item=item, zabbix_type=zabbix_type, grafana_src=grafana_src)
        return {'error': 0, 'info': '创建成功'}
    zts = ZabbixTemplate.query.order_by(ZabbixTemplate.node_type).all()
    data = [{"id": z.id, "node_type": z.node_type, "item": z.item,
             "node_type_cn_name": z.node_type_cn_name(), "grafana_src": z.grafana_src} for z in zts]
    return jsonify(data)

@blueprint.route('/alert_suggestion_manage_page')
@login_required
@check_topology_get
def alert_suggestion_manage_page():
    operate = request.args.get('operate', type=int, default=0)
    if operate == 1:
        suggestions = AlertSuggestion.query.all()
        data = [{'id': s.id, 'name': s.name, 'node_type': s.node_type, "regexp_string": s.regexp_string,
                 'reason': s.reason, 'suggestion': s.suggestion, 'node_type_cn_name': s.node_type_cn_name()} for s in suggestions]
        return jsonify(data)
    node_types = NodeType.query.all()
    return render_template('topology/alert_suggestion_manage.html', node_types=node_types)

@blueprint.route('/alert_suggestion_del')
@login_required
def alert_suggestion_del():
    data = request.args.getlist('ids[]')
    db.session.execute(text('delete from alert_suggestions where id in ({})'.format(','.join(data))))
    db.session.commit()
    return {'error':0,'info':'删除完毕'}

@blueprint.route('/alert_suggestion_add',methods=['POST'])
@login_required
def alert_suggestion_add():
    data = request.form.to_dict()
    del data['csrf_token']
    AlertSuggestion.create(**data)
    return {'error':0,'info':'创建完毕'}

@blueprint.route('/alert_suggestion_edit',methods=['POST'])
@login_required
def alert_suggestion_edit():
    data = request.form.to_dict()
    del data['csrf_token']
    suggestion = AlertSuggestion.query.filter_by(id=data['id']).first()
    del data['id']
    suggestion.update(**data)
    return {'error':0,'info':'修改完毕'}

@blueprint.route("/node_metric_config_page")
@login_required
@check_topology_get
def node_metric_config_page():
    topology_name = request.args.get("topology_name", default="")
    return render_template("topology/node_metric_config_page.html", topology_name=topology_name)

@blueprint.route("/nodemetric_list",methods=['GET','POST'])
@login_required
@check_topology_get
def nodemetric_list():
    if request.method == 'POST':
        node_id = request.form.get('node_id',type=int)
        name = request.form.get('name')
        grafana_src = request.form.get('grafana_src')
        metric_type = request.form.get('metric_type',type=int,default=0)
        nm = NodeMetric.query.filter(text('node_id={} and name="{}" and metric_type="{}"'.format(node_id,name,metric_type))).first()
        if nm is not None:
            return {'error':1,'info':'节点不能重复添加！'}
        NodeMetric.create(node_id=node_id,name=name,grafana_src=grafana_src,metric_type=metric_type)
        return {'error':0,'info':'创建成功'}
    search = request.args.get('search',default="")
    if search != "":
        nodes = Node.query.filter(text("topology_name = '{}'".format(search))).all()
        query_node = "node_id in () and metric_type=0"
        if len(nodes) > 0:
            nodes_list = ["'{}'".format(n.id) for n in nodes]
            nodes_string = ','.join(nodes_list)
            query_node = "node_id in ({}) and metric_type=0".format(nodes_string)
        links = Link.query.filter(text("topology_name = '{}'".format(search))).all()
        query_link = "metric_type=1"
        if len(links) > 0:
            links_list = ["'{}'".format(l.id) for l in links]
            links_string = ','.join(links_list)
            query_link = "node_id in ({}) and metric_type=1".format(links_string)
        query = "({}) or ({})".format(query_node,query_link)
        
        nodemetrics = NodeMetric.query.filter(text(query)).order_by(NodeMetric.node_id).all()
    else:
        nodemetrics = NodeMetric.query.order_by(NodeMetric.node_id).all()
    data = [{"id":n.id,"node_id":n.node_id,"node_name":n.get_node_name(),"name":n.name,"grafana_src":n.grafana_src,"metric_type":n.metric_type} for n in nodemetrics]
    return jsonify(data)

@blueprint.route("/edit_nodemetric_info",methods=['GET','POST'])
@login_required
def edit_nodemetric_info():
    if request.method == "GET":
        id = request.args.get("id")
        operation = request.args.get('operation',type=int,default=1)
        node = NodeMetric.query.filter_by(id=id).first()
        if operation == 0:
            node.delete()
            return {'error':0,'info':'删除成功'}
    else:
        data = request.form.to_dict()
        id = data['id']
        data.pop('csrf_token')
        data.pop('id')
        nodemetric = NodeMetric.query.filter_by(id=id).first()
        nodemetric.update(**data)
        return {'error':0,'info':"更新成功"}

@blueprint.route("/ping_config_nav")
@login_required
@check_topology_get
def ping_config_nav():
    topology_name = request.args.get("topology_name", default="")
    return render_template("topology/ping_config_nav.html", topology_name=topology_name)

@blueprint.route("/topology_config_nav")
@login_required
@check_topology_get
def topology_config_nav():
    topology_name = request.args.get("topology_name", default="")
    node_types = NodeType.query.all()
    return render_template("topology/topology_config_nav.html", topology_name=topology_name, node_types=node_types)

@blueprint.route("/node_manage_page/")
@login_required
@check_topology_get
def node_manage_page():
    topology_name = request.args.get("topology_name")
    node_types = NodeType.query.all()
    return render_template("topology/node_manage_page.html",topology_name=topology_name,node_types=node_types)

@blueprint.route("/change_topology_by_change_bu")
@login_required
def change_topology_by_change_bu():
    topology_name = request.args.get("topology_name")
    bg = request.args.get("bg")
    bu = request.args.get("bu")
    tp = Topology.query.filter_by(name=topology_name).first()
    tp.update(bg=bg, bu=bu)
    return {"error": 0, "info": "更新成功"}


@blueprint.route("/json")
@login_required
def node_json():
    topology_name = request.args.get('topology_name', default="")
    topology_node_obj = Node.query.filter_by(
        topology_name=topology_name).order_by(Node.id).all()
    topology_node = [{"id": tno.id, "name": tno.name, "node_type": tno.node_type, "ip": tno.ip, "fx": tno.fx,
                      "fy": tno.fy, "color": tno.color, "alert": ["正常"], "alert_count": 0} for tno in topology_node_obj]

    topology_link_obj = Link.query.filter_by(
        topology_name=topology_name).order_by(Link.id).all()
    topology_link = [{"id": tlo.id, "source": tlo.source, "target": tlo.target, "color": tlo.color, "alert": "正常",
                      "source_port": tlo.source_port, "target_port": tlo.target_port, "path_type": tlo.path_type} for tlo in topology_link_obj]

    topology_group = []
    group_list = db.session.execute(text(
        "select distinct group_name from nodes where topology_name='{}'".format(topology_name))).fetchall()
    for gl in group_list:
        group_name = gl.group_name
        if group_name == "":
            continue
        group = {"nodes": [], "name": group_name, "color": ""}
        sql_stmt = "topology_name='{}' and group_name='{}'".format(
            topology_name, group_name)
        nodes = Node.query.filter(text(sql_stmt)).order_by(Node.id).all()
        for n in nodes:
            group["color"] = n.group_color
            group["nodes"].append(n.id)
        if len(group["nodes"]) == 0:
            continue
        topology_group.append(group)

    return {"nodes": topology_node, "links": topology_link, "groups": topology_group}


@blueprint.route("/alert_report_page")
@login_required
def alert_report_page():
    topology_name = request.args.get('topology_name')
    return render_template("topology/alert_report.html", topology_name=topology_name)

@blueprint.route("/topology_general_info",methods=["GET","POST"])
@login_required
def topology_general_info():
    if request.method == "GET":
        name = request.args.get("name")
        topology = Topology.query.filter_by(name=name).first()
        if topology is not None:
            if topology.is_tingxian:
                is_tingxian = "true"
            else:
                is_tingxian = "false"
            if topology.is_eol:
                is_eol = "true"
            else:
                is_eol = "false"
            return {"id":topology.id,"name":topology.name,"bg":topology.bg,"bu":topology.bu,"location":topology.location,"is_tingxian":is_tingxian,"is_eol":is_eol,"igoer_group_id":topology.igoer_group_id,"playlist_url":topology.playlist_url}
        else:
            return {"id":None,"name":None,"bg":None,"bu":None,"location":'wf',"is_tingxian":"false","is_eol":"false","igoer_group_id":None,"playlist_url":None}
    else:
        data = request.form.to_dict()
        data.pop('csrf_token')
        if data["name"] == "" or data["bg"] == "" or data["bu"] == "":
            return {"error":1,"info":"拓扑图信息不能为空！"}

        if data["is_tingxian"] == "false":
            data["is_tingxian"] = False
        else:
            data["is_tingxian"] = True
        if data["is_eol"] == "false":
            data["is_eol"] = False
        else:
            data["is_eol"] = True
        topology = Topology.query.filter_by(name=data['name']).first()
        
        if topology is None:
            Topology.create(**data)
        else:
            if not topology.is_eol and data["is_eol"]:
                chech_topology_eol(topology.name)
            topology.update(**data)
        return {"error":0,"info":"保存成功"}

@blueprint.route("/admin_node_type_list_page")
@login_required
@check_admin
def node_type_list_page():
    topology_name = request.args.get('topology_name',default='')
    return render_template("topology/node_type_config.html",topology_name=topology_name)

@blueprint.route('/iframe_embed_url_manage',methods=["GET","POST"])
@login_required
def iframe_embed_url_manage():
    if request.method == "GET":
        operate = request.args.get('operate',type=int,default=0)
        topology_name = request.args.get('topology_name',default="")
        from_where = request.args.get('from_where',default="")
        if operate == 1:
            urls = IframeEmbedUrl.query.filter_by(topology_name=topology_name).all()
            data = [{"id":u.id,"name":u.name,"url":u.url} for u in urls]
            return jsonify(data)
        elif operate == 2:
            id_list = request.args.getlist('ids[]')
            db.session.execute(text("delete from iframe_embed_urls where id in ({})".format(",".join(id_list))))
            db.session.commit()
            return {"error":0,"info":"删除完毕"}
        return render_template("topology/iframe_embed_url_manage.html",topology_name=topology_name,from_where=from_where)
    else:
        data = request.form.to_dict()
        del data['csrf_token']
        if data['name'] == "" or data['url'] == "" or data['topology_name']=="":
            return {"error":1,"info":"参数值不能为空"}
        IframeEmbedUrl.create(**data)
        return {"error":0,"info":"添加成功"}

@blueprint.route('/get_update_iframe_embed_url', methods=['GET', 'POST'])
@login_required
def get_update_iframe_embed_url():
    if request.method == "GET":
        grafana_token = jwt_generate()
        topology_name = request.args.get('topology_name')
        urlobjs = IframeEmbedUrl.query.filter_by(
            topology_name=topology_name).all()
        if urlobjs is not None or len(urlobjs) > 0:
            urls = [{"id": u.id, "name": u.name, "url": u.url, "width": u.width,
                     "height": u.height, "top": u.top, "left": u.left, 
                     "grafana_token":grafana_token} for u in urlobjs]
        else:
            urls = []
        return jsonify(urls)
    else:
        data_string = request.form.get("style")
        data = json.loads(data_string)
        for d in data:
            id = d['id']
            url = IframeEmbedUrl.query.filter_by(id=id).first()
            url.update(width=d['width'], height=d['height'],
                       top=d['top'], left=d['left'])
        return {"error": 0, "info": "更新成功"}


@blueprint.route("/edit_link_other_info", methods=['POST'])
@login_required
def edit_link_other_info():
    data = request.form.to_dict()
    data.pop("csrf_token")
    link = Link.query.filter_by(id=data['id']).first()
    data.pop("id")
    link.update(**data)
    return {"error": 0, "info": "设置成功"}


@blueprint.route("/edit_node_info", methods=['GET', 'POST'])
@login_required
def edit_node_info():
    if request.method == "GET":
        id = request.args.get("id")
        operation = request.args.get('operation', type=int, default=1)
        node = Node.query.filter_by(id=id).first()
        if operation == 0:
            targets = SmokepingTarget.query.filter_by(target_id=node.id).all()
            for t in targets:
                t.delete()
            links = Link.query.filter(
                text("source={} or target={}".format(node.id, node.id))).all()
            for l in links:
                l.delete()
            node_2_alert = NodeForAlertCenter.query.filter(
                text("node_id={}".format(node.id))).all()
            for n2a in node_2_alert:
                n2a.delete()
            node.delete()
            return {'error': 0, 'info': '删除成功'}
        return {"id": node.id, "topology_name": node.topology_name, "name": node.name, "ip": node.ip, "node_type": node.node_type, "group_name": node.group_name, "group_color": node.group_color}
    else:
        data = request.form.to_dict()
        id = data['id']
        data.pop('csrf_token')
        data.pop('id')
        node = Node.query.filter_by(id=id).first()
        if node.ip != data["ip"]:
            target = SmokepingTarget.query.filter_by(target_id=node.id).first()
            if target is not None:
                target.update(
                    host=data["ip"], smokeping_path="/{}~{}".format(data["ip"].replace(".", "_"), target.slave))
        node.update(**data)
        return {'error': 0, 'info': "更新成功"}


@blueprint.route("/node_list", methods=['GET', 'POST'])
@login_required
@check_topology_get
def node_list():
    if request.method == 'POST':
        topology_name = request.form.get('topology_name')
        name = request.form.get('name')
        ip = request.form.get('ip')
        node_type = request.form.get('node_type')
        fx = request.form.get('fx', type=float, default=0)
        fy = request.form.get('fy', type=float, default=0)
        node = Node.query.filter(text('topology_name="{}" and name="{}" and ip="{}"'.format(
            topology_name, name, ip))).first()
        if node is not None:
            return {'error': 1, 'info': '节点不能重复添加！'}

        if fx != 0 or fy != 0:
            node = Node.create(name=name, topology_name=topology_name,
                               ip=ip, node_type=node_type, fx=fx, fy=fy)
        else:
            node = Node.create(
                name=name, topology_name=topology_name, ip=ip, node_type=node_type)
        _topology_get_all_zabbix_name(topology_name)
        return {'error': 0, 'info': '创建成功', "id": node.id}
    search = request.args.get('search', default="")
    topology_name = request.args.get('topology_name', default="")
    if topology_name != '':
        query = topology_name
    else:
        query = "{}".format(search)
    nodes = Node.query.filter(text('topology_name = "{}"'.format(query))).order_by(
        Node.topology_name).all()
    data = [{"id": n.id, "name": n.name, "topology_name": n.topology_name, 'ip': n.ip, "group_name": n.group_name,
             "group_color": n.group_color, "node_type": n.node_type, "node_type_cn_name": n.node_type_cn_name()} for n in nodes]
    return jsonify(data)

@blueprint.route("/admin_ping_client_page")
@login_required
@check_admin
def ping_client_page():
    operate = request.args.get("operate",type=int,default=0)
    topology_name = request.args.get('topology_name',default="")
    if operate == 1:
        offset = request.args.get('offset',type=int)
        limit = request.args.get('limit',type=int)
        search = request.args.get('search',default="")
        page = offset/limit+1
        pagenation = GtkPingClient.query.order_by(GtkPingClient.id).paginate(page=page,per_page=limit)
        gpcs = pagenation.items
        total = pagenation.total
        data = [{"id":g.id,
            "hostname":g.hostname,
            "description":g.description,
            "ip":g.ip,
            "enabled":g.enabled,
            "time_out":g.time_out,
            "time_interval":g.time_interval,
            "ping_count":g.ping_count,
            "avg_rtt":g.avg_rtt,
            "packet_loss":g.packet_loss
        } for g in gpcs]
        return {'total':total,'totalNotFiltered':total,'rows':data}
    else:
        client_list_sql = GtkPingClient.query.order_by(GtkPingClient.hostname).all()
        client_list = [c.hostname for c in client_list_sql]
    return render_template("topology/ping_client.html",client_list=client_list,topology_name=topology_name)

@blueprint.route("/smokeping_targets_cfg_page")
@login_required
@check_topology_get
def smokeping_targets_cfg_page():
    topology_name = request.args.get("topology_name")
    links = Link.query.filter_by(topology_name=topology_name).all()
    return render_template("topology/smokeping_targets_cfg.html",topology_name=topology_name,links=links)

@blueprint.route("/link_manage_page/")
@login_required
@check_topology_get
def link_manage_page():
    topology_name = request.args.get("topology_name")
    from_where= request.args.get('from_where',default="config")
    topology_name_list = current_user.get_topology_list()
    return render_template("topology/link_manage_page.html",topology_name=topology_name,tpnl=topology_name_list,from_where=from_where)

@blueprint.route("/delete_a_topology")
@login_required
@check_topology_get
def delete_a_topology():
    topology_name = request.args.get('topology_name')
    if delete_topology(topology_name):
        return {'error':0,'info':'删除完毕'}
    return {'error':1,'info':'删除失败，请联系管理员'}

@blueprint.route("/create_nodes_piliang",methods=["POST"])
@login_required
@check_topology_post
def create_nodes_piliang():
    data_string = request.form.get("data")
    topology_name = request.form.get("topology_name")
    data = json.loads(data_string)
    for d in data:
        node = Node.query.filter(text("ip='{}' and topology_name='{}'".format(d["ip"].strip(),topology_name))).first()
        if node is not None:
            continue
        node = Node.create(name=d["name"],ip=d["ip"].strip(),topology_name=topology_name,group_name=d["group_name"],group_color="#CCFFCC",node_type="PC")
        switch = Node.query.filter(text("ip='{}' and topology_name='{}'".format(d["uplink_ip"].strip(),topology_name))).first()
        if switch is not None:
            Link.create(topology_name=topology_name,source=switch.id,target=node.id)
    _topology_get_all_zabbix_name(topology_name)
    return {"error":0,"info":"创建成功！"}

@blueprint.route("/create_switches_piliang",methods=["POST"])
@login_required
@check_topology_post
def create_switches_piliang():
    data_string = request.form.get("data")
    topology_name = request.form.get("topology_name")
    data = json.loads(data_string)

    node_types = NodeType.query.all()
    node_type_list = [n.name for n in node_types]
    tip_flag = False

    for d in data:
        if d['node_type'] not in node_type_list:
            tip_flag = True
            continue
        if "ip" not in d:
            continue
        node = Node.query.filter(text("ip='{}' and topology_name='{}'".format(d["ip"],topology_name))).first()
        if node is not None:
            continue
        node = Node.create(name=d["name"],ip=d["ip"],topology_name=topology_name,node_type=d['node_type'])
        if "uplink_ip" not in d:
            continue
        switch = Node.query.filter(text("ip='{}' and topology_name='{}'".format(d["uplink_ip"],topology_name))).first()
        if switch is not None:
            Link.create(topology_name=topology_name,source=switch.id,target=node.id)
    if tip_flag:
        return {"error":1,"info":"存在设备类型填写错误的情况！"}
    _topology_get_all_zabbix_name(topology_name)
    return {"error":0,"info":"创建成功！"}

@blueprint.route("/node_group_config_page")
@login_required
def node_group_config_page():
    edit_flag = False
    if current_user.is_admin or current_user.get_role_value('has_config') == "1":
        edit_flag = True
    topology_name = request.args.get("topology_name")
    from_where = request.args.get('from_where',default="")
    group_list = db.session.execute(text("select distinct group_name from nodes where topology_name = '{}' and NOT group_name IS NULL and group_name != ''".format(topology_name))).fetchall()
    no_group_list = db.session.execute(text("select id,name,ip from nodes where topology_name = '{}' and (group_name IS NULL or group_name = '')".format(topology_name))).fetchall()
    return render_template("topology/node_group_config.html",
                           topology_name=topology_name,
                           group_list=group_list,
                           no_group_list=no_group_list,
                           edit_flag=edit_flag,
                           from_where=from_where)


@blueprint.route("/get_alert_suggestions",methods=['POST'])
@login_required
@csrf_protect.exempt
def get_alert_suggestions():
    data_string = request.form.get('data')
    data = json.loads(data_string)
    results = []
    for d in data:
        suggestion = AlertSuggestion.query.filter(text('node_type = "{}" and regexp_string != "" and \'{}\' REGEXP regexp_string'.format(d['node_type'],d['alert']))).first()
        if suggestion is None:
            print(d)
        else:
            results.append({'name':suggestion.name,'reason':suggestion.reason,'suggestion':suggestion.suggestion,'node_info':d['node_name']})
    return {'error':0,'results':results}

@blueprint.route("/node_type_list",methods=["GET","POST"])
@login_required
def node_type_list():
    if request.method == "POST":
        data = request.form.to_dict()
        data.pop("csrf_token")
        NodeType.create(**data)
        return {"error":0,"info":"创建成功！"}
    else:
        operate = request.args.get("operate",default=1,type=int)
        id = request.args.get("id",type=int)
        if operate == 0:
            nt = NodeType.query.filter_by(id=id).first()
            if nt.name in ["DBServer","VirtualMachine","Server","PC","SANSwitch","JieRuSwitch","HuiJuSwitch","CoreSwitch","Farm","APPServerVirtualMachine","FireWall","AP"]:
                return {"error":1,"info":"属于基本节点，无法删除！"}
            count = db.session.execute(text('select count(*) from nodes where node_type="{}"'.format(nt.name))).fetchone()
            if count[0] > 0:
                return {"error":1,"info":"请先修改拓扑图节点的类型！"}
            else:
                count = db.session.execute(text('select count(*) from zabbix_template where node_type="{}"'.format(nt.name))).fetchone()
                if count[0] > 0:
                    return {"error":1,"info":"请先修改监控项模板中的节点类型！"}

            nt.delete()
            return {"error":0,"info":"删除成功！"}
        nts = NodeType.query.all()
        data = [{"id":n.id,"name":n.name,"img_url":n.img_url,"cn_name":n.cn_name,"keyword":n.keyword,"cmdb_class":n.cmdb_class} for n in nts]
        return jsonify(data)

@blueprint.route("/edit_node_type",methods=["POST"])
@login_required
def edit_node_type():
    data = request.form.to_dict()
    data.pop("csrf_token")
    id = data.pop("id")
    nt = NodeType.query.filter_by(id=id).first()
    rename_flag = False
    old_name = nt.name
    new_name = data["name"]
    if new_name != old_name:
        rename_flag = True
    
    nt.update(**data)

    if rename_flag:

        #修改节点中的类型：
        nodes = Node.query.filter_by(node_type=old_name).all()
        for n in nodes:
            n.update(node_type=new_name)

        #修改zabbix template表：
        zts = ZabbixTemplate.query.filter_by(node_type=old_name).all()
        for z in zts:
            z.update(node_type=new_name)
    return {"error":0,"info":"更新成功"}


@blueprint.route("/node_group_config_get",methods=["GET","POST"])
@login_required
def node_group_config_get():
    if request.method == "GET":
        get_type = request.args.get("get_type")
        topology_name = request.args.get("topology_name")
        group_name = request.args.get("group_name")
        if get_type == "group_members":
            members = db.session.execute(text("select id,name,ip,group_color from nodes where topology_name = '{}' and group_name='{}'".format(topology_name,group_name))).fetchall()
            data = [{"id":m.id,"name":m.name,"color":m.group_color,"ip":m.ip} for m in members]
            return {'data':data}
        elif get_type == "no_group_nodes":
            members = db.session.execute(text("select id,name,ip from nodes where topology_name = '{}' and (group_name IS NULL or group_name = '')".format(topology_name))).fetchall()
            data = [{"id":m.id,"name":m.name,"ip":m.ip} for m in members]
            return {'data':data}
        elif get_type == "group_list":
            members = db.session.execute(text("select distinct group_name from nodes where topology_name = '{}' and NOT group_name IS NULL and group_name != ''".format(topology_name))).fetchall()
            data = [ m[0] for m in members]
            return {'data':data}
        

@blueprint.route("/edit_nodes_group",methods=['POST'])
@login_required
def edit_nodes_group():
    node_list_jsonstring = request.form.get('node_list')
    group_name = request.form.get('group_name')
    group_color = request.form.get('group_color')

    if node_list_jsonstring == "all":
        topology_name = request.form.get('topology_name')
        nodes = Node.query.filter(text("topology_name='{}' and group_name='{}'".format(topology_name,group_name))).all()
        for n in nodes:
            n.update(group_color=group_color)
        return {"error":0,"info":"上传成功"}

    node_list = json.loads(node_list_jsonstring)
    for n_id in node_list:
        node = Node.query.filter_by(id=n_id).first()
        node.update(group_name=group_name,group_color=group_color)
    
    return {"error":0,"info":"上传成功"}

@blueprint.route("/ping_client_info_edit",methods=['POST'])
@login_required
def ping_client_info_edit():
    data = request.form.to_dict()
    del data['csrf_token']
    id = data['id']
    gclient = GtkPingClient.query.filter_by(id=id).first()
    del data['id']
    gclient.update(**data)
    return {'error':0,'info':'更新成功'}

@blueprint.route('/ping_client_remove')
@login_required
def ping_client_remove():
    hostname = request.args.get('hostname',default='')
    if hostname == '':
        return {'error':1,'info':"客户端不能为空"}
    db.session.execute(text('update links set smokeping_path=NULL where smokeping_path like "%~{}"'.format(hostname)))
    db.session.execute(text('delete from smokeping_targets where slave="{}"'.format(hostname)))
    db.session.execute(text('delete from gtk_ping_clients where hostname="{}"'.format(hostname)))
    db.session.commit()
    return {'error':0,'info':"删除完毕"}

@blueprint.route('/exchange_client_config',methods=['POST'])
@login_required
def exchange_client_config():
    source = request.form.get('source_hostname',default='')
    target = request.form.get('target_hostname',default='')
    if source == target:
        return {'error':1,'info':"迁移客户端不能相同！"}

    links = Link.query.filter(text('smokeping_path like "%~{}"'.format(source))).all()
    for l in links:
        l.update(smokeping_path=l.smokeping_path.replace(source,target))
    sts = SmokepingTarget.query.filter_by(slave=source).all()
    for s in sts:
        s.update(slave=target,smokeping_path=s.smokeping_path.replace(source,target))
    return {'error':0,'info':"迁移完毕"}

@blueprint.route("/target_list")
@login_required
def target_list():
    offset = request.args.get('offset',type=int)
    limit = request.args.get('limit',type=int)
    search = request.args.get('search',default="")
    query = "%{}%".format(search)
    page = offset/limit+1
    pagenation = SmokepingTarget.query.filter(text('topology_name like "{}"'.format(query))).order_by(SmokepingTarget.id).paginate(page=page,per_page=limit)
    targets = pagenation.items
    total = pagenation.total
    data = [{"id":t.id,"host":t.host,"link_id":t.link_id,"link_name":t.get_link_name(),"slave":t.slave} for t in targets]
    return {'total':total,'totalNotFiltered':total,'rows':data}


@blueprint.route("/ping_client_list")
@login_required
def ping_client_list():
    offset = request.args.get('offset',type=int)
    limit = request.args.get('limit',type=int)
    search = request.args.get('search',default="")
    page = offset/limit+1
    pagenation = GtkPingClient.query.order_by(GtkPingClient.id).paginate(page=page,per_page=limit)
    gpcs = pagenation.items
    total = pagenation.total
    data = [{"id":g.id,
        "hostname":g.hostname,
        "description":g.description,
        "ip":g.ip,
        "enabled":g.enabled,
        "time_out":g.time_out,
        "time_interval":g.time_interval,
        "ping_count":g.ping_count,
        "avg_rtt":g.avg_rtt,
        "packet_loss":g.packet_loss
    } for g in gpcs]
    return {'total':total,'totalNotFiltered':total,'rows':data}

@blueprint.route("/smokeping_edit_targets",methods=["GET","POST"])
@login_required
def smokeping_edit_targets():
    if request.method == "POST":
        operate = request.form.get("operate",type=int,default=0)
        if operate == 0:
            ip_pattern = re.compile(r'\d+\.\d+\.\d+\.\d+')
            topology_name = request.form.get("topology_name")
            slave = request.form.get("slave")
            is_client = 0
            gclient = GtkPingClient.query.filter_by(hostname=slave).first()
            if gclient is not None:
                is_client = 1
            data_string = request.form.get("data")
            data = json.loads(data_string)
            
            #存在重复的smokeping target主机，需要弹出一个提示：
            repeat_flag = False

            for d in data:
                break_flag = False
                ip = d["ip"]
                if not ip_pattern.match(ip):
                    if '.com' in ip or '.cn' in ip or '.org' in ip or '.net' in ip:
                        pass
                    else:
                        ip = "{}.gtsc.com".format(d["ip"])
                sts = SmokepingTarget.query.filter_by(host=ip).all()

                #判断是否存在多slave的情况
                multi_slave = 0
                if sts is not None and len(sts) > 0:
                    for st in sts:
                        if st.slave == slave:
                            break_flag = True
                            repeat_flag = True
                            break
                    if not break_flag:
                        multi_slave = 1
                        for st in sts:
                            st.update(multi_slave = 1)
                if break_flag:
                    continue

                link = Link.query.filter_by(target=d["id"]).first()
                if link is not None:
                    SmokepingTarget.create(host=ip,target_id=d["id"],link_id=link.id,slave=slave,topology_name=topology_name,smokeping_path="/{}~{}".format(ip.replace('.','_'),slave),multi_slave=multi_slave,is_gtk_client=is_client)
                else:
                    SmokepingTarget.create(host=ip,target_id=d["id"],slave=slave,topology_name=topology_name,smokeping_path="/{}~{}".format(ip.replace('.','_'),slave),multi_slave=multi_slave,is_gtk_client=is_client)
            if repeat_flag:
                return {"error":0,"info":"添加成功,部分host与其他项目重复，请通过【连线设置】中的【复制Ping监控项】按钮复用相关监控和告警！"}
            else:
                return {"error":0,"info":"添加成功"}
        elif operate == 1:
            target_id = request.form.get("target_id")
            link_id = request.form.get("link_id")
            host = request.form.get("host")
            st = SmokepingTarget.query.filter_by(id=target_id).first()
            if host != '' and st.host != st:
                st.update(link_id=link_id,host=host)
            else:
                st.update(link_id=link_id)
            return {"error":0,"info":"修改成功"}

@blueprint.route("/target_ping_del")
@login_required
def target_ping_del():
    id = request.args.get('id',type=int)
    st = SmokepingTarget.query.filter_by(id=id).first()
    st.delete()
    return {"error":0,"info":"删除成功"}


@blueprint.route("/link_list",methods=['GET','POST'])
@login_required
@check_topology_get
def link_list():
    if request.method == 'POST':
        topology_name = request.form.get('topology_name')
        source = request.form.get('source',type=int)
        target = request.form.get('target',type=int)
        if target == source:
            return {'error':1,'info':'节点不能自己连自己！'}
        link = Link.query.filter(text('topology_name="{}" and ((source={} and target={}) or (source={} and target={}))'.format(topology_name,source,target,target,source))).first()
        if link is not None:
            return {'error':1,'info':'节点不能重复添加！'}
        link = Link.create(topology_name=topology_name,source=source,target=target)
        return {'error':0,'info':'创建成功','id':link.id}
    search = request.args.get('search',default="")
    topology_name = request.args.get('topology_name',default="")
    if topology_name != '':
        query = topology_name
    else:
        query = "{}".format(search)
    links = Link.query.filter(text('topology_name = "{}"'.format(query))).order_by(Link.topology_name).all()
    data = [{"id":l.id,"source":l.source,"target":l.target,"source_name":l.get_source_name(),"target_name":l.get_target_name(),"topology_name":l.topology_name,"smokeping_path":l.smokeping_path,"source_port":l.source_port,"target_port":l.target_port,"need_alert":l.need_alert,"alert_inerval":l.alert_inerval,'avg_rtt':l.avg_rtt,'alert_custom_name':l.alert_custom_name} for l in links]
    return jsonify(data)


@blueprint.route("/get_nodes_for_link")
@login_required
@check_topology_get
def get_nodes_for_link():
    topology_name=request.args.get("topology_name",default="")
    metric_type = request.args.get("metric_type",type=int,default=0)
    if metric_type == 0:
        nodes = Node.query.filter_by(topology_name=topology_name).order_by(Node.id).all()
        data = [{"id":n.id,"name":n.name} for n in nodes]
    else:
        links = Link.query.filter_by(topology_name=topology_name).order_by(Link.id).all()
        data = [{"id":l.id,"name":l.get_link_name()} for l in links]
    return {"data":data}

@blueprint.route("/edit_link_info")
@login_required
def edit_link_info():
    id = request.args.get("id")
    link = Link.query.filter_by(id=id).first()
    link.delete()
    return {'error':0,'info':'删除成功'}

@blueprint.route('/copy_ping_from_other_project')
@login_required
def copy_ping_from_other_project():
    source_top = request.args.get('source_topology')
    target_top = request.args.get('target_topology')
    if copy_smokeping_path(source_top,target_top):
        return {'error':0,'info':"复制完毕"}
    else:
        return {'error':1,'info':"复制失败"}

@blueprint.route("/edit_link_smokeping_path",methods=['POST'])
@login_required
def edit_link_smokeping_path():
    data = request.form.to_dict()
    data.pop("csrf_token")
    link = Link.query.filter_by(id=data['id']).first()
    if link.need_alert==0 and data['need_alert'] == '1':
        top = Topology.query.filter_by(name = link.topology_name).first()
        data['topology_id'] = top.id
    data.pop("id")
    print(data)
    link.update(**data)
    if link.avg_rtt is not None and link.avg_rtt != '' and 'ms' in link.avg_rtt:
        smpt = SmokepingTarget.query.filter_by(smokeping_path=link.smokeping_path).first()
        smpt.update(avg_rtt=link.avg_rtt)
    return {"error":0,"info":"设置成功"}

# 2026-07-01 需要修改
@blueprint.route("/show_modal")
@login_required
def show_modal():
    node_id = request.args.get("id",type=int)
    from_time = request.args.get("from",type=int)
    to_time = request.args.get("to",type=int)
    metric_type = request.args.get("metric_type",type=int,default=0)
    sql_statment = 'node_id = {} and metric_type = {}'.format(node_id,metric_type)
    metrics = NodeMetric.query.filter(text(sql_statment)).order_by(NodeMetric.name).all()
    ip = None
    items = []
    smokeping_path = ""
    node_type = None
    grafana_token = ''
    grafana_src_ping_delay = GRAFANA_PING_DELAY_URL
    grafana_src_drop_rate = GRAFANA_DROP_RATE_URL
    
    if metric_type == 0:
        node = Node.query.filter_by(id=node_id).first()
        ip = node.ip
        node_type = node.node_type
        items = ZabbixTemplate.query.filter_by(node_type=node.node_type).order_by(ZabbixTemplate.item).all()
        if len(metrics)==0 and len(items) == 0:
            return "未配置任何监控项"
        if node_type == "PC":
            sm = SmokepingTarget.query.filter_by(target_id = node.id).first()
            if sm is None:
                smokepinglink = Link.query.filter_by(target=node.id).first()
                if smokepinglink is not None and smokepinglink.smokeping_path is not None and smokepinglink.smokeping_path != "":
                    smokeping_path = smokepinglink.smokeping_path
            else:
                smokeping_path = sm.smokeping_path
    elif metric_type == 1:
        link = Link.query.filter_by(id=node_id).first()
        if link.smokeping_path is not None and link.smokeping_path != "":
            smokeping_path = link.smokeping_path.replace('/','%2F')
        elif len(metrics)==0:
            return "未配置任何监控项"
        
    
    grafana_token = jwt_generate()
    return render_template("topology/modal_template.html",
                           metrics=metrics,
                           from_time=from_time,
                           to_time=to_time,
                           ip=ip,
                           items=items,
                           metric_type=metric_type,
                           smokeping_path=smokeping_path,
                           node_type=node_type,
                           grafana_token=grafana_token,
                           grafana_src_ping_delay=grafana_src_ping_delay,
                           grafana_src_drop_rate=grafana_src_drop_rate,)

@blueprint.route("/topology_config_select")
@login_required
@check_topology_get
def topology_config_select():
    return render_template("topology/topology_config_select.html")

@blueprint.route("/moni_alert")
@login_required
def moni_alert():
    print(current_user.first_name)
    topology_name = request.args.get("topology_name",default="")
    alert_cache = AlertCache.query.filter_by(topology_name=topology_name).order_by(desc(AlertCache.id)).first()
    if alert_cache is not None and alert_cache.expire_time >= datetime.datetime.now():
        return Response(alert_cache.alert_string, mimetype='application/json')
    return {"node_alerts":{},"link_alerts":{}}

@blueprint.route("/fix_topology_position")
@login_required
def fix_topology_position():
    id = request.args.get("id",type=int)
    fx = request.args.get("fx",type=float)
    fy = request.args.get("fy",type=float)

    node = Node.query.filter_by(id=id).first()
    node.fx = fx
    node.fy = fy
    node.update()
    return {"info":"完成"}

@blueprint.route("/fix_all_topology_position",methods=["POST"])
@login_required
def fix_all_topology_position():
    data_string = request.form.get("data")
    data = json.loads(data_string)
    for d in data:
        id = d['id']
        fx = d['fx']
        fy = d['fy']

        node = Node.query.filter_by(id=id).first()
        node.fx = fx
        node.fy = fy
        node.update()
    return {"info":"完成"}

@blueprint.route('/change_link_type')
@login_required
def change_link_type():
    default_node_type = []
    id = request.args.get('id',type=int)
    link = Link.query.filter_by(id=id).first()
    if link.path_type == 0:
        nodes = Node.query.filter(text(f'id={link.source} or id={link.target}')).all()
        if nodes[0].node_type in default_node_type or nodes[1].node_type in default_node_type:
            path_type=1
        else:
            path_type=2
    elif link.path_type == 1:
        path_type=2
    else:
        path_type=1
    link.update(path_type=path_type)
    return {'error':0,'info':"切换完毕",'path_type':path_type}

@blueprint.route("/gtk_ping_client_register")
def gtk_ping_client_register():
    hostname = request.args.get("hostname")
    gclient = GtkPingClient.query.filter_by(hostname=hostname).first()
    if gclient is None:
        GtkPingClient.create(hostname=hostname)
    return {"is_register":1}

@blueprint.route("/gtk_ping_client_ping_list")
def gtk_ping_client_ping_list():
    hostname = request.args.get("hostname")
    smkp_list = SmokepingTarget.query.filter_by(slave=hostname).all()
    if smkp_list is None or len(smkp_list) == 0:
        return {"need_ping":False,"data":[]}
    gclient = GtkPingClient.query.filter_by(hostname=hostname).first()
    if gclient.enabled == 0:
        return {"need_ping":False,"data":[]}
    data = [{"host":s.host,"smokeping_path":s.smokeping_path,'avg_rtt':s.get_avg_rtt(gclient.avg_rtt)} for s in smkp_list]
    return {"need_ping":True,"data":data,"time_out":gclient.time_out,"time_interval":gclient.time_interval,"ping_count":gclient.ping_count,"avg_rtt":gclient.avg_rtt,"packet_loss":gclient.packet_loss}

@blueprint.route('/ping_target_list')
@login_required
def ping_target_list():
    topology_name = request.args.get('topology_name')
    targets = SmokepingTarget.query.filter_by(topology_name=topology_name).all()
    result = [{'host':t.host,'path':t.smokeping_path} for t in targets]
    return jsonify(result)

@blueprint.route('/get_names_for_alert_center')
@login_required
def get_names_for_alert_center():
    operate = request.args.get('operate',type=int,default=0)
    if operate == 0:
        node_id = request.args.get('node_id',type=int)
        nodes = NodeForAlertCenter.query.filter_by(node_id=node_id).all()
        result = [{'hostname':n.alertcenter_name,'id':n.id} for n in nodes]
        return jsonify(result)
    elif operate == 1:
        node_id = request.args.get('node_id',type=int)
        hostname = request.args.get('hostname')

        node = Node.query.filter_by(id=node_id).first()
        top = Topology.query.filter_by(name=node.topology_name).first()

        NodeForAlertCenter.create(topology_id=top.id,topology_name=top.name,node_id=node_id,alertcenter_name=hostname)

        return {'error':0,'info':'添加完毕'}
    elif operate == 2:
        ids = request.args.getlist('ids[]')
        db.session.execute(text('delete from node_for_alert_centers where id in ({})'.format(','.join(ids))))
        db.session.commit()
        return {'error':0,'info':'删除完毕'}

@blueprint.route('/topology_get_all_zabbix_name')
@login_required
def topology_get_all_zabbix_name():
    is_all = request.args.get('is_all',type=int,default=0)
    if is_all == 0:
        top_name = request.args.get('topology_name')
        if _topology_get_all_zabbix_name(top_name):
            return {'error':0,'info':'同步完毕'}
        else:
            return {'error':1,'info':'发生了位置未知错误'}
    else:
        tops=Topology.query.all()
        for top in tops:
            _topology_get_all_zabbix_name(top.name)
        return {'error':0,'info':'同步完毕'}

def _topology_get_all_zabbix_name(top_name):
    top = Topology.query.filter_by(name=top_name).first()
    nodes = Node.query.filter_by(topology_name=top_name).all()
    ips = [n.ip for n in nodes]
    ip2id = { n.ip:n.id for n in nodes}
    result = alert_get_zabbix_hostname(ips)
    nodes_for_ip = Node.query.filter(text('''
                                          topology_name='{}'
                                          '''.format(top_name,))).all()
    for node in nodes_for_ip:
        n = NodeForAlertCenter.query.filter(text('''
                topology_id={} and node_id={} and alertcenter_name='{}'
            '''.format(top.id,node.id,node.ip))).first()
        if n is None:
            NodeForAlertCenter.create(topology_id=top.id,topology_name=top.name,node_id=node.id,alertcenter_name=node.ip)
    for k,v in result.items():
        for name in v:
            n = NodeForAlertCenter.query.filter(text('''
                topology_id={} and node_id={} and alertcenter_name='{}'
            '''.format(top.id,ip2id[k],name))).first()
            if n is None:
                NodeForAlertCenter.create(topology_id=top.id,topology_name=top.name,node_id=ip2id[k],alertcenter_name=name)
    return True
