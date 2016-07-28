from flask import Blueprint, render_template, abort, request, redirect, session, url_for, send_file
from flask.ext.login import current_user, login_user, logout_user
from sqlalchemy import desc, or_, and_, desc
from packages.objects import *
from packages.common import *
from packages.config import _cfg
from packages.email import send_confirmation, send_reset
from packages.blueprints.api import upload_package
from packages.kpack import PackageInfo
from datetime import datetime, timedelta

import binascii
import os
import zipfile
import urllib
import re
import json
import locale
import shlex
import math

encoding = locale.getdefaultlocale()[1]
html = Blueprint('html', __name__, template_folder='../../templates')

@html.route("/")
def index():
    recent = Package.query.filter(Package.approved == True).order_by(desc(Package.updated)).limit(10).all()
    recent_users = User.query.filter(User.confirmation == None).order_by(desc(User.created)).limit(10).all()
    queue = Package.query.filter(Package.approved == False).order_by(desc(Package.updated)).all()
    total = Package.query.filter(Package.approved == True).count()
    return render_template("index.html", recent=recent, recent_users=recent_users, queue=queue, total=total)

@html.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template("register.html")
    else:
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        errors = dict()
        if not email:
            errors['email'] = 'Email is required.'
        else:
            if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
                errors['email'] = 'Please use a valid email address.'
            if User.query.filter(User.username.ilike(username)).first():
                errors['username'] = 'This username is already in use.'
        if not username:
            errors['username'] = 'Username is required.'
        else:
            if not re.match(r"^[A-Za-z0-9_]+$", username):
                errors['username'] = 'Letters, numbers, underscores only.'
            if len(username) < 3 or len(username) > 24:
                errors['username'] = 'Must be between 3 and 24 characters.'
            if User.query.filter(User.username.ilike(username)).first():
                errors['username'] = 'This username is already in use.'
        if not password:
            errors['password'] = 'Password is required.'
        else:
            if len(password) < 5 or len(password) > 256:
                errors['password'] = 'Must be between 5 and 256 characters.'
        if errors != dict():
            return render_template("register.html", username=username, email=email, errors=errors)
        # All good, create an account for them
        user = User(username, email, password)
        user.confirmation = binascii.b2a_hex(os.urandom(20)).decode("utf-8")
        db.add(user)
        db.commit()
        send_confirmation(user)
        return redirect("/pending")

@html.route("/confirm/<confirmation>")
def confirm(confirmation):
    user = User.query.filter(User.confirmation == confirmation).first()
    if not user:
        return render_template("confirm.html", **{ 'success': False, 'user': user })
    else:
        user.confirmation = None
        login_user(user)
        db.commit()
        return render_template("confirm.html", **{ 'success': True, 'user': user })

@html.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if current_user:
            return redirect("/")
        reset = request.args.get('reset') == '1'
        return render_template("login.html", **{ 'return_to': request.args.get('return_to'), 'reset': reset })
    else:
        username = request.form['username']
        password = request.form['password']
        remember = request.form.get('remember-me')
        if remember == "on":
            remember = True
        else:
            remember = False
        user = User.query.filter(User.username.ilike(username)).first()
        if not user:
            return render_template("login.html", **{ "username": username, "errors": 'Your username or password is incorrect.' })
        if user.confirmation != '' and user.confirmation != None:
            return redirect("/pending")
        if not bcrypt.checkpw(password, user.password):
            return render_template("login.html", **{ "username": username, "errors": 'Your username or password is incorrect.' })
        login_user(user, remember=remember)
        if 'return_to' in request.form and request.form['return_to']:
            return redirect(urllib.parse.unquote(request.form.get('return_to')))
        return redirect("/")

@html.route("/logout")
@loginrequired
def logout():
    logout_user()
    return redirect("/")

