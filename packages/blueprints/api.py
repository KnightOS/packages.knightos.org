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

@api.route("/api/v1/login", methods=['POST'])
@json_output
def login():
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter(User.username.ilike(username)).first()
    if not user:
        return { 'success': False, 'error': 'Your username or password is incorrect.' }
    if user.confirmation != '' and user.confirmation != None:
        return { 'success': False, 'error': 'Your account is pending. Check your email or contact support@knightos.org' }
    if not bcrypt.checkpw(password, user.password):
        return { 'success': False, 'error': 'Your username or password is incorrect.' }
    login_user(user)
    return { 'success': True }
