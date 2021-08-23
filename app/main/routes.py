from app.main import bp
from flask import render_template, abort
from app import models


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/sensor")
def sensor():
    return render_template("sensor.html", title="Sensor")


@bp.route("/sensor/<int:id>")
def sensor_id(id):
    if models.Sensor.query.get(id) is None:
        return abort(404)

    return render_template("sensor_id.html", title="Edit Sensor")

@bp.route("/sensor/new")
def sensor_new():
    return render_template("sensor_new.html", title="New Sensor")

@bp.route("/about")
def about():
    return render_template("about.html", title="About")
