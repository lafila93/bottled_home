from datetime import datetime, timedelta

from app import auth_token, db, models
from app.api import bp
from app.api.errors import bad_request, error_response
from flask import jsonify, request


@bp.route("/sensor")
@auth_token.login_required
def sensor_get():
    """ route for sensor get request

    Request Args:
        column_name1[]: filtering the amount of sensors by given column values

    Returns:
        response: JSON object of all sensors
    """
    # filter sensors by user id beforehand
    q = models.Sensor.query.filter_by(user_id=auth_token.current_user().id)

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
@auth_token.login_required
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

    # check if all arguments in json data can be set
    for key in data.keys():
        if not key in models.Sensor.api_valid_setter:
            return bad_request("Invalid column: '{}' - column cannot be set".format(key))

    sensor = models.Sensor(**data)
    sensor.user = auth_token.current_user()
    db.session.add(sensor)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return bad_request("Could not create sensor: '{}'".format(e))

    return jsonify(sensor.to_dict())


@bp.route("/sensor/<int:id>", methods=["DELETE"])
@auth_token.login_required
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
    if sensor.user != auth_token.current_user():
        return error_response(401, "You do not have permissions to delete this sensor.")
    db.session.delete(sensor)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return bad_request("Could not delete sensor: '{}'".format(e))
    return "", 200


@bp.route("/sensor/<int:id>", methods=["PUT"])
@auth_token.login_required
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
    if sensor.user != auth_token.current_user():
        return error_response(401, "You do not have permissions to change this sensor.")
    # check if all arguments in json data can be set
    for key in data.keys():
        if not key in models.Sensor.api_valid_setter:
            return bad_request("Invalid column: '{}' - column cannot be modified".format(key))

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
@auth_token.login_required
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
        s = models.Sensor.query.get(id)
        if s is None:
            return bad_request("Unknown sensor id {}".format(id))
        if s.user != auth_token.current_user():
            return error_response(401, "No Permission to collect readings from sensor {}".format(s.id))
        

    # if no ids given, grab all ids
    if len(ids) == 0:
        ids = [s.id for s in models.Sensor.query.filter_by(
            user_id=auth_token.current_user().id).all()]

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
@auth_token.login_required
def sensor_reading_post():
    """ create new sensor readings

    Request Header:
        Content-Type: application/json

    Request Args:
        any valid sensor reading column names and values as single obj or list of obj
    """
    data = request.get_json()

    # convert dict to list of single dict
    if not isinstance(data, list):
        data = [data]

    readings = []
    columns = set(models.SensorReading.column_names())
    for reading_dict in data:
        # check if all arguments in json data can be set
        for key in reading_dict.keys():
            if not key in models.SensorReading.api_valid_setter:
                return bad_request("Invalid column: '{}' - column cannot be set".format(key))

        # check if sensor_id exists
        sensor_id = reading_dict.get("sensor_id")
        sensor = models.Sensor.query.get(sensor_id)
        if sensor_id is None or sensor is None:
            return bad_request("'sensor_id' not set or invalid: '{}'".format(sensor_id))
        
        if sensor.user != auth_token.current_user():
            return error_response(401, "No permissions to add readings to sensor {}".format(sensor_id))

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
@auth_token.login_required
def sensor_reading_delete(id):
    """ delete sensor readings

    Args:
        id (int): id of reading
    """
    r = models.SensorReading.query.get(id)
    if r is None:
        return bad_request("Sensor reading with id {} does not exist".format(id))
    if r.sensor.user != auth_token.current_user():
        return error_response(401, "No permissions to delete sensor reading")

    db.session.delete(r)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return bad_request("Could not delete sensor reading: '{}'".format(e))
    return "", 200


@bp.route("/sensor/reading/<int:id>", methods=["PUT"])
@auth_token.login_required
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
    if r.sensor.user != auth_token.current_user():
        return error_response(401, "No permissions to modify sensor reading")
    
    # check if all arguments in json data can be set
    for key in data.keys():
        if not key in models.SensorReading.api_valid_setter:
            return bad_request("Invalid column: '{}' - column cannot be modified".format(key))

    # set new data
    for key, value in data.items():
        setattr(r, key, value)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return bad_request("Could not update sensor reading: '{}'".format(e))

    return jsonify(r.to_dict())
