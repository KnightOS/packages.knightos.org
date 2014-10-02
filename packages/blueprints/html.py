from flask import Blueprint, render_template, abort, request, redirect, session, url_for
from flask.ext.login import current_user, login_user
from sqlalchemy import desc
from packages.objects import *
from packages.common import *
from packages.config import _cfg

import os
import zipfile
import urllib

html = Blueprint('html', __name__, template_folder='../../templates')

@html.route("/")
def index():
    return render_template("index.html")

@html.route("/help")
def help():
    return render_template("help.html")
