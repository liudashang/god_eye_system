# -*- coding: utf-8 -*-
"""User views."""
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user

from god_eye_system.user.models import FavoriteTopology, db, BU, User, Role, Topology
from god_eye_system.utils import check_admin


from sqlalchemy import text

blueprint = Blueprint("user", __name__, url_prefix="/users", static_folder="../static")


@blueprint.route("/")
@login_required
def members():
    """List members."""
    """List members."""
    
    operate = request.args.get('operate',type=int,default=0)
    if operate == 1:
        topology_list = current_user.get_topology_list(True)
        topologys = []
        for t in topology_list:
            alert_status = ""
            if t.alert_status != "":
                if t.ping_status == 0:
                    alert_status = "Ping检测工具失效"+"，"+t.alert_status
                else:
                    alert_status = t.alert_status
            else:
                if t.ping_status == 0:
                    alert_status = "Ping检测工具失效"
                else:
                    alert_status = t.alert_status
            
            topologys.append({'id':t.id,'name':t.name,'bg':t.bg,'bu':t.bu,'alert_status':alert_status,'is_tingxian':t.is_tingxian,'is_eol':t.is_eol,'ping_status':t.ping_status})
        return jsonify(topologys)
    return render_template("users/members.html")

@blueprint.route("/config_my_favorite")
@login_required
def config_my_favorite():
    operate = request.args.get('operate',type=int,default=0)
    if operate == 1:
        ids = request.args.getlist('ids[]',type=int)
        group_name = request.args.get('group_name',default='默认分组')
        username = current_user.username
        for id in ids:
            FavoriteTopology.create(topology_id=id,group_name=group_name,username=username)
        return {'error':0,'info':'收藏成功'}
    elif operate == 0:
        groups = db.session.execute(text('''
            select t.name,ft.group_name,ft.create_time from topologys t join favorite_topologys ft 
            on t.id=ft.topology_id and ft.username = '{}'
            order by ft.group_name, ft.create_time desc
        '''.format(current_user.username))).fetchall()
        group_dict = {}
        index = 0
        for g in groups:
            if g.group_name not in group_dict:
                expanded = 'false'
                show = ''
                collapsed = 'collapsed'
                if index == 0 or g.group_name == '最近访问':
                    expanded = 'true'
                    show = 'show'
                    collapsed = ''
                group_dict[g.group_name] = {}
                group_dict[g.group_name]['tops'] = []
                group_dict[g.group_name]['html_id'] = ['headingFavorite'+str(index),'collapseFavorite'+str(index),expanded,show,collapsed]
                index += 1
            group_dict[g.group_name]['tops'].append(g.name)
        return render_template('users/favorite_topologys.html',data=group_dict)
    
@blueprint.route("/admin_users_manager")
@login_required
@check_admin
def users_manager():
    '''用户账户管理界面'''
    topology_list = current_user.get_topology_list()
    return render_template("users/users_manager.html",topology_list=topology_list)

@blueprint.route("/bu_list_simple")
@login_required
def bu_list_simple():
    bus = BU.query.filter(text("bu_type=1 and status=1")).all()
    data = [b.name for b in bus]
    return jsonify(data)

@blueprint.route("/bu_list_simple_bu")
@login_required
def bu_list_simple_bu():
    bu_parent = request.args.get('bu_parent')
    bus = BU.query.filter(text("bu_type=2 and status=1 and bu_parent='{}'".format(bu_parent))).all()
    data = [b.name for b in bus]
    return jsonify(data)

@blueprint.route("/admin_user_roles_info")
@login_required
@check_admin
def user_roles_info():
    user_id = request.args.get('user_id',type=int)
    user = User.query.filter_by(id=user_id).first()
    g_or_u = user.get_role_value('g_or_u')
    has_config = user.get_role_value('has_config')
    has_edit_node_info = user.get_role_value('has_edit_node_info')
    bg_fanwei = user.get_role_value('bg_fanwei')
    if g_or_u == 'bu':
        bu_fanwei = user.get_role_value('bu_fanwei')
        return {'g_or_u':g_or_u,'has_config':has_config,'has_edit_node_info':has_edit_node_info,'bg_fanwei':bg_fanwei,'bu_fanwei':bu_fanwei}
    elif g_or_u == 'one_top':
        topology = user.get_role_value('has_one_topology')
        return {'g_or_u':g_or_u,'has_config':has_config,'has_edit_node_info':has_edit_node_info,'topology':topology}
    else:
        return {'g_or_u':g_or_u,'has_config':has_config,'has_edit_node_info':has_edit_node_info,'bg_fanwei':bg_fanwei}

