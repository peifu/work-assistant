#!/usr/bin/env python3
#coding: utf-8

#import pysnooper
import time
import time
from datetime import datetime, timedelta
import re
import os
import sys
import json
import prettytable as pt
import pandas as pd
import numpy as np
from io import StringIO
from jira import JIRA

DEBUG_LOG_ENABLE = 0
DEBUG_DUMP_ENABLE = 0

MAX_ISSUE = 200
MAX_SUMMARY = 80
JIRA_SERVER = "cfg/server.json"
TEST_JIRA_FILTER = "cfg/jira_filter.json"
TEST_JIRA_PATTERN = "cfg/jira_pattern_test.json"
JIRA_SERVER_ADDR = "https://jira.amlogic.com"
JIRA_FILTER_CONFIG = "cfg/jira_filter.json"
JIRA_FILTER_CONFIG2 = "apps/models/cfg/jira_filter.json"
MY_SERVER_CONFIG = "cfg/server-%s.json"
MY_SERVER_CONFIG2 = "apps/models/cfg/server-%s.json"

USER_LOG_FILE = 'apps/models/cfg/server.log'
USER_LOG_FILE2 = './server.log'

JIRA_LABEL_DATE = 'JIRALABELDATE'
JIRA_ASSIGNEE = 'JIRAASSIGNEE'
JIRA_LINK = '<a href="https://jira.amlogic.com/browse/%s">%s</a>'
JIRA_KEY_PATTERN = '(SWPL|RSP|OTT|SH|IPTV|OPS|TV|GH|KAR|VLSI|WIRELESS|SBTP|RK)-[1-9][0-9]*'
DATE_KEY_PATTERN = '[1-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
DATE_HIGHLIGHT_RED = '<font color="red">%s</font>'
DATE_HIGHLIGHT_BLUE = '<font color="blue">%s</font>'
DATE_HIGHLIGHT_GREEN = '<font color="green">%s</font>'
DATE_HIGHLIGHT_ORANGE = '<font color="orange">%s</font>'

JIRA_PATTERN = "project in ({}) AND priority in ({}) AND status in ({}) AND assignee in ({}) ORDER BY priority DESC, status ASC, assignee ASC"
FIELD_NAMES = ["Issue", "Issuetype", "Priority", "Status", "Assingee", "Creator", "Summary"]
FIELD_NAMES2 = ["Issue", "Priority", "Status", "Assignee", "Leader", "Due Date", "Finish Date", "Summary"]

def debug(args):
    if (DEBUG_LOG_ENABLE == 1):
        print(args, file=sys.stderr)

def info(args):
    print(args, file=sys.stderr)

def error(args):
    print(args, file=sys.stderr)

def log_write(msg):
    date = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime())
    try:
        log_file = open(USER_LOG_FILE, 'a+')
    except:
        log_file = open(USER_LOG_FILE2, 'a+')
    if (log_file):
        log_file.write(date + ' ' + msg + '\n')
        log_file.flush()
        log_file.close()

def this_monday():
    today = time.strftime('%Y-%m-%d', time.localtime())
    today = datetime.strptime(str(today), '%Y-%m-%d')
    return datetime.strftime(today + timedelta(- today.weekday()), '%Y%m%d')

def store_csv(filename, csv_str):
    csv_file = open(filename, "w+")
    csv_file.write(csv_str)
    csv_file.close()

def delete_file(filename):
    if os.path.exists(filename):
        os.remove(filename)
    else:
        print("The file does not exist")

def store_file(filename, file_str):
    csv_file = open(filename, "w+")
    csv_file.write(file_str)
    csv_file.close()

def init_server_config(user):
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

def init_filter_config():
    cfg = JIRA_FILTER_CONFIG
    try:
        f = open(cfg, encoding="utf-8")
        filter_config = json.load(f)
    except:
        cfg = JIRA_FILTER_CONFIG2
        f = open(cfg, encoding="utf-8")
        filter_config = json.load(f)
    return filter_config

def init_config_with_json(cfg_json):
    jira_config = json.loads(cfg_json)
    debug(jira_config)
    return jira_config

def key2link(matched):
    key = matched.group()
    link = JIRA_LINK % (key, key)
    return link

def add_link(table):
    table2 = re.sub(JIRA_KEY_PATTERN, key2link, table)
    return table2

def date_highlight(matched):
    key = matched.group()
    d1 = datetime.today()
    d2 = datetime.strptime(key, '%Y-%m-%d')
    dd = (d2 - d1).days
    if dd <= 1:
        key_hl = DATE_HIGHLIGHT_RED % (key)
    elif dd <= 3:
        key_hl = DATE_HIGHLIGHT_ORANGE % (key)
    else:
        key_hl = key
    return key_hl

def add_highlight(table):
    table2 = re.sub(DATE_KEY_PATTERN, date_highlight, table)
    return table2

