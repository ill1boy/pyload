# -*- coding: utf-8 -*-

import traceback
from ast import literal_eval
from itertools import chain
from urllib.parse import unquote

import flask
from flask.json import jsonify

from pyload.core.api import BaseObject

from ..helpers import clear_session, set_session, login_required


bp = flask.Blueprint("api", __name__, url_prefix="/api")


# accepting positional arguments, as well as kwargs via post and get
# @bottle.route(
# r"/api/<func><args:re:[a-zA-Z0-9\-_/\"\'\[\]%{},]*>")
@login_required("ALL")
@bp.route("/<func>", methods=["GET", "POST"], endpoint="rpc")
@bp.route("/<func>/<path:args>", methods=["GET", "POST"], endpoint="rpc")
# @apiver_check
def rpc(func, args=""):

    api = flask.current_app.config["PYLOAD_API"]
    s = flask.session
    if not api.isAuthorized(func, {"role": s["role"], "permission": s["perms"]}):
        return "Unauthorized", 401
        
    args = args.split("/")
    kwargs = {}

    for x, y in chain(
        flask.request.args.items(), flask.request.form.items()
    ):
        kwargs[x] = unquote(y)

    try:
        return call_api(func, *args, **kwargs)
    except Exception as exc:
        return jsonify(error=exc, traceback=traceback.format_exc()), 500


def call_api(func, *args, **kwargs):
    api = flask.current_app.config["PYLOAD_API"]

    if not hasattr(api.EXTERNAL, func) or func.startswith("_"):
        flask.flash(f"Invalid API call '{func}'")
        return "Not Found", 404

    result = getattr(api, func)(
        *[literal_eval(x) for x in args],
        **{x: literal_eval(y) for x, y in kwargs.items()},
    )

    # null is invalid json response
    return jsonify(result or True)


@bp.route("/login", methods=["POST"], endpoint="login")
# @apiver_check
def login():
    user = flask.request.form["username"]
    password = flask.request.form["password"]

    api = flask.current_app.config["PYLOAD_API"]
    user_info = api.checkAuth(user, password)

    if not user_info:
        return jsonify(False)

    s = set_session(user_info)
    flask.flash("Logged in successfully")
    
    return jsonify(s)


@bp.route("/logout", endpoint="logout")
# @apiver_check
def logout():
    # logout_user()
    clear_session()
    return jsonify(True)
