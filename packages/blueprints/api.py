from flask import Blueprint, render_template, abort, request, redirect, session, url_for
from flask.ext.login import current_user, login_user
from sqlalchemy import desc
from packages.objects import *
from packages.common import *
from packages.config import _cfg

import os
import zipfile
import urllib

api = Blueprint('api', __name__)

@api.route("/test")
@json_output
def test():
    return { 'value': 'Hello world!' }