def format_table(table):
    table2 = add_link(table)
    table2 = add_highlight(table2)
    return table2

def init_jira(jira_config):
    server = JIRA_SERVER_ADDR
    user = jira_config["server"]["user"]
    pwd = jira_config["server"]["password"]
    #debug("server={}, user={}, pwd={}".format(server, user, pwd))
    try:
        jira = JIRA({"server": server}, basic_auth=(user, pwd))
        print("Login success!")
    except Exception as e:
        print("Login failed!")
    return jira

def get_filters(cfg):
    try:
        f = open(cfg, encoding="utf-8")
    except:
        print("Open failed! " + cfg)
    filter_json = json.load(f)
    f.close()
    return filter_json["filter"]

def get_patterns(cfg):
    try:
        f = open(cfg, encoding="utf-8")
    except:
        print("Open failed! " + cfg)
        return ""
    pattern_json = json.load(f)
    f.close()
    return pattern_json["pattern"]

def get_dataframe_from_csv(csv_str):
    df = pd.DataFrame(pd.read_csv(StringIO(csv_str)))
    print(df)

def init_table():
    tb = pt.PrettyTable()
    tb.field_names = FIELD_NAMES2
    tb.align = 'l'
    return tb

def get_leader(issue):
    if (issue.fields.customfield_11903):
        return issue.fields.customfield_11903.key
    else:
        return "None"

def get_finish_date(issue):
    return issue.fields.customfield_11614

def update_table(tb, issue):
    item = [issue.key, issue.fields.issuetype.name, issue.fields.priority.name,
        issue.fields.status.name, issue.fields.assignee.key, issue.fields.creator.key,
        issue.fields.summary[0:MAX_SUMMARY]]
    item2 = [issue.key, issue.fields.priority.name,
        issue.fields.status.name, issue.fields.assignee.name.lower(),
        get_leader(issue),
        issue.fields.duedate, get_finish_date(issue),
        issue.fields.summary[0:MAX_SUMMARY]]
    tb.add_row(item2)

def dump_table(tb):
    if (DEBUG_DUMP_ENABLE == 0):
        return

    s = tb.get_string()
    print(s)

def dump_issue(issue):
    if (DEBUG_DUMP_ENABLE == 0):
        return

    print(dir(issue.fields))
    print('{}:{}'.format(issue.key, issue.fields.summary))
    item = [issue.key, issue.fields.issuetype, issue.fields.priority, issue.fields.status,
         issue.fields.assignee, issue.fields.creator, issue.fields.summary]
    print(item)
    item3 = issue.fields.customfield_11903
    print(item3)

def query_issues(jira, pattern, count):
    issues = jira.search_issues(pattern, maxResults=count)
    return issues

def get_issues_by_pattern(jira, pattern):
    tb = init_table()
    debug(pattern)
    issues = query_issues(jira, pattern, MAX_ISSUE)
    debug(issues)
    try:
        for issue in issues:
            update_table(tb, issue)
            # debug issue
            dump_issue(issue)
    except:
        print("update table failed!")
    dump_table(tb)
    return tb

#@pysnooper.snoop()
def add_label_by_pattern(jira, pattern, label):
    tb = init_table()
    debug(pattern)
    issues = query_issues(jira, pattern, MAX_ISSUE)
    debug(issues)
    try:
        for issue in issues:
            update_table(tb, issue)
            print(issue)
            print(issue.fields.labels)
            issue.fields.labels.append(label)
            issue.update(fields={"labels": issue.fields.labels})
            # debug issue
            dump_issue(issue)
    except:
        print("update table failed!")
    dump_table(tb)
    return tb

def get_issues_by_filter(jira, filter):
    tb = init_table()
    pattern = JIRA_PATTERN.format(filter["project"], filter["priority"], filter["status"], filter["assignee"])
    debug(pattern)
    issues = query_issues(jira, pattern, MAX_ISSUE)
    try:
        for issue in issues:
            update_table(tb, issue)
            # debug issue
            dump_issue(issue)
    except:
        print("update table failed!")
    return tb

def get_jira_csv(filter):
    jira_config = init_config(JIRA_SERVER)
    jira = init_jira(jira_config)
    tb = get_issues_by_filter(jira, filter)
    csv = tb.get_csv_string()
    return csv

def get_jira_html(filter):
    jira_config = init_config(JIRA_SERVER)
    jira = init_jira(jira_config)
    tb = get_issues_by_filter(jira, filter)
    csv = tb.get_csv_string()
    df = pd.DataFrame(pd.read_csv(StringIO(csv)))
    html = df.to_html(index=False)
    return html

#@pysnooper.snoop()
def get_jira_table_by_pattern(pattern):
    jira_config = init_config(JIRA_SERVER)
    jira = init_jira(jira_config)
    try:
        tb = get_issues_by_pattern(jira, pattern)
        return tb
    except:
        print("get table failed!")
    return None

