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
import apps.models.sumup_client

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
    html = apps.models.jira_client.test_jira_pattern()
    return html

@blueprint.route('/sum-up-1', methods=["GET"])
@login_required
def sumup_gen():
    cur_date = time.strftime("%Y-%m-%d", time.localtime()) 
    html = apps.models.sumup_client.gen_draft('', '', cur_date)
    return html

@blueprint.route('/sum-up-2', methods=["GET"])
@login_required
def sumup_submit():
    cur_date = time.strftime("%Y-%m-%d", time.localtime()) 
    html = apps.models.sumup_client.submit_draft(cur_date)
    return html

@blueprint.route('/sum-up-3', methods=["GET"])
@login_required
def sumup_get():
    cur_date = time.strftime("%Y-%m-%d", time.localtime()) 
    html = apps.models.sumup_client.get_sumup_list('', '', cur_date)
    return html