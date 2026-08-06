#!/usr/bin/python3

import sys
import requests
import re

def task():
    #print(sys.argv[0])
    alert_name = sys.argv[1]
    node_path = '/'+sys.argv[2].replace('.','/')

    all_100_flag = False
    all_u_flag = False

    matchObj = re.match(r'(\S+)\s+\[from (\S+)\]',node_path)
    if matchObj:
        node_path = "{}~{}".format(matchObj.group(1),matchObj.group(2))

    #loss信息处理
    matchObj = re.match(r'loss:\s(.*)',sys.argv[3])
    if matchObj:
        info_string = matchObj.group(1).replace(" ","")
        info_list = info_string.split(',')
        count = len(info_list)
        loop_count = 0
        for i in info_list:
            loop_count += 1
            if i != "100%":
                break
        if count == loop_count:
            all_100_flag = True
        now_loss = info_list[-1]

    #loss信息处理
    matchObj = re.match(r'rtt:\s(.*)',sys.argv[4])
    if matchObj:
        info_string = matchObj.group(1).replace(" ","")
        info_list = info_string.split(',')
        count = len(info_list)
        loop_count = 0
        for i in info_list:
            loop_count += 1
            if i != 'U':
                break
        if count == loop_count:
            all_u_flag = True
        now_rrt = info_list[-1]
        if now_rrt == 'U':
            now_rrt = "中断"
    alert_info = "Ping至少{}次，最新丢包率：{}，最新延迟：{}".format(count,now_loss,now_rrt)

    if all_100_flag and all_u_flag:
        alert_name = "linkdown"

    data = {"alert_name":alert_name,"node_path":node_path,"alert_info":alert_info,"host_ip":sys.argv[5]}
    r = requests.post('http://127.0.0.1:5000',data=data)
    print(r.text)



if __name__ == '__main__':
    task()