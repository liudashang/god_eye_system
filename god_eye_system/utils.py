# -*- coding: utf-8 -*-
"""Helper utilities and decorators."""
from flask import flash,request,redirect,url_for
from flask_login import current_user
from functools import wraps
from god_eye_system.user.models import SystemRegister
import hashlib
import datetime


def flash_errors(form, category="warning"):
    """Flash all errors for a form."""
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{getattr(form, field).label.text} - {error}", category)

def check_admin(func):
    @wraps(func)
    def wrapper(*args,**kwargs):
        if '/admin_' in request.path:
            if current_user.is_admin:
                return func(*args,**kwargs)
            else:
                flash("您不具有该功能的权限。", "warning")
                return redirect(url_for("user.members"))
        return func(*args,**kwargs)
    return wrapper

def check_topology_get(func):
    @wraps(func)
    def wrapper(*args,**kwargs):
        if request.method == "GET":
            if current_user.is_admin:
                return func(*args,**kwargs)
            elif current_user.get_role_value('has_config') == "1":
                topology_list = current_user.get_topology_list()
                topology_name = request.args.get('topology_name',default= "")
                if topology_name == "":
                    topology_name = request.args.get('search',default= "")
                if topology_name == "" or (len(topology_list)>0 and topology_name in topology_list):
                    return func(*args,**kwargs)
                else:
                    flash("您不具有该功能的权限。", "warning")
                    return redirect(url_for("user.members"))
            else:
                flash("您不具有该功能的权限。", "warning")
                return redirect(url_for("user.members"))
        return func(*args,**kwargs)
    return wrapper

def check_topology_post(func):
    @wraps(func)
    def wrapper(*args,**kwargs):
        if request.method == "POST":
            if current_user.is_admin:
                return func(*args,**kwargs)
            elif current_user.get_role_value('has_config') == '1':
                topology_list = current_user.get_topology_list()
                topology_name = request.form.get('topology_name',default= "")
                if topology_name == "" or (len(topology_list)>0 and topology_name in topology_list):
                    return func(*args,**kwargs)
                else:
                    flash("您不具有该功能的权限。", "warning")
                    return redirect(url_for("user.members"))
            else:
                flash("您不具有该功能的权限。", "warning")
                return redirect(url_for("user.members"))
        return func(*args,**kwargs)
    return wrapper
