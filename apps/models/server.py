#!/usr/bin/env python3
#coding: utf-8

import time
from datetime import datetime, timedelta
import re
import os
import sys
import json
from io import StringIO
from apps.models.jira_client import jira_login

DEBUG_LOG_ENABLE = 1

USER_LOG_FILE = 'apps/models/cfg/server.log'
#USER_LOG_FILE = 'server.log'
MY_SERVER_CONFIG = 'apps/models/cfg/server-%s.json'

global log_file
log_file = None

def debug(args):
    if (DEBUG_LOG_ENABLE == 1):
        print(args, file=sys.stderr)

def info(args):
    print(args, file=sys.stderr)

def error(args):
    print(args, file=sys.stderr)

def log_open():
    global log_file
    if (log_file == None):
        log_file = open(USER_LOG_FILE, 'a+')

def log_write(msg):
    global log_file
    date = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime())
    if (log_file == None):
        log_open()
    if (log_file):
        log_file.write(date + ' ' + msg + '\n')
        log_file.flush()

def log_close():
    global log_file
    if (log_file):
        log_file.close()
        log_file = None

def delete_file(filename):
    if os.path.exists(filename):
        os.remove(filename)
    else:
        debug('The file does not exist')

def server_login(username, password):
    ret = jira_login(username, password)
    if ret != 0:
        error(username + ' Login failed!')
        log_write(username + ' Login failed!')
        return ret

    server_config = {
        "server": {
            "user": username,
            "password": password
        }
    }
    my_server_config = MY_SERVER_CONFIG % username
    with open(my_server_config, 'w+') as f:
        json.dump(server_config, f)
        f.close()
    log_write(username + ' Login successfully!')
    return 0

def server_logout(username):
    log_close()
    user = username
    try:
        my_server_config = MY_SERVER_CONFIG % user
        delete_file(my_server_config)
        log_write(username + ' Logout successfully!')
        return 0
    except Exception as e:
        error(username + ' Logout failed!')
        log_write(username + ' Logout failed!')
        return 1

def test_log():
    log_open()
    log_write('test log')
    log_close()

if __name__ == "__main__":
    test_log()
