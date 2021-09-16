import time
import datetime

from app import db, helper, models
from app.api import bp
from app.api.errors import bad_request
from flask import jsonify, request
from sqlalchemy import func


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
        sensor_id[]: optional, one or more sensor ids
        timedelta: optional, number of seconds behind to retrieve data up to
        timeinterval: optional, letter for datetime grouping
        timeinterval_function: optional, function for grouping, avg by default

    Returns:
        response: JSON object of sensors_id keys and minimal reading values
    """
    # grab sensor_id[] arguments and deduplicate
    ids = request.args.getlist("sensor_id[]")
    try:
        ids = {int(id) for id in ids}
    except TypeError:
        return bad_request("sensor_id needs to be integers")

    # check if all sensor_ids are present
    found_ids = [s.id for s in 
        models.Sensor.query.filter(models.Sensor.id.in_(ids)).all()]
    xor_ids = ids.symmetric_difference(found_ids)
    if xor_ids:
        return bad_request("Unknown sensor id(s) {}".format(xor_ids))
        
    # if no ids given, grab all ids
    if len(ids) == 0:
        ids = [s.id for s in models.Sensor.query.all()]

    timedelta = request.args.get("timedelta", 0)
    try:
        timedelta = float(timedelta)
    except ValueError:
        return bad_request("'timedelta' needs to be a number")
    end = datetime.datetime.utcnow()
    start = end - datetime.timedelta(seconds=timedelta)
    
    base_query = models.SensorReading.query \
        .filter(models.SensorReading.sensor_id.in_(ids)) \
        .filter(models.SensorReading.datetime.between(start, end)) \
        .order_by(models.SensorReading.datetime.asc())

    # data container for response
    data = {id: [] for id in ids}

    ti = request.args.get("timeinterval")
    if not ti is None:
        # handle timeinterval argument
        try:
            ti = int(ti)
        except ValueError:
            pass
        try:
            timeinterval_query_func = models.SensorReading.timeinterval_grouper(ti)
        except ValueError as e:
            return bad_request("'timeinterval' value invalid: {}".format(e))

        func_mapper = {"avg": func.avg, "min": func.min, "max": func.max, "sum": func.sum}
        ti_func = func_mapper.get(request.args.get("timeinterval_function", "avg"))
        if ti_func is None:
            return bad_request("'timeinterval_function' needs to be one of {}".format(list(func_mapper.keys())))

        
        base_query = base_query.with_entities(
            models.SensorReading.sensor_id,
            timeinterval_query_func.label("timeinterval"),
            ti_func(models.SensorReading.value).label("value_agg"),
            func.count(models.SensorReading.id).label("count"),
        ).group_by("timeinterval", models.SensorReading.sensor_id)

        for row in base_query.all():
            data[row.sensor_id].append({
                "value": row.value_agg,
                "datetime" : helper.to_datetime(row.timeinterval).isoformat(),
                "count" : row.count,
            })
    else:
        for row in base_query.all():
            data[row.sensor_id].append({
                "value": row.value,
                "datetime": row.datetime.isoformat(),
            })

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
                reading_dict["datetime"] = helper.to_datetime(timestamp)
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
            data["datetime"] = helper.to_datetime(timestamp)
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
