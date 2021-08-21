from app.main import bp
from flask import render_template

@bp.route("/")
def index():
    return render_template("index.html")

@bp.route("/sensors")
def sensors():
    return render_template("sensors.html", title="Sensors")

@bp.route("/led")
def led():
    return render_template("led.html", title="LED")
