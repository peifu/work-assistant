# -*- encoding: utf-8 -*-

from apps.work import blueprint
from flask import render_template, request, jsonify
from flask_login import login_required, current_user
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
def jira_get():
    pattern = request.args['pattern']
    html = apps.models.jira_client.jira_get(current_user.username, pattern)
    return html

@blueprint.route('/sumup-1', methods=["GET"])
@login_required
def sumup_get():
    date = request.args['date']
    command = request.args['command']
    html = apps.models.sumup_client.sumup_get(current_user.username, date, command)
    return html