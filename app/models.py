import time
from datetime import datetime

import jwt
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import auth_token, db, login_manager


class ApiMixin:

    api_valid_setter = set()

    @classmethod
    def column_names(cls):
        """ Returns list of column names

        Returns:
            list
        """
        return cls.__table__.columns.keys()

    @classmethod
    def column_properties(cls):
        """Returns list of table columns dicts

        Returns:
            list(dict): list of dicts describing the table columns
        """
        columns = []
        for column in cls.__table__.columns:
            columns.append({
                "name" : column.name,
                "type" : str(column.type),
                "nullable" : column.nullable,
                "primary_key" : column.primary_key,
                "unique" : column.unique,
            })
        return columns


class SensorReading(db.Model, ApiMixin):
    __tablename__ = "sensor_reading"

    id = db.Column(db.Integer, primary_key=True)
    sensor_id = db.Column(db.Integer, 
        db.ForeignKey("sensor.id", onupdate="CASCADE"), nullable=False)
    value = db.Column(db.Float, nullable=True)
    datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # relationships
    sensor = db.relationship("Sensor", back_populates="readings")

    api_valid_setter = {"sensor_id", "value", "datetime"}

    def __repr__(self):
        return "SensorReading<id={}, sensor_id={}, value={}, datetime={}>".format(
            self.id, self.sensor_id, self.value, self.datetime
        )

    def to_dict(self, *args):
        """Writes object to dictionary

        Args:
            *args: Strings of columns that should be used. if empty, every column is included
        """
        data = {
            "id" : self.id,
            "sensor_id" : self.sensor_id,
            "value" : self.value,
            "datetime" : self.datetime.strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        # reduce dict by *args values
        if len(args) > 0:
            data = {arg : data[arg] for arg in args}
        return data


class Sensor(db.Model, ApiMixin):
    __tablename__ = "sensor"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    unit = db.Column(db.String)
    description = db.Column(db.String)
    user_id = db.Column(db.Integer, 
        db.ForeignKey("user.id", onupdate="CASCADE"), nullable=False
    )

    # relationships
    readings = db.relationship(
        "SensorReading",
        back_populates="sensor",
        cascade="all, delete-orphan",
    )

    user = db.relationship(
        "User",
        back_populates="sensors",
    )

    api_valid_setter = {"name", "unit", "description"}

    def __repr__(self):
        return "Sensor<id={}, name={}, unit={}, description={}>".format(
            self.id, self.name, self.unit, self.description
        )

    def to_dict(self):
        return {
            "id" : self.id,
            "name" : self.name,
            "unit" : self.unit,
            "description" : self.description,
            "user_id" : self.user_id,
        }


class User(db.Model, UserMixin):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False, unique=True)
    password_hash = db.Column(db.String, nullable=False)

    sensors = db.relationship(
        "Sensor",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return "User<id={}, username='{}'>".format(self.id, self.username)

    def set_password(self, password):
        """Password hasher and setter

        Args:
            password (str): unhashed password

        Returns:
            self
        """
        self.password_hash = generate_password_hash(password)
        return self

    def check_password(self, password):
        """Password checker

        Args:
            password (str): unhashed password to compare with hashed stored one

        Returns:
            bool: password matches stored one
        """
        return check_password_hash(self.password_hash, password)

    def create_token(self, data_dict = {}, exp=3600):
        """Creates JWT with user id

        Args:
            data_dict (dict): additional data
            exp (int): token expiration timedelta
        
        Returns:
            str: signed token
        """
        for key in ("user_id", "exp"):
            if (key in data_dict):
                raise ValueError("'{}' may not be set in 'data_dict'".format(key))
        data = {"user_id" : self.id}
        if not exp is None:
            data["exp"] = int(time.time()) + exp
        data.update(data_dict)

        token = jwt.encode(data, current_app.config["SECRET_KEY"], "HS256")
        return token

    @classmethod
    def check_token(cls, token):
        """Returns user

        Args:
            token (str): jws token
        
        Returns:
            User object (models.User), data (dict): if valid or None, None otherwise
        """
        try:
            data = jwt.decode(token, current_app.config["SECRET_KEY"], "HS256")
        except Exception as _:
            return None, None
        return cls.query.get(data.get("user_id")), data


@login_manager.user_loader
def load_user(user_id):
    """User loader for LoginManager
    """
    return User.query.get(user_id)

@auth_token.verify_token
def verify_token(token):
    """User loader for token based HTTPAuth
    """
    return User.check_token(token)[0]
