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

USER_LOG_FILE = 'apps/models/cfg/server.log'

DOMAIN='@amlogic.com'
SERVER_CONFIG = "apps/models/cfg/server.json"
MY_SERVER_CONFIG = "apps/models/cfg/server-%s.json"
MY_SERVER_CONFIG2 = "cfg/server-%s.json"
USERID_PATTERN = '/weekly_sumup/table/member/[1-9][0-9]*/%s'
DEPARTMENTID_PATTERN = "'departmentid': \"[1-9][0-9]*"

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

def log_write(msg):
    date = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime())
    log_file = open(USER_LOG_FILE, 'a+')
    if (log_file):
        log_file.write(date + ' ' + msg + '\n')
        log_file.flush()
        log_file.close()

def this_sunday(today):
    today = datetime.strptime(str(today), '%Y-%m-%d')
    return datetime.strftime(today + timedelta(7 - today.weekday() - 1), '%Y-%m-%d')

def last_sunday(today):
    today = datetime.strptime(str(today), '%Y-%m-%d')
    return datetime.strftime(today + timedelta(- today.weekday() - 1), '%Y-%m-%d')

def this_monday(today):
    today = datetime.strptime(str(today), '%Y-%m-%d')
    return datetime.strftime(today + timedelta(- today.weekday()), '%Y-%m-%d')

def load_list(task_file):
    f = open(task_file, encoding="utf-8")
    task_list = json.load(f)
    f.close()
    return task_list

def format_table(table):
    table = table.replace('<table border="1" class="dataframe">', '<table class="table table-sm table-bordered table-hover">')
    table = table.replace('style="text-align: right;"', '')
    table = table.replace('<thead>', '<thead class="thead-light" style="text-transform:uppercase;">')
    table = table.replace('SUBMITTED-YES', '<i class="fa fa-check-square" style="font-size:20px;color:green;"></i>')
    table = table.replace('SUBMITTED-NO', '<i class="fa fa-window-close" style="font-size:20px;color:red;"></i>')
    return table

def init_config(user):
    cfg = MY_SERVER_CONFIG % user
    try:
        f = open(cfg, encoding="utf-8")
        server_config = json.load(f)
    except:
        cfg = MY_SERVER_CONFIG2 % user
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
    debug('date: ' + date)
    data = {
        'id': userid,
        'departmentid': departmentid,
        'date': date,
        'workType': -1,
        'fetchAll': 100,
    }
    res = s.post(URL_LIST, headers=POST_HEADERS, data=data)
    debug(res)
    if (res.status_code == 200):
        try:
            task = json.dumps(json.loads(res.text), indent=4, separators=(',', ':'))
        except:
            task = ''
            return None
    else:
        task = ''
        return None
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
    print(task)
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
    server_config = init_config(user)
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
    res = list_to_html(draft_list)
    res = format_table(res)
    return res

def get_sumup_status(user, date):
    global draft_list
    # Login
    server_config = init_config(user)
    user = server_config["server"]["user"]
    password = server_config["server"]["password"]
    ret = login(user, password)
    if (ret != 0):
        print('Login failed! Error code: ' + ret)
        return 'Login failed! Error code: ' + ret

    if (date == None or date ==''):
        date = time.strftime('%Y-%m-%d', time.localtime())
        date0 = '2022-01-01'
        #date0 = time.strftime('%Y-01-01', time.localtime())

    sumup_columns = ['WEEK', 'WORKTIME', 'STATUS']
    sumup_status = []

    # Get weekly sumpup status in this year
    sumup_sunday = this_sunday(date)
    sumup_sunday0 = this_sunday(date0)
    while (sumup_sunday != sumup_sunday0):
        sumup_worktime = 0
        this_list = get_list(sumup_sunday)
        if (this_list == None):
            sumup_submit = 'SUBMITTED-NO'
            sumup_worktime = 0
        else:
            sumup_submit = 'SUBMITTED-YES'
            for item in this_list:
                sumup_worktime += item['workTime']
        sumup_week = this_monday(sumup_sunday)  + ' ~ ' + sumup_sunday
        sumup_status.append([sumup_week, sumup_worktime, sumup_submit])
        sumup_sunday = last_sunday(sumup_sunday)

    df = pd.DataFrame(sumup_status, columns=sumup_columns)
    res = df.to_html(escape=False)
    res = format_table(res)
    print(res)
    return res

def gen_sumup_draft(user, date):
    print('>> gen_draft() ...')
    global draft_list

    server_config = init_config(user)
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
    res = list_to_html(draft_list)
    res = format_table(res)
    return res

def submit_sumup_draft(user, date):
    global draft_list
    print('>> submit_draft() ...')
    draft_sunday = this_sunday(date)

    # Get this week work list
    this_list = get_list(draft_sunday)
    if (this_list != None):
        return "The work list of this week has already been submitted!"

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

# API
def sumup_get(user, date, command):
    debug('>> sumup_get(data=%s, cmd=%s) ...' %(date , command))
    log_write('[' + user + '] sumup_get: ' + date + ' ' + command)
    if command == 'get_status':
        res = get_sumup_status(user, date)
    elif command == 'get_list':
        res = get_sumup_list(user, date)
    elif command == 'gen_draft':
        res = gen_sumup_draft(user, date)
    elif command == 'submit_draft':
        res = submit_sumup_draft(user, date)
    return res

# Test
def test_save_list():
    print('>> Test update task list ...')
    task_list = load_list(TASK_LIST)
    print(task_list)
    save_report = urlencode(task_list)
    res = s.post(URL_SAVE, headers=POST_HEADERS, cookies=cookie, data=save_report)
    print(res)

def test_gen_draft(user, date):
    res = gen_sumup_draft(user, date)

def test_get_sumup_status(user, date):
    res = get_sumup_status(user, date)

def test_submit_draft():
    res = submit_sumup_draft()
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
    #test_gen_draft('peifu.jiang', '')
    #test_submit_draft()
    test_get_sumup_status('peifu.jiang', '')
