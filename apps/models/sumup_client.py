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

POST_HEADERS = {
    "Accpet": "*/*",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Connection": "keep-alive",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74 Safari/537.36",
}

TASK_LIST='./save_report.json'
s = Session()
cookie = ''
draft_list = []

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
    print(res)
    cookie = requests.utils.dict_from_cookiejar(s.cookies)
    print(cookie)
    res = s.get(URL_MAIN)
    if (res.status_code == 200):
        return 0
    else:
        return res.status_code

def get_list(date):
    print('date: ' + date)
    data = {
        'id': 604,
        'departmentid': 141,
        'date': date,
        'workType': -1,
        'fetchAll': 100,
    }
    res = s.post(URL_LIST, headers=POST_HEADERS, data=data)
    print(res)
    if (res.status_code == 200):
        task = json.dumps(json.loads(res.text), indent=4, separators=(',', ':'))
    else:
        task = ''
    json_task = json.loads(task)
    if (len(json_task['sumup']['data']) > 0):
        return json_task['sumup']['data']
    else:
        return None

def prepare_list(task):
    draft_list.clear()
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
        draft_list.append(sumup_item)

    return draft_list

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
    # Login
    server_config = init_config(SERVER_CONFIG)
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

    server_config = init_config(SERVER_CONFIG)
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
    else:
        print('Get last week work list successfully!')
    
    draft_list = prepare_list(last_list)
    dump_list(draft_list)
    return list_to_html(draft_list)

def submit_draft(user, date):
    print('>> submit_draft() ...')
    draft_sunday = this_sunday(date)

    # Get this week work list
    this_list = get_list(draft_sunday)
    if (this_list != None):
        return "The work list of this week is already submitted!"

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
