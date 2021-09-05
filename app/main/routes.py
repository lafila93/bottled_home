from app import models
from app.main import bp
from app.main.forms import SensorForm
from flask import abort, render_template
from flask_login import current_user, login_required


@bp.app_errorhandler(404)
def page_not_found(e):
    return render_template("404.html", title="Not found"), 404

@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/sensor")
@login_required
def sensor():
    return render_template("sensor.html", title="Sensor")


@bp.route("/sensor/<int:id>")
@login_required
def sensor_id(id):
    s = models.Sensor.query.get(id)
    if s is None:
        return abort(404)
    if s.user != current_user:
        return abort(401)
    
    form = SensorForm()
    for key in ("name", "unit", "description"):
        setattr(getattr(form, key), "data", getattr(s, key))

    return render_template("sensor_id.html", title="Edit Sensor", form=form)

@bp.route("/sensor/new")
@login_required
def sensor_new():
    form = SensorForm()
    return render_template("sensor_new.html", title="New Sensor", form=form)

@bp.route("/about")
def about():
    return render_template("about.html", title="About")
