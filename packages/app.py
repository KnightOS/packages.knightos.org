from flask import Flask, render_template, request, g, Response, redirect, session, abort, send_file, url_for
from flask.ext.login import LoginManager, current_user
from jinja2 import FileSystemLoader, ChoiceLoader
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from shutil import rmtree, copyfile
from sqlalchemy import desc

import sys
import os
import subprocess
import urllib
import requests
import json
import zipfile
import locale
import traceback
import xml.etree.ElementTree as ET

from packages.config import _cfg, _cfgi
from packages.database import db, init_db
from packages.common import *
from packages.network import *

from packages.blueprints.api import api
from packages.blueprints.html import html

app = Flask(__name__)
app.secret_key = _cfg("secret-key")
app.jinja_env.cache = None
init_db()
login_manager = LoginManager()
login_manager.init_app(app)

#@login_manager.user_loader
#def load_user(username):
#    return User.query.filter(User.username == username).first()

login_manager.anonymous_user = lambda: None

app.register_blueprint(api)
app.register_blueprint(html)

locale.setlocale(locale.LC_ALL, 'en_US')

if not app.debug:
    @app.errorhandler(500)
    def handle_500(e):
        # shit
        try:
            db.rollback()
            db.close()
        except:
            # shit shit
            sys.exit(1)
        return render_template("internal_error.html"), 500
    # Error handler
    if _cfg("error-to") != "":
        import logging
        from logging.handlers import SMTPHandler
        mail_handler = SMTPHandler((_cfg("smtp-host"), _cfg("smtp-port")),
           _cfg("error-from"),
           [_cfg("error-to")],
           'packages.knightos.org application exception occured',
           credentials=(_cfg("smtp-user"), _cfg("smtp-password")))
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)

@app.errorhandler(404)
def handle_404(e):
    return render_template("not_found.html"), 404

@app.route('/version')
def version():
    return Response(subprocess.check_output(["git", "log", "-1"]), mimetype="text/plain")

@app.route('/hook', methods=['POST'])
def hook_publish():
    allow = False
    for ip in _cfg("hook_ips").split(","):
        parts = ip.split("/")
        range = 32
        if len(parts) != 1:
            range = int(parts[1])
        addr = networkMask(parts[0], range)
        if addressInNetwork(dottedQuadToNum(request.remote_addr), addr):
            allow = True
    if not allow:
        return "unauthorized", 403
    # Pull and restart site
    event = json.loads(request.data.decode("utf-8"))
    if not _cfg("hook_repository") == "%s/%s" % (event["repository"]["owner"]["name"], event["repository"]["name"]):
        return "ignored"
    if any("[noupdate]" in c["message"] for c in event["commits"]):
        return "ignored"
    if "refs/heads/" + _cfg("hook_branch") == event["ref"]:
        subprocess.call(["git", "pull", "origin", "master"])
        subprocess.Popen(_cfg("restart_command").split())
        return "thanks"
    return "ignored"

@app.context_processor
def inject():
    return {
        'root': _cfg("protocol") + "://" + _cfg("domain"),
        'domain': _cfg("domain"),
        'len': len,
        'any': any,
        'request': request,
        'locale': locale,
        'url_for': url_for
    }
