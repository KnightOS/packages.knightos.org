from flask import session, jsonify, redirect, request, Response, abort
from flask.ext.login import current_user
from werkzeug.utils import secure_filename
from functools import wraps
from packages.objects import User
from packages.database import db, Base

import json
import urllib
import requests
import xml.etree.ElementTree as ET

def with_session(f):
    @wraps(f)
    def go(*args, **kw):
        try:
            ret = f(*args, **kw)
            db.commit()
            return ret
        except:
            db.rollback()
            db.close()
            raise
    return go

def loginrequired(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user or current_user.confirmation:
            return redirect("/login?return_to=" + urllib.parse.quote_plus(request.url))
        else:
            return f(*args, **kwargs)
    return wrapper

def adminrequired(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user or current_user.confirmation:
            return redirect("/login?return_to=" + urllib.parse.quote_plus(request.url))
        else:
            if not current_user.admin:
                abort(401)
            return f(*args, **kwargs)
    return wrapper

def json_output(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        def jsonify_wrap(obj):
            jsonification = json.dumps(obj)
            return Response(jsonification, mimetype='application/json')

        result = f(*args, **kwargs)
        if isinstance(result, tuple):
            return jsonify_wrap(result[0]), result[1]
        if isinstance(result, dict):
            return jsonify_wrap(result)
        if isinstance(result, list):
            return jsonify_wrap(result)

        # This is a fully fleshed out response, return it immediately
        return result

    return wrapper

def cors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        res = f(*args, **kwargs)
        if request.headers.get('x-cors-status', False):
            if isinstance(res, tuple):
                json_text = res[0].data
                code = res[1]
            else:
                json_text = res.data
                code = 200

            o = json.loads(json_text)
            o['x-status'] = code

            return jsonify(o)

        return res

    return wrapper


