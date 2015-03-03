from flask import Blueprint, render_template, abort, request, redirect, session, url_for
from flask.ext.login import current_user, login_user
from sqlalchemy import desc
from shutil import move
from datetime import datetime
from packages.objects import *
from packages.common import *
from packages.config import _cfg
from packages.kpack import PackageInfo
from packages.email import send_new_pacakge_email

import os
import zipfile
import urllib
import tempfile

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

@api.route("/api/v1/<repo>/<name>")
@json_output
def get_info(repo, name):
    package = Package.query.filter(Package.name == name).filter(Package.repo == repo).first()
    if not package:
        return { 'success': False, 'error': 'Package not found.' }, 404
    json = {
        'name': package.name,
        'repo': package.repo,
        'full_name': '{0}/{1}'.format(package.repo, package.name),
        'version': package.version,
        'author': package.author,
        'maintainer': package.maintainer,
        'infourl': package.infourl,
        'copyright': package.copyright,
        'capabilities': package.capabilities,
        'dependencies': list(),
        'approved': package.approved
    }
    for d in package.dependencies:
        json['dependencies'].append('{0}/{1}'.format(d.repo, d.name))
    return json

@api.route("/api/v1/<repo>/<name>/approve", methods=["POST"])
@json_output
def approve_package(repo, name):
    package = Package.query.filter(Package.name == name).filter(Package.repo == repo).first()
    if not package:
        return { 'success': False, 'error': 'Package not found.' }, 404
    if not current_user or not current_user.admin:
        return { 'success': False, 'error': 'You do not have permission to approve this package.' }, 403
    package.approved = True
    db.commit()
    return { 'success': True }


@api.route("/api/v1/transfer/<repo>/<name>/<username>", methods=["POST"])
@json_output
def transfer_package(repo, name, username):
    package = Package.query.filter(Package.name == name).filter(Package.repo == repo).first()
    if not package:
        return { 'success': False, 'error': 'Package not found.' }, 404
    if not current_user or not current_user.admin:
        return { 'success': False, 'error': 'You do not have permission to move this package.' }, 403

    new_user = User.query.filter(User.username == username).first()
    if not new_user:
        return { 'success': False, 'error': 'User not found' }, 404
    package.user = new_user
    db.commit()

    return { 'success': True }


@api.route("/api/v1/upload", methods=['POST'])
@json_output
@loginrequired
def upload_package():
    package_file = request.files.get('package')
    if not package_file:
        return { 'success': False, 'error': 'You must include a package file.' }
    f, path = tempfile.mkstemp()
    package_file.save(path)
    info = None
    try:
        info = PackageInfo.read_package(path)
        if info.repo == None or info.name == None or info.version == None:
            return { 'success': False, 'error': 'This is not a valid KnightOS package.' }, 400
        if not info.repo in ['core', 'extra', 'community', 'ports']:
            return { 'success': False, 'error': '{0} is not an acceptable package repository.'.format(info.repo) }, 400
        if '/' in info.name:
            return { 'success': False, 'error': '{0} is not an acceptable package name.'.format(info.name) }, 400
    except:
        return { 'success': False, 'error': 'This is not a valid KnightOS package.' }, 400
    package = Package()
    existing = Package.query.filter(Package.name == info.name).first()
    if existing:
        if existing.repo != info.repo:
            return { 'success': False, 'error': 'This name conflicts with {0}/{1}.'.format(existing.repo, existing.name) }, 403
        if existing.user.username != current_user.username and not current_user.admin:
            return { 'success': False, 'error': 'You do not have permission to update {0}/{1}.'.format(existing.repo, existing.name) }, 403
        package = existing
        package.updated = datetime.now()
    else:
        package.user = current_user
        package.name = info.name
        package.repo = info.repo
    package.version = '{0}.{1}.{2}'.format(info.version[0], info.version[1], info.version[2])
    package.description = info.description
    package.author = info.author
    package.maintainer = info.maintainer
    package.infourl = info.infourl
    package.copyright = info.copyright
    package.capabilities = ' '.join(info.capabilities)
    package.dependencies = list()
    for dep in info.dependencies:
        try:
            repo = dep.split('/')[0]
            name = dep.split('/')[1]
            db_dep = Package.query.filter(Package.repo == repo).filter(Package.name == name).first()
            if not db_dep:
                raise Exception()
            package.dependencies.append(db_dep)
            print('appended ' + db_dep.name)
        except:
            return { 'success': False, 'error': '{0} is not a known dependency. Did you upload it first?'.format(dep) }, 400
    package.approved = False
    storage_dir = os.path.join(_cfg("storage"), package.repo)
    if not os.path.exists(storage_dir):
        os.makedirs(storage_dir)
    final_path = os.path.join(storage_dir, "{0}-{1}.pkg".format(package.name, package.version))
    move(path, final_path)
    if not existing:
        db.add(package)
        send_new_pacakge_email(package)
    db.commit()
    return { 'success': True, 'url': '/{0}/{1}'.format(package.repo, package.name) }, 200
