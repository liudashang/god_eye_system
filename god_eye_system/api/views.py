from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from flask_login import login_required, login_user, logout_user

from flask_restful import reqparse, abort, Api, Resource

from sqlalchemy import text
from god_eye_system.user.models import Configuration,Role,User,db
from god_eye_system.utils import check_admin

blueprint = Blueprint('api', __name__, url_prefix="/api", static_folder='../static')

api = Api(blueprint)

class Api_setting(Resource):
    #@login_required
    def post(self):
        s_ldap_address = request.form.get("ldap_address","")
        s_ldap_account = request.form.get("ldap_account","")
        s_ldap_password = request.form.get("ldap_password","")
        if s_ldap_account == "" or s_ldap_address == "" or s_ldap_password== "":
            return {"error":1, "info":"配置参数不完整"}
        else:
            try:
                Configuration.create(config_name="ldap_address",config_value=s_ldap_address)
                Configuration.create(config_name="ldap_account",config_value=s_ldap_account)
                Configuration.create(config_name="ldap_password",config_value=s_ldap_password)
            except Exception as e:
                ldap_address = Configuration.query.filter_by(config_name="ldap_address").first()
                ldap_account = Configuration.query.filter_by(config_name="ldap_account").first()
                ldap_password = Configuration.query.filter_by(config_name="ldap_password").first()
                if ldap_address.config_value != s_ldap_address:
                    ldap_address.update(config_value=s_ldap_address)
                if ldap_account.config_value != s_ldap_account:
                    ldap_account.update(config_value=s_ldap_account)
                if ldap_password.config_value != s_ldap_password:
                    ldap_password.update(config_value=s_ldap_password)
            return {"error":0, "info":"配置完成"}

class Api_users_manager(Resource):
    @login_required
    @check_admin
    def get(self):
        offset = request.args.get('offset',type=int)
        limit = request.args.get('limit',type=int)
        search = request.args.get('search',default="")
        page = offset/limit+1
        if search != "":
            pagenation = User.query.filter(text("username like '%{}%' or first_name like '%{}%'".format(search,search))).order_by(User.username).paginate(page=page,per_page=limit)
        else:
            pagenation = User.query.order_by(User.username).paginate(page=page,per_page=limit)
        users = pagenation.items
        total = pagenation.total
        data = [{'username':u.username,'id':u.id,'first_name':u.first_name,'active':u.active,'is_admin':u.is_admin} for u in users]
        return {'total':total,'totalNotFiltered':total,'rows':data}

    @login_required
    @check_admin
    def post(self):
        id = request.form.get("id",type=int)
        first_name = request.form.get("first_name")
        active = request.form.get("active",type=bool)
        is_admin = request.form.get("is_admin",type=bool)

        user = User.query.filter_by(id=id).first()
        user.first_name = first_name
        user.active = active
        user.is_admin = is_admin
        user.update()

        return {"error":0, "info":"保存完成"}

class Api_users_roles(Resource):
    @login_required
    @check_admin
    def get(self):
        offset = request.args.get('offset',type=int)
        limit = request.args.get('limit',type=int)
        search = request.args.get('search',default='')
        page = offset/limit+1
        if search != '':
            pagenation = Role.query.filter(text(f'''name like "%{search}%" or value like "%{search}%"''')).order_by(Role.user_id).paginate(page=page,per_page=limit)
        else:
            pagenation = Role.query.order_by(Role.user_id).paginate(page=page,per_page=limit)
        roles = pagenation.items
        total = pagenation.total
        data = []
        for r in roles:
            d = {"id":r.id,"name":r.name,"value":r.value,"user_id":r.user_id}
            if r.user is None:
                d['user_name'] = '-'
            else:
                d['user_name'] = r.user.first_name
            data.append(d)
        return {'total':total,'totalNotFiltered':total,'rows':data}

    @login_required
    @check_admin
    def post(self):
        op = request.form.get('operate',type=int,default=1)
        if op == 1:
            user_id = request.form.get("user_id",default=0,type=int)
            name = request.form.get("name",default="")
            value = request.form.get("value",default="")
            if user_id == 0 or name == "":
                return {"error":1,"info":"信息填写不完整！"}
            role = Role.query.filter(text("name='{}' and user_id={}".format(name,user_id))).first()
            if role is not None:
                if role.value != value:
                    role.update(value=value)
                    return {"error":0,"info":"权限更新成功！"}
                return {"error":1,"info":"该用户已创建此权限(或权限名称重复)"}
            Role.create(name=name,value=value,user_id=user_id)
            return {"error":0,"info":"创建成功"}
        elif op == 0:
            role_id = request.form.get("id",default=0,type=int)
            role = Role.query.filter_by(id=role_id).first()
            if role is None:
                return {"error":1,"info":"该权限已删除"}
            role.delete()
            return {"error":0,"info":"删除成功"}
        elif op == 2:
            data = request.form.getlist("data[]",type=int)
            for d in data:
                role = Role.query.filter_by(id=d).first()
                db.session.delete(role)
            db.session.commit()
            return {"error":0,"info":"批量删除成功"}
        
            


api.add_resource(Api_setting,"/settings",endpoint="settings")
api.add_resource(Api_users_manager,"/admin_users_manager",endpoint="users_manager")
api.add_resource(Api_users_roles,"/admin_users_roles",endpoint="users_roles")