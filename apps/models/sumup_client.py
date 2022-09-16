#!/usr/bin/env python3
#
#coding: utf-8
#
# Copyright (C) 2022 Amlogic, Inc. All rights reserved.
#
#
# This source code is subject to the terms and conditions defined in the
# file 'LICENSE' which is part of this source code package.
#
#

import json
import requests
import lxml
import sys
import re
import time
from datetime import datetime, timedelta
from requests import Session
from urllib.parse import urlencode
from bs4 import BeautifulSoup as bs
from argparse import ArgumentParser
import pandas as pd
import copy

URL_HOME='http://aats.amlogic.com:10000/weekly_sumup/'
URL_LOGIN='http://aats.amlogic.com:10000/weekly_sumup/user/login/ad'
URL_MAIN='http://aats.amlogic.com:10000/weekly_sumup/main'
URL_LIST='http://aats.amlogic.com:10000/weekly_sumup/table/list'
URL_SAVE='http://aats.amlogic.com:10000/weekly_sumup/save_report'

DOMAIN='@amlogic.com'
SERVER_CONFIG = "apps/models/cfg/server.json"
MY_SERVER_CONFIG = "apps/models/cfg/server-%s.json"
USERID_PATTERN = '/weekly_sumup/table/member/[1-9][0-9]*/%s'
DEPARTMENTID_PATTERN = "'departmentid':\"[1-9][0-9]*"

POST_HEADERS = {
    "Accpet": "*/*",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Connection": "keep-alive",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74 Safari/537.36",
}

TASK_LIST='./save_report.json'
s = Session()
cookie = ''
global draft_list
draft_list = None
global userid
userid = 0
global departmentid
departmentid = 0

DEBUG_LOG_ENABLE=1

def debug(args):
    if (DEBUG_LOG_ENABLE == 1):
        print(args, file=sys.stderr)

def this_sunday(today):
    today = datetime.strptime(str(today), '%Y-%m-%d')
    return datetime.strftime(today + timedelta(7 - today.weekday() - 1), '%Y-%m-%d')

def last_sunday(today):
    today = datetime.strptime(str(today), '%Y-%m-%d')
    return datetime.strftime(today + timedelta(- today.weekday() - 1), '%Y-%m-%d')

def load_list(task_file):
    f = open(task_file, encoding="utf-8")
    task_list = json.load(f)
    f.close()
    return task_list

def init_config(cfg):
    f = open(cfg, encoding="utf-8")
    server_config = json.load(f)
    f.close()
    return server_config

def matched_userid(matched):
    global userid
    key = matched.group()
    debug(key)
    id = re.findall('\d+', key)
    userid = id[0]
    debug('userid: ' + userid)
    return key

def matched_departmentid(matched):
    global departmentid
    key = matched.group()
    debug(key)
    id = re.findall('\d+', key)
    departmentid = id[0]
    debug('departmentid: ' + departmentid)
    return key

def get_userid(user, text):
    pattern = USERID_PATTERN % (user)
    re.sub(pattern, matched_userid, text, 0, re.IGNORECASE)

def get_departmentid(text):
    global departmentid
    pattern = DEPARTMENTID_PATTERN
    re.sub(pattern, matched_departmentid, text)


def login(u, p):
    print('>> Login ...')
    if (u == None or u ==''):
        user = USER
    else:
        user = u
    if (p == None or p ==''):
        password = PASSWORD
    else:
        password = p

    login_data = {"email": user + DOMAIN, "password": password}
    res = s.post(URL_LOGIN, headers=POST_HEADERS, data=login_data)
    cookie = requests.utils.dict_from_cookiejar(s.cookies)
    print(cookie)
    res = s.get(URL_MAIN)
    if (res.status_code == 200):
        get_userid(user, res.text)
        get_departmentid(res.text)
        return 0
    else:
        return res.status_code

def get_list(date):
    global userid
    global departmentid
    print('date: ' + date)
    data = {
        'id': userid,
        'departmentid': departmentid,
        'date': date,
        'workType': -1,
        'fetchAll': 100,
    }
    res = s.post(URL_LIST, headers=POST_HEADERS, data=data)
    print(res)
    if (res.status_code == 200):
        try:
            task = json.dumps(json.loads(res.text), indent=4, separators=(',', ':'))
        except:
            task = ''
            return None
    else:
        task = ''
    json_task = json.loads(task)
    if (len(json_task['sumup']['data']) > 0):
        return json_task['sumup']['data']
    else:
        return None

