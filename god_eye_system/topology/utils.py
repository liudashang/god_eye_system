from god_eye_system.user.models import db, Link

from sqlalchemy import text
import jwt
import datetime

def chech_topology_eol(topology_name):
    
    db.session.execute(text(f'''
                        update smokeping_targets st join
                        links l on st.link_id = l.id
                        and st.topology_name = '{topology_name}'
                        set l.smokeping_path = ""
                       '''))
    db.session.execute(text(f'delete from smokeping_targets where topology_name="{topology_name}"'))
    db.session.commit()
    return True

def delete_topology(topology_name):
    chech_topology_eol(topology_name)
    db.session.execute(text("delete from links where topology_name='{}'".format(topology_name)))
    db.session.execute(text("delete from nodes where topology_name='{}'".format(topology_name)))
    db.session.execute(text("delete from topologys where name='{}'".format(topology_name)))
    db.session.commit()
    return True

def copy_smokeping_path(source_topology,target_topology):
    source_datas = db.session.execute(text('''
        select l.id,l.topology_name,n1.ip as source_ip,n2.ip as target_ip,l.smokeping_path from links l inner join nodes n1 on l.source = n1.id INNER join nodes n2 on l.target = n2.id
        where l.topology_name = "{}"
    '''.format(source_topology))).fetchall()

    source_dict = {'{}_{}'.format(d['source_ip'],d['target_ip']):d['smokeping_path'] for d in source_datas}

    target_datas = db.session.execute(text('''
        select l.id,l.topology_name,n1.ip as source_ip,n2.ip as target_ip,l.smokeping_path from links l inner join nodes n1 on l.source = n1.id INNER join nodes n2 on l.target = n2.id
        where l.topology_name = "{}"
    '''.format(target_topology))).fetchall()

    smokeping_target_datas = db.session.execute(text('''
        select st.smokeping_path,n.ip from smokeping_targets st
        inner join nodes n 
        on st.target_id = n.id
        WHERE
        st.slave in (select distinct slave from smokeping_targets where topology_name = '{}')
        AND
        st.topology_name != '{}'
        AND
        n.ip in (select ip from nodes where topology_name='{}')
    '''.format(target_topology,target_topology,target_topology))).fetchall()
    target_dict = {s['ip']:s['smokeping_path'] for s in smokeping_target_datas}

    for t in target_datas:
        ip_key = '{}_{}'.format(t['source_ip'],t['target_ip'])
        if ip_key in source_dict and source_dict[ip_key] is not None and source_dict[ip_key] != "":
            link = Link.query.filter_by(id = t['id']).first()
            link.update(smokeping_path=source_dict[ip_key])
        if t['smokeping_path'] is None or t['smokeping_path'] == "":
            if t['target_ip'] in target_dict:
                link = Link.query.filter_by(id = t['id']).first()
                link.update(smokeping_path=target_dict[t['target_ip']])
    
    return True

def jwt_generate():
    # 读取私钥和公钥
    with open('pytools/once_job/private.pem', 'r') as f:
        private_key = f.read()
    with open('pytools/once_job/public.pem', 'r') as f:
        public_key = f.read()
    
    # 需要传递的信息
    payload = {
        'iss': 'godeye',  # 签发者
        'iat': int(datetime.datetime.now().timestamp()),  # 签发时间
        'exp': int(datetime.datetime.now().timestamp()) + 3600,  # 过期时间（一小时，可根据需求修改）
        'sub': 'godeye_user'# 即用户名，注意不能写默认用户名admin
    }
    
    # 使用私钥生成JWT
    token = jwt.encode(payload, private_key, algorithm='RS256')
    
    
    
    print('Generated Token:', token)
    
    # 使用公钥验证JWT
    try:
        decoded = jwt.decode(token, public_key, algorithms=['RS256'])
        print('Decoded Token:', decoded)
    except jwt.ExpiredSignatureError:
        print('Token is expired')
    except jwt.InvalidTokenError as e:
        print('Token is invalid:', str(e))
    return token