@html.route("/forgot-password", methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'GET':
        return render_template("forgot.html")
    else:
        email = request.form.get('email')
        if not email:
            return render_template("forgot.html", bad_email=True)
        user = User.query.filter(User.email == email).first()
        if not user:
            return render_template("forgot.html", bad_email=True, email=email)
        user.passwordReset = binascii.b2a_hex(os.urandom(20)).decode("utf-8")
        user.passwordResetExpiry = datetime.now() + timedelta(days=1)
        db.commit()
        send_reset(user)
        return render_template("forgot.html", success=True)

@html.route("/reset", methods=['GET', 'POST'])
@html.route("/reset/<username>/<confirmation>", methods=['GET', 'POST'])
def reset_password(username, confirmation):
    user = User.query.filter(User.username == username).first()
    if not user:
        redirect("/")
    if request.method == 'GET':
        if user.passwordResetExpiry == None or user.passwordResetExpiry < datetime.now():
            return render_template("reset.html", expired=True)
        if user.passwordReset != confirmation:
            redirect("/")
        return render_template("reset.html", username=username, confirmation=confirmation)
    else:
        if user.passwordResetExpiry == None or user.passwordResetExpiry < datetime.now():
            abort(401)
        if user.passwordReset != confirmation:
            abort(401)
        password = request.form.get('password')
        password2 = request.form.get('password2')
        if not password or not password2:
            return render_template("reset.html", username=username, confirmation=confirmation, errors="Please fill out both fields.")
        if password != password2:
            return render_template("reset.html", username=username, confirmation=confirmation, errors="You seem to have mistyped one of these, please try again.")
        user.set_password(password)
        user.passwordReset = None
        user.passwordResetExpiry = None
        db.commit()
        return redirect("/login?reset=1")

@html.route("/pending")
def pending():
    return render_template("pending.html")

@html.route("/upload", methods=['GET', 'POST'])
@loginrequired
def upload():
    if request.method == 'GET':
        return render_template("upload.html")
    else:
        result = upload_package()[0]
        j = json.loads(result.data.decode(encoding))
        if not j['success']:
            return render_template("upload.html", error=j['error'])
        else:
            return redirect(j['url'])

@html.route("/<repo>/<name>")
def package(repo, name):
    p = Package.query.filter(Package.name == name).filter(Package.repo == repo).first()
    if not p:
        abort(404)
    if p.contents == None:
        packagePath = os.path.join(_cfg("storage"), p.repo, "{0}-{1}.pkg".format(p.name, p.version))
        packageDict = PackageInfo.get_package_contents(packagePath)
        p.contents = json.dumps(packageDict)
        db.commit()
    packageContents = json.loads(p.contents)
    if p.downloads == None:
        p.downloads = 0
    return render_template("package.html", package=p, packageContents = packageContents)


@html.route("/users")
def users():
    
    if not current_user or not current_user.admin:
        abort(403)

    terms = request.args.get('terms')
    if not terms:
        terms = ''

    try:
        page = request.args.get('page')
        if not page:
            page = '0'
        page = int(page)
    except:
        abort(400)
    split_terms = shlex.split(terms)
    results = User.query
    filters = list()

    try:
        PAGE_SIZE = request.args.get('count')
        if not PAGE_SIZE:
            PAGE_SIZE = '10'
        PAGE_SIZE = int(PAGE_SIZE)
    except:
        PAGE_SIZE = 10

    if PAGE_SIZE <= 0: PAGE_SIZE = 10

    for term in split_terms:
        filters.append(User.username.ilike('%' + term + '%'))
        filters.append(User.email.ilike('%' + term + '%'))
    results = results.filter(or_(*filters))
    results = results.filter()
    total = math.ceil(results.count() / PAGE_SIZE)
    pageCount = total

    pageResults = results.order_by(desc(User.created)).all()[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    if len(pageResults) == 0:
        page = 0
        pageResults = results.order_by(desc(User.created)).all()[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    results = pageResults
    return render_template("users.html", results=results, terms=terms, pageCount=pageCount, page=page)

@html.route("/user/<username>")
def user(username):
    user_profile = User.query.filter(User.username == username).first()
    if not user_profile:
        abort(404)
    user_packages = Package.query.filter(Package.user == user_profile).all()
    return render_template("user.html", user_profile=user_profile, user_packages=user_packages)


@html.route("/<repo>")
@html.route("/<repo>/")
def repo(repo):

    try:
        page = request.args.get('page')
        if not page:
            page = '0'
        page = int(page)
    except:
        abort(400)

    try:
        PAGE_SIZE = request.args.get('count')
        if not PAGE_SIZE:
            PAGE_SIZE = '10'
        PAGE_SIZE = int(PAGE_SIZE)
    except:
        PAGE_SIZE = 10

    if PAGE_SIZE <= 0: PAGE_SIZE = 10

    results = Package.query.filter(Package.repo == repo and Package.approved == True)

    total = math.ceil(results.count() / PAGE_SIZE)
    pageCount = total

    pageResults = results.order_by(desc(Package.updated)).all()[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    if len(pageResults) == 0:
        page = 0
        pageResults = results.order_by(desc(Package.updated)).all()[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    results = pageResults

    if len(results) == 0:
        abort(404)

    return render_template("repo.html", results=results, pageCount=pageCount, page=page, repo=repo)

@html.route("/search")
def search():
    repos = request.args.getlist("repos")
    terms = request.args.get('terms')
    if not terms:
        terms = ''
    try:
        page = request.args.get('page')
        if not page:
            page = '0'
        page = int(page)
    except:
        abort(400)
    split_terms = shlex.split(terms)
    results = Package.query
    filters = list()

    try:
        PAGE_SIZE = request.args.get('count')
        if not PAGE_SIZE:
            PAGE_SIZE = '10'
        PAGE_SIZE = int(PAGE_SIZE)
    except:
        PAGE_SIZE = 10

    if PAGE_SIZE <= 0: PAGE_SIZE = 10

    repoFilters = list()
    if "core" in repos:
        repoFilters.append(Package.repo == "core")
    if "extra" in repos:
        repoFilters.append(Package.repo == "extra")
    if "community" in repos:
        repoFilters.append(Package.repo == "community")
    if "ports" in repos:
        repoFilters.append(Package.repo == "ports")
    if "nonfree" in repos:
        repoFilters.append(Package.repo == "nonfree")
    results = results.filter(or_(*repoFilters))

    for term in split_terms:
        filters.append(Package.repo.ilike('%' + term + '%'))
        filters.append(Package.name.ilike('%' + term + '%'))
        filters.append(Package.description.ilike('%' + term + '%'))
    results = results.filter(or_(*filters))
    results = results.filter(Package.approved == True)
    total = math.ceil(results.count() / PAGE_SIZE)
    pageCount = total

    pageResults = results.order_by(desc(Package.updated)).all()[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    if len(pageResults) == 0:
        page = 0
        pageResults = results.order_by(desc(Package.updated)).all()[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    results = pageResults
    return render_template("search.html", results=results, terms=terms, pageCount=pageCount, page=page)

@html.route("/<repo>/<name>/download")
def download(repo, name):
    p = Package.query.filter(Package.name == name and Package.repo == repo).first()
    if not p:
        abort(404)
    if p.downloads == None:
        p.downloads = 0
    p.downloads += 1
    db.commit()
    return send_file(os.path.join(_cfg("storage"), p.repo, "{0}-{1}.pkg".format(p.name, p.version)), as_attachment=True)

@html.route("/guidelines")
def guidelines():
    return render_template("guidelines.html")

@html.route("/help")
def help():
    return render_template("help.html")
