from app import models
from app.main import bp
from app.main.forms import SensorForm
from flask import abort, render_template


@bp.route("/")
def index():
    return render_template("main/index.html")


@bp.route("/sensor")
def sensor():
    return render_template("main/sensor.html", title="Sensor")


@bp.route("/sensor/<int:id>")
def sensor_id(id):
    s = models.Sensor.query.get(id)
    if s is None:
        return abort(404)
    
    form = SensorForm()
    # prefill sensor form
    for key in models.Sensor.column_names():
        setattr(getattr(form, key), "data", getattr(s, key))

    return render_template("main/sensor_id.html", title="Edit Sensor", form=form)

@bp.route("/sensor/new")
def sensor_new():
    form = SensorForm()
    return render_template("main/sensor_new.html", title="New Sensor", form=form)

@bp.route("/about")
def about():
    return render_template("main/about.html", title="About")
