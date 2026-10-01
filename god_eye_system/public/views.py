# -*- coding: utf-8 -*-
"""Public section, including homepage and signup."""
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
    send_from_directory,
    jsonify,
)
from flask_login import login_required, login_user, logout_user, current_user

from god_eye_system.extensions import login_manager
from god_eye_system.public.forms import LoginForm
from god_eye_system.user.forms import RegisterForm
from god_eye_system.user.models import User, Configuration, SystemRegister
from god_eye_system.utils import flash_errors, check_admin
from god_eye_system.settings import DOWNLOAD_FILE_PATH

import random
import string
import os

blueprint = Blueprint("public", __name__, static_folder="../static")


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    return User.get_by_id(int(user_id))


@blueprint.route("/", methods=["GET", "POST"])
def home():
    """Home page."""
    form = LoginForm(request.form)
    current_app.logger.info("Hello from the home page!")
    # Handle logging in
    if request.method == "POST":
        if form.validate_on_submit():
            login_user(form.user)
            flash("登录成功。", "success")
            redirect_url = request.args.get("next") or url_for("user.members")
            return redirect(redirect_url)
        else:
            flash_errors(form)
    return render_template("public/login.html", form=form)


@blueprint.route("/logout/")
@login_required
def logout():
    """Logout."""
    logout_user()
    flash("您已经登出系统。", "info")
    return redirect(url_for("public.home"))

@blueprint.route("/test_register/", methods=["GET", "POST"])
def test_register():
    """Register new user."""
    admin = User.query.filter_by(username="admin").first()
    if admin is not None:
        return redirect(url_for("public.home"))
        
    form = RegisterForm(request.form)
    if form.validate_on_submit():
        is_admin = False
        if form.username.data == "admin":
            is_admin = True
        User.create(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data,
            active=True,
            is_admin=is_admin,
        )
        flash("账户注册成功。", "success")
        # return redirect(url_for("public.home"))
    else:
        flash_errors(form)
    return render_template("public/register.html", form=form)


@blueprint.route("/admin_register/", methods=["GET", "POST"])
@login_required
@check_admin
def register():
    """Register new user."""
    form = RegisterForm(request.form)
    if form.validate_on_submit():
        User.create(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data,
            active=True,
        )
        flash("账户注册成功。", "success")
        # return redirect(url_for("public.home"))
    else:
        flash_errors(form)
    return render_template("public/register.html", form=form)


@blueprint.route("/about/")
def about():
    """About page."""
    form = LoginForm(request.form)
    return render_template("public/about.html", form=form)

@blueprint.route("/admin_settings", methods=["GET"])
@login_required
@check_admin
def setting():
    c_ldap_address = Configuration.query.filter_by(config_name="ldap_address").first()

    if c_ldap_address is None:
        data = ["暂未配置LDAP", "暂未配置LDAP"]
    else:
        c_ldap_account = Configuration.query.filter_by(config_name="ldap_account").first()
        data = [c_ldap_address.config_value, c_ldap_account.config_value]
    return render_template("public/settings.html", data=data)

@blueprint.route('/download/excel/<path:name>')
@login_required
def download_excel(name):
    return send_from_directory(DOWNLOAD_FILE_PATH+"/excel/", name, as_attachment=True)

@blueprint.route('/upgrade/<path:name>')
def upgrade(name):
    return send_from_directory(DOWNLOAD_FILE_PATH+"/clients/", name, as_attachment=True)

@blueprint.route('/update_user_gonggao')
@login_required
def update_user_gonggao():
    gonggao = request.args.get("gonggao", default="")
    current_user.update(gonggao=gonggao)
    return {"error": 0, "info": "更新成功"}

@blueprint.route('/upload_user_guide', methods=['POST'])
@login_required
def upload_user_guide():
    f = request.files['file']
    f.save('downloads/document/天眼系统用户说明书.docx')
    return {"error": 0, "info": "上传完毕"}

@blueprint.route('/download/document/<path:name>')
@login_required
def download_document(name):
    return send_from_directory(DOWNLOAD_FILE_PATH+"/document/", name, as_attachment=True)

@blueprint.route('/admin_system_register_view', methods=['GET', 'POST'])
@login_required
@check_admin
def system_register_view():
    if request.method == 'GET':
        operate = request.args.get('operate', type=int, default=0)
        if operate == 0:
            return render_template("public/system_register.html")
        elif operate == 1:
            regs = SystemRegister.query.all()
            result = [{'id': r.id, 'name': r.name, 'sys_key': r.sys_key,
                       'sys_secret': r.sys_secret, 'description': r.description} for r in regs]
            return jsonify(result)
        elif operate == 2:
            id = request.args.get('id', type=int)
            reg = SystemRegister.query.filter_by(id=id).first()
            reg.delete()
            return {'error': 0, 'info': '删除完毕'}
    else:
        name = request.form.get('name')
        description = request.form.get('description')

        key_len = 16
        secret_len = 8
        sys_key = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(key_len))
        sys_secret = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(secret_len))

        sys = SystemRegister.query.filter_by(name=name).first()
        if sys is not None:
            return {'error': 1, 'info': '系统名称不能重复'}

        SystemRegister.create(name=name, sys_key=sys_key, sys_secret=sys_secret, description=description)

        return {'error': 0, 'info': '添加成功'}

@blueprint.route('/admin_show_system_log')
@login_required
@check_admin
def show_system_log():
    operate = request.args.get('operate',type=int,default=0)
    files = sorted(os.listdir('/tmp'))
    if operate == 0:
        return render_template('public/system_info_view.html',files=files)
    elif operate == 1:
        file_name = request.args.get('file')
        result = os.popen(f"tail -n 2000 /tmp/{file_name}")
        out = result.read()
        return {'error':0,'info':'读取成功','content':out}
    
