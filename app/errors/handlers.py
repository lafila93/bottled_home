from app.errors import bp
from flask import render_template


@bp.app_errorhandler(401)
def unauthorized(e):
    return render_template("errors/401.html", title="Unauthorized"), 401


@bp.app_errorhandler(404)
def page_not_found(e):
    return render_template("errors/404.html", title="Not found"), 404