@blueprint.route("/admin_users_roles")
@login_required
@check_admin
def users_roles():
    '''权限管理界面'''
    return render_template("users/roles.html")

@blueprint.route("/admin_bu_config_page")
@login_required
@check_admin
def bu_config_page():
    topology_name = request.args.get('topology_name',default=None)
    return render_template("users/bu_config.html",topology_name=topology_name)

@blueprint.route("/admin_bu_list",methods=["GET","POST"])
@login_required
@check_admin
def bu_list():
    if request.method == "GET":
        offset = request.args.get('offset',type=int)
        limit = request.args.get('limit',type=int)
        search = request.args.get('search',default="")
        page = offset/limit+1
        if search != "":
            pagenation = BU.query.filter(text("name like '%{}%'".format(search))).order_by(BU.id).paginate(page=page,per_page=limit)
        else:
            pagenation = BU.query.order_by(BU.id).paginate(page=page,per_page=limit)

        bus = pagenation.items
        total = pagenation.total
        data = [{"id":b.id,"name":b.name,"bu_type":b.bu_type,"status":b.status,"bu_parent":b.bu_parent} for b in bus]
        return {'total':total,'totalNotFiltered':total,'rows':data}
    else:
        data = request.form.to_dict()
        data.pop("csrf_token")
        BU.create(**data)
        return {"error":0,"info":"创建成功"}
    

@blueprint.route("/admin_bu_rename",methods=["POST"])
@login_required
@check_admin
def bu_rename():
    bg_id = request.form.get("id",type=int)
    old_name = request.form.get("old_name")
    new_name = request.form.get("new_name")
    bu = BU.query.filter_by(id=bg_id).first()
    if bu.name != old_name:
        return {"error":1,"info":"原名称不正确，无法修改！"}
    bu.update(name=new_name)
    
    if bu.bu_type == 1:
        bus = BU.query.filter_by(bu_parent=old_name).all()

        for b in bus:
            b.update(bu_parent=new_name)

        topologys = Topology.query.filter_by(bg=old_name).all()
        for t in topologys:
            t.update(bg=new_name)
        
        roles = Role.query.filter(text("name='bg_fanwei' and value like '%{}%'".format(old_name))).all()

        for r in roles:
            r.update(value=r.value.replace(old_name,new_name))
    else:
        topologys = Topology.query.filter(text("bg='{}' and bu='{}'".format(bu.bu_parent,old_name))).all()
        for t in topologys:
            t.update(bu=new_name)

        roles = Role.query.filter(text("name='bu_fanwei' and value like '%{}%'".format(old_name))).all()
        for r in roles:
            if r.user.get_role_value("bg_fanwei") == bu.bu_parent:
                r.update(value=r.value.replace(old_name,new_name))
    return {"error":0,"info":"更新完毕！"}

@blueprint.route("/admin_move_bu_page")
@login_required
@check_admin
def move_bu_page():
    id = request.args.get("id",type=int)
    bu = BU.query.filter_by(id=id).first()

    #获取人员信息：
    #获取项目信息：
    if bu.bu_type == 1:
        roles = Role.query.filter(text("name = 'bg_fanwei' and value like '%{}%'".format(bu.name))).all()

        topologys = Topology.query.filter(text("bg = '{}'".format(bu.name))).all()
    else:
        tmp_roles = Role.query.filter(text("name = 'bu_fanwei' and value like '%{}%'".format(bu.name))).all()
        roles = [r for r in tmp_roles if r.user.get_role_value('bg_fanwei') == bu.bu_parent]

        topologys = Topology.query.filter(text("bg = '{}' and bu = '{}'".format(bu.bu_parent,bu.name))).all()

    
    return render_template("users/move_bu.html",bu=bu,roles=roles,topologys=topologys)

@blueprint.route("/admin_delete_bu")
@login_required
@check_admin
def delete_bu():
    id = request.args.get("id",type=int)
    bu = BU.query.filter_by(id=id).first()

    if bu.bu_type == 1:
        roles = Role.query.filter(text("name = 'bg_fanwei' and value like '%{}%'".format(bu.name))).all()

    else:
        tmp_roles = Role.query.filter(text("name = 'bu_fanwei' and value like '%{}%'".format(bu.name))).all()
        roles = [r for r in tmp_roles if r.user.get_role_value('bg_fanwei') == bu.bu_parent]

    for r in roles:
        tmp_list = r.value.split(",")
        if len(tmp_list) == 1:
            r.delete()
        else:
            final_list = [t for t in tmp_list if t != bu.name]
            r.update(value=','.join(final_list))

    bu.update(status=0)
    return {"error":0,"info":"变更成功！"}