def prepare_list(task):
    tmp_draft_list = []
    for item in task:
        sumup_item = {}
        sumup_item['statement'] = item['statement']
        sumup_item['label'] = item['label'] 
        sumup_item['project.id'] = item['projectId']
        sumup_item['workType.id'] = item['workType']
        sumup_item['jiraId'] = item['jiraId']
        sumup_item['workTime'] = str(item['workTime'])
        if (item['isOnTime']):
            sumup_item['isOnTime'] = 'true'
        sumup_item['reason.id'] = item['reason']
        sumup_item['notes'] = item['notes']
        tmp_draft_list.append(sumup_item)

    return tmp_draft_list

def update_list(task_list):
    print('>> Update task list ...')
    print(task_list)
    save_report = urlencode(task_list)
    res = s.post(URL_SAVE, headers=POST_HEADERS, cookies=cookie, data=save_report)
    return res.text

def dump_list(task):
    for item in task:
        task_name = item['statement']
        print('TASK: ' + task_name)

def list_to_html(task):
    df = pd.DataFrame(task)
    return df.to_html(escape=False)

def get_sumup_list(user, date):
    print('>> gen_draft() ...')
    global draft_list
    # Login
    my_server_config = MY_SERVER_CONFIG % user
    server_config = init_config(my_server_config)
    user = server_config["server"]["user"]
    password = server_config["server"]["password"]
    ret = login(user, password)
    if (ret != 0): 
        print('Login failed! Error code: ' + ret)
        return 'Login failed! Error code: ' + ret

    if (date == None or date ==''):
        date = time.strftime('%Y-%m-%d', time.localtime())

    # Get this week work list
    this_list = get_list(this_sunday(date))
    if (this_list == None):
        return "This week work list is empty!"

    print('Get this week work list successfully!')    
    draft_list = prepare_list(this_list)
    dump_list(draft_list)
    return list_to_html(draft_list)
        
def gen_draft(user, date):
    print('>> gen_draft() ...')
    global draft_list

    my_server_config = MY_SERVER_CONFIG % user
    server_config = init_config(my_server_config)
    user = server_config["server"]["user"]
    password = server_config["server"]["password"]
    # Login
    ret = login(user, password)
    if (ret != 0): 
        print('Login failed! Error code: ' + ret)
        return 'Login failed! Error code: ' + ret

    if (date == None or date ==''):
        date = time.strftime('%Y-%m-%d', time.localtime())

    draft_sunday = this_sunday(date)

    # Get last week work list
    last_list = get_list(last_sunday(date))
    if (last_list == None):
        print('Get last week work list failed!')
        draft_list = None
        return "The lask week work list is empty!"
    else:
        print('Get last week work list successfully!')
    
    draft_list = prepare_list(last_list)
    dump_list(draft_list)
    return list_to_html(draft_list)

def submit_draft(user, date):
    global draft_list
    print('>> submit_draft() ...')
    draft_sunday = this_sunday(date)

    # Get this week work list
    this_list = get_list(draft_sunday)
    if (this_list != None):
        return "The work list of this week is already submitted!"

    if (draft_list == None):
        return "FAILED: The draft work list is empty!"

    for item in draft_list:
        item['label'] = draft_sunday

    list_data = {
        'sumup': draft_list,
        'issue': [],
        'plan': [],
        'removeSumup': '',
        'removeIssue': '',
        'removePlan': '',
    }
    res = update_list(list_data)
    return res

def test_save_list():
    print('>> Test update task list ...')
    task_list = load_list(TASK_LIST)
    print(task_list)
    save_report = urlencode(task_list)
    res = s.post(URL_SAVE, headers=POST_HEADERS, cookies=cookie, data=save_report)
    print(res)

def test_gen_draft():
    res = gen_draft('', '', '')

def test_submit_draft():
    res = submit_draft()
    print(res)

def get_args():
    parser = ArgumentParser()
    parser.add_argument('-u', help='Username')
    parser.add_argument('-p', help='Password')
    parser.add_argument('-d', help='Date')
    parser.add_argument('-f', help='Work list file')

    return parser.parse_args()

def main():
    args = get_args()
    print(args)
    # Login
    ret = login(args.u, args.p)
    if (ret != 0): 
        print('Login failed! Error code: ' + ret)
        return 1

    if (args.d != None):
        date = args.d
    else:
        date = time.strftime('%Y-%m-%d', time.localtime())
 
    # Get this week work list
    this_list = get_list(this_sunday(date))
    if (this_list != None):
        print('This week work list already submitted!')
        dump_list(this_list)
        return 0

    # Get last week work list
    last_list = get_list(last_sunday(date))
    if (last_list == None):
        print('Get last work list failed!')
        return 2
    else:
        print('Get last work list successfully!')

    # Draft work list for this week
    my_list = prepare_list(last_list, this_sunday(date))
    res = update_list(my_list)

    return 0

if __name__ == "__main__":
    #main()
    test_gen_draft()
    test_submit_draft()
