from datetime import datetime, timedelta

from app import db, models
from app.api import bp
from app.api.errors import bad_request, error_response
from flask import jsonify, request


@bp.route("/sensor/<name>")
def sensor_name_get(name):
    """ route for sensor data get request

    request arguments:
        days: number of days behind to retrieve data up to
        minutes: number of minutes behind to retrieve data up to

    Args:
        name: name(s) of valid sensors, separated by '&' if multiple

    Returns:
        response: JSON
    """
    #multiple sensors can be queried, separated by &
    names = name.split("&")

    for name in names:
        #unknown sensor
        if models.Sensor.query.filter_by(name=name).first() is None:
            return bad_request("Unknown sensor '{}'".format(name))

    days = request.args.get("days", 0)
    minutes = request.args.get("minutes", 0)

    try:
        days = int(days)
        minutes = int(minutes)
    except ValueError:
        return bad_request("'days' and 'minutes' need to be integers")
    start = datetime.utcnow() - timedelta(days=days, minutes=minutes)

    data = {}
    for name in names:
        readings = models.Sensor_Reading.query.join(
            models.Sensor).filter(
            models.Sensor.name == name).filter(
            models.Sensor_Reading.datetime >= start).all()
        data[name] = [r.to_dict() for r in readings]

    return jsonify(data)


@bp.route("/sensor/<name>", methods=["POST"])
def sensor_name_post(name):
    """ route for sensor data post request

    request header:
        Content-Type: application/json

    request data:
        {"value": float}

    Args:
        name: name of valid sensor
    """

    if "&" in name:
        return bad_request("Invalid character in sensor name '&'")

    t = models.Sensor.query.filter_by(name=name).first()
    # create new if non existant
    if t is None:
        t = models.Sensor(name=name)
        db.session.add(t)

    try:
        data = request.get_json()

        r = models.Sensor_Reading()
        r.value = float(data["value"])
        r.sensor = t
        db.session.add(r)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return bad_request()
    
    return "", 200

@bp.route("/sensor")
def sensor_get():
    """ route for sensor get request

    Returns:
        response: JSON of all sensors
    """
    sensors = models.Sensor.query.all()
    return jsonify([s.to_dict() for s in sensors])
