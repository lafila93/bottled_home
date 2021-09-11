from datetime import datetime, timedelta
import time

from app import db, models
from app.api import bp
from app.api.errors import bad_request
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
    data = request.get_json() or {} #set empty dict if None

    # check if all arguments in json data can be set
    for key in data.keys():
        if not key in models.Sensor.column_names():
            return bad_request("Column does not exist: '{}'".format(key))

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
    data = request.get_json() or {}

    sensor = models.Sensor.query.get(id)
    if sensor is None:
        return bad_request("Sensor with id {} does not exist".format(id))
    # check if all arguments in json data can be set
    for key in data.keys():
        if not key in sensor.column_names():
            return bad_request("Column does not exist: '{}'".format(key))

    # set new values
    sensor.update(**data)

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
    # grab sensor_id[] arguments and deduplicate
    ids = request.args.getlist("sensor_id[]")
    try:
        ids = {int(id) for id in ids}
    except TypeError:
        return bad_request("sensor_id needs to be integers")

    # check for invalid ids
    for id in ids:    
        if models.Sensor.query.get(id) is None:
            return bad_request("Unknown sensor id {}".format(id))
        
    # if no ids given, grab all ids
    if len(ids) == 0:
        ids = [s.id for s in models.Sensor.query.all()]

    days = request.args.get("days", 0)
    minutes = request.args.get("minutes", 0)
    try:
        days = float(days)
        minutes = float(minutes)
    except ValueError:
        return bad_request("'days' and 'minutes' need to be numbers")
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
        any valid sensor reading column names and values as single obj or list of obj
    """
    data = request.get_json() or {}

    # convert dict to list of single dict
    if not isinstance(data, list):
        data = [data]

    readings = []
    for reading_dict in data:
        # check if all arguments in json data can be set
        for key in reading_dict.keys():
            if not key in models.SensorReading.column_names():
                return bad_request("Column does not exist: '{}'".format(key))

        # check if sensor_id exists
        sensor_id = reading_dict.get("sensor_id")
        sensor = models.Sensor.query.get(sensor_id)
        if sensor_id is None or sensor is None:
            return bad_request("'sensor_id' not set or invalid: '{}'".format(sensor_id))

        # if datetime timestamp is given, try to convert
        if "datetime" in reading_dict:
            timestamp = reading_dict["datetime"]
            try:
                reading_dict["datetime"] = datetime.fromtimestamp(timestamp)
            except TypeError as e:
                return bad_request("Could not convert given datetime timestamp: '{}'".format(timestamp))

        # create new reading
        r = models.SensorReading(**reading_dict)
        readings.append(r)

    db.session.add_all(readings)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return bad_request("Could not create sensor reading(s): '{}'".format(e))
    
    return jsonify([r.to_dict() for r in readings])


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
    data = request.get_json() or {}

    r = models.SensorReading.query.get(id)
    if r is None:
        return bad_request("Sensor reading with id {} does not exist".format(id))
    
    # check if all arguments in json data can be set
    for key in data.keys():
        if not key in r.column_names():
            return bad_request("Column does not exist: '{}'".format(key))

    # if datetime timestamp is given, try to convert
    if "datetime" in data:
        timestamp = data["datetime"]
        try:
            data["datetime"] = datetime.fromtimestamp(timestamp)
        except TypeError as e:
            return bad_request("Could not convert given datetime timestamp: '{}'".format(timestamp))

    # set new data
    r.update(**data)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return bad_request("Could not update sensor reading: '{}'".format(e))

    return jsonify(r.to_dict())

@bp.route("/timestamp")
def timestamp():
    return jsonify(time.time())
