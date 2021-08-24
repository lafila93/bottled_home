from datetime import datetime, timedelta

from app import db, models
from app.api import bp
from app.api.errors import bad_request, error_response
from flask import jsonify, request


@bp.route("/sensor")
def sensor_get():
    """ route for sensor get request

    Request Args:
        column_name1[]: filtering the amount of sensors by given column values

    Returns:
        response: JSON object of all sensors
    """
    q = models.Sensor.query

    # maps sqlalchemy column to respective request args
    # "...?id[]=1&id[]=2" -> {sqlcolumn(id) : ["1", "2"], sqlcolumn(name) : [], ...}
    mapper = {col : request.args.getlist(col.name + "[]") for 
        col in models.Sensor.__table__.columns}

    # filter based on reponse arguments
    for col, values in mapper.items():
        if len(values) > 0:
            q = q.filter(col.in_(values))
    
    sensors = q.all()

    # {id : sensor_object}
    return jsonify({s.id : s.to_dict() for s in sensors})


@bp.route("/sensor/columns")
def sensor_columns():
    """ Displays the table columns
    """
    return jsonify(models.Sensor.column_properties())


@bp.route("/sensor", methods=["POST"])
def sensor_post():
    """ Adding sensors

    Request Header:
        Content-Type: application/json

    Request Args:
        any valid columns and values of sensor object

    Returns:
        response: JSON object of new sensor
    """
    data = request.get_json()

    # check if all arguments in json data are valid columns
    columns = set(models.Sensor.column_names())
    if not all(key in columns for key in data.keys()):
        return bad_request("Invalid columns")

    sensor = models.Sensor(**data)
    db.session.add(sensor)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return bad_request("Could not create sensor: '{}'".format(e))

    return jsonify(sensor.to_dict())


@bp.route("/sensor/<int:id>", methods=["DELETE"])
def sensor_delete(id):
    """ sensor delete
    
    Args:
        id (int): id of sensor that should be deleted

    Returns:
        response: empty
    """
    sensor = models.Sensor.query.get(id)
    if sensor is None:
        return bad_request("Sensor with id {} does not exist".format(id))
    db.session.delete(sensor)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return bad_request("Could not delete sensor: '{}'".format(e))
    return "", 200


@bp.route("/sensor/<int:id>", methods=["PUT"])
def sensor_put(id):
    """ sensor update

    Args:
        id (int): id of sensor that should be updated

    Request Header:
        Content-Type: application/json

    Request Args:
        any valid column names and values of sensor object
    """
    data = request.get_json()

    sensor = models.Sensor.query.get(id)
    if sensor is None:
        return bad_request("Sensor with id {} does not exist".format(id))

    # check if all data keys are valid column names
    columns = set(models.Sensor.column_names())
    if not all(key in columns for key in data.keys()):
        return bad_request("Invalid columns")

    # set new values
    for key, value in data.items():
        setattr(sensor, key, value)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return bad_request("Could not update sensor: '{}'".format(e))

    return jsonify(sensor.to_dict())


@bp.route("/sensor/reading")
def sensor_reading_get():
    """ route for sensor reading get request

    Request Args:
        sensor_id[]: one or more sensor ids
        days: number of days behind to retrieve data up to
        minutes: number of minutes behind to retrieve data up to

    Returns:
        response: JSON object of sensors_id keys and minimal reading values
    """
    ids = request.args.getlist("sensor_id[]")
    try:
        ids = {int(id) for id in ids}
    except TypeError:
        return bad_request("sensor_id needs to be integers")

    # check for invalid ids
    for id in ids:    
        if models.Sensor.query.get(id) is None:
            return bad_request("Unknown sensor id {}".format(id))

    days = request.args.get("days", 0)
    minutes = request.args.get("minutes", 0)
    try:
        days = int(days)
        minutes = int(minutes)
    except ValueError:
        return bad_request("'days' and 'minutes' need to be integers")
    start = datetime.utcnow() - timedelta(days=days, minutes=minutes)

    data = {}
    for id in ids:
        readings = models.SensorReading.query.filter(
            models.SensorReading.sensor_id == id).filter(
            models.SensorReading.datetime >= start).order_by(
            models.SensorReading.datetime.asc()).all()
        # generate minimal sensor reading entries
        data[id] = [r.to_dict("value", "datetime") for r in readings]

    return jsonify(data)


@bp.route("/sensor/reading/columns")
def sensor_reading_columns():
    """ Displays the table columns
    """
    return jsonify(models.SensorReading.column_properties())


@bp.route("/sensor/reading", methods=["POST"])
def sensor_reading_post():
    """ create new sensor readings

    Request Header:
        Content-Type: application/json

    Request Args:
        any valid sensor reading column names and values
    """
    data = request.get_json()

    # check if all data keys are column names
    columns = set(models.SensorReading.__table__.columns.keys())
    if not all(key in columns for key in data.keys()):
        return bad_request("Invalid columns")

    # check if sensor_id exists
    sensor_id = data.get("sensor_id")
    if sensor_id is None or models.Sensor.query.get(sensor_id) is None:
        return bad_request("'sensor_id' not set or invalid")

    r = models.SensorReading(**data)
    db.session.add(r)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return bad_request("Could not create sensor reading: '{}'".format(e))
    
    return jsonify(r.to_dict())


@bp.route("/sensor/reading/<int:id>", methods=["DELETE"])
def sensor_reading_delete(id):
    """ delete sensor readings

    Args:
        id (int): id of reading
    """
    r = models.SensorReading.query.get(id)
    if r is None:
        return bad_request("Sensor reading with id {} does not exist".format(id))
    db.session.delete(r)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return bad_request("Could not delete sensor reading: '{}'".format(e))
    return "", 200


@bp.route("/sensor/reading/<int:id>", methods=["PUT"])
def sensor_reading_put(id):
    """ change sensor readings

    Args:
        id (int): id of reading

    Request Header:
        Content-Type: application/json

    Request Args:
        any valid sensor reading column names and values
    """
    data = request.get_json()

    r = models.SensorReading.query.get(id)
    if r is None:
        return bad_request("Sensor reading with id {} does not exist".format(id))
    
    # check if all data keys are column names
    columns = models.SensorReading.__table__.columns.keys()
    if not all(key in columns for key in data.keys()):
        return bad_request("Invalid columns")

    # set new data
    for key, value in data.items():
        setattr(r, key, value)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return bad_request("Could not update sensor reading: '{}'".format(e))

    return jsonify(r.to_dict())