def get_jira_table(filter):
    jira_config = init_config(JIRA_SERVER)
    jira = init_jira(jira_config)
    tb = get_issues_by_filter(jira, filter)
    s = tb.get_string()
    return s

def get_html_from_table(tb):
    csv = tb.get_csv_string()
    df = pd.DataFrame(pd.read_csv(StringIO(csv)))
    html = df.to_html(index=False)
    return html

def add_jira_label_by_pattern(pattern, label):
    jira_config = init_config(JIRA_SERVER)
    jira = init_jira(jira_config)
    try:
        tb = add_label_by_pattern(jira, pattern, label)
        return tb
    except:
        print("get table failed!")
    return None

def jira_login(username, password):
    server = JIRA_SERVER_ADDR
    user = username
    pwd = password
    #info("server={}, user={}, pwd={}".format(server, user, pwd))
    try:
        jira = JIRA({"server": server}, basic_auth=(user, pwd))
        if (jira):
            info("Login success!")
            return 0
        else:
            error("Login success!")
            return 1
    except Exception as e:
        error("Login failed!")
        return 2

def jira_get_table_by_pattern(user, pattern):
    jira_config = init_server_config(user)
    jira = init_jira(jira_config)
    try:
        tb = get_issues_by_pattern(jira, pattern)
        return tb
    except:
        print("get table failed!")
    return None

def jira_get_table_by_date(user, pattern, date):
    info('jira_get_table_by_date(' + user + ', ' + pattern + ', ' + date + ')')
    log_write('[' + user + '] jira_get: ' + pattern + date)
    server_config = init_server_config(user)
    user = server_config["server"]["user"]
    filter_config = init_filter_config()

    for my_filter in filter_config['filter']:
        if my_filter['name'] == pattern:
            jira_pattern = my_filter['pattern']
            break

    if 'my-weekly' in pattern:
        jira_pattern = re.sub(JIRA_ASSIGNEE, user, jira_pattern)
        jira_pattern = re.sub(JIRA_LABEL_DATE, date, jira_pattern)

    info(jira_pattern)
    tb = jira_get_table_by_pattern(user, jira_pattern)
    return tb

def jira_get_tb(user, pattern):
    print(user, file=sys.stderr)
    print(pattern, file=sys.stderr)
    log_write('[' + user + '] jira_get: ' + pattern)
    server_config = init_server_config(user)
    user = server_config["server"]["user"]
    filter_config = init_filter_config()

    for my_filter in filter_config['filter']:
        if my_filter['name'] == pattern:
            jira_pattern = my_filter['pattern']
            break

    if 'my-weekly' in pattern:
        jira_pattern = re.sub(JIRA_ASSIGNEE, user, jira_pattern)
        jira_pattern = re.sub(JIRA_LABEL_DATE, this_monday(), jira_pattern)
    elif 'my-' in pattern:
        jira_pattern = re.sub(JIRA_ASSIGNEE, user, jira_pattern)
    elif 'weekly' in pattern:
        jira_pattern = re.sub(JIRA_LABEL_DATE, this_monday(), jira_pattern)

    tb = jira_get_table_by_pattern(user, jira_pattern)
    return tb

def jira_get(user, pattern):
    tb = jira_get_tb(user, pattern)
    if (tb):
        html = get_html_from_table(tb)
        html2 = format_table(html)
    else:
        html2 = "None"
    return html2

def test_jira_get(user, pattern):
    html = jira_get(user, pattern)
    print(html)

def test_jira_html():
    filters = get_filters(TEST_JIRA_FILTER)
    for filter in filters[0:1]:
        s = get_jira_html(filter)
        print(filter["name"])
        print(s)

def test_jira_table():
    filters = get_filters(TEST_JIRA_FILTER)
    for filter in filters[0:1]:
        s = get_jira_table(filter)
        print(filter["name"])
        print(s)

def test_jira_pattern():
    html = ""
    patterns = get_patterns(TEST_JIRA_PATTERN)
    for pattern in patterns:
        tb = get_jira_table_by_pattern(pattern["pattern"])
        print(tb)
        html = get_html_from_table(tb)
        #print(pattern["name"])
        #print(html)
    return html

if __name__ == "__main__":
    #test_jira_html()
    #test_jira_table()
    #test_jira_pattern()
    #test_jira_get('peifu.jiang', 'my-open')
    #test_jira_get('peifu.jiang', 'my-todo')
    #test_jira_get('peifu.jiang', 'my-ongoing')
    #test_jira_get('peifu.jiang', 'my-resolved')
    #test_jira_get('peifu.jiang', 'my-closed')
    #test_jira_get('peifu.jiang', 'security-open')
    #test_jira_get('peifu.jiang', 'security-todo')
    #test_jira_get('peifu.jiang', 'security-ongoing') 
    #test_jira_get('peifu.jiang', 'security-resolved')
    test_jira_get('peifu.jiang', 'my-weekly')
