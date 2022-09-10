# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from apps.work import blueprint
from flask import render_template, request, jsonify
from flask_login import login_required
import json
import os
import time
import apps.models.jira_client

@blueprint.route('/task-list-1', methods=["GET"])
@login_required
def task_list():
    cur_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) 
    body = {}
    body["code"] = 0
    body["msg"] = cur_time
    body["count"] = 4
    body["data"] = ['aa', 'bb', 'cc', 'dd']
    return jsonify(body)

@blueprint.route('/jira-list-1', methods=["GET"])
@login_required
def jira_list():
    cur_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) 
    html = apps.models.jira_client.test_jira_pattern()
    return html