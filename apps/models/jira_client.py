#!/usr/bin/env python3
#coding: utf-8

#import pysnooper
import re
import json
import prettytable as pt
import pandas as pd
import numpy as np
from io import StringIO
from jira import JIRA

DEBUG_LOG_ENABLE = 1
DEBUG_DUMP_ENABLE = 1

MAX_ISSUE = 200
MAX_SUMMARY = 80
JIRA_SERVER = "apps/models/cfg/jira_server.json"
TEST_JIRA_FILTER = "apps/models/cfg/jira_filter.json"
TEST_JIRA_PATTERN = "apps/models/cfg/jira_pattern_test.json"

JIRA_PATTERN = "project in ({}) AND priority in ({}) AND status in ({}) AND assignee in ({}) ORDER BY priority DESC, status ASC, assignee ASC"
FIELD_NAMES = ["Issue", "Issuetype", "Priority", "Status", "Assingee", "Creator", "Summary"]
FIELD_NAMES2 = ["Issue", "Priority", "Status", "Assignee", "Leader", "Due Date", "Finish Date", "Summary"]

def debug(args):
    if (DEBUG_LOG_ENABLE == 1):
        print(args)

def store_csv(filename, csv_str):
    csv_file = open(filename, "w+")
    csv_file.write(csv_str)
    csv_file.close()

def init_config(cfg):
    f = open(cfg, encoding="utf-8")
    jira_config = json.load(f)
    f.close()
    debug(jira_config)
    return jira_config

def init_config_with_json(cfg_json):
    jira_config = json.loads(cfg_json)
    debug(jira_config)
    return jira_config

def init_jira(jira_config):
    server = jira_config["server"]["server_addr"]
    user = jira_config["server"]["user"]
    pwd = jira_config["server"]["password"]
    debug("server={}, user={}, pwd={}".format(server, user, pwd))
    jira = JIRA({"server": server}, basic_auth=(user, pwd))
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
    patterns = get_patterns(TEST_JIRA_PATTERN)
    for pattern in patterns:
        tb = get_jira_table_by_pattern(pattern["pattern"])
        html = get_html_from_table(tb)
        print(pattern["name"])
    print(html)
    return html

if __name__ == "__main__":
    #test_jira_html()
    #test_jira_table()
    test_jira_pattern()