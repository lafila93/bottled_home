from app import db
from datetime import datetime


class ColumnMixin:
    @classmethod
    def column_properties(cls):
        """Returns list of table columns dicts

        Returns:
            list(dict): list of dicts describing the table columns
        """
        columns = []
        for column in cls.__table__.c:
            columns.append({
                "name" : column.name,
                "type" : str(column.type),
                "nullable" : column.nullable,
                "primary_key" : column.primary_key,
                "unique" : column.unique,
            })
        return columns


class SensorReading(db.Model, ColumnMixin):
    __tablename__ = "sensor_reading"
    id = db.Column(db.Integer, primary_key=True)
    sensor_id = db.Column(db.Integer, 
        db.ForeignKey("sensor.id", onupdate="CASCADE"), nullable=False)
    value = db.Column(db.Float, nullable=False)
    datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    sensor = db.relationship("Sensor", back_populates="readings")

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


class Sensor(db.Model, ColumnMixin):
    __tablename__ = "sensor"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True)
    unit = db.Column(db.String)
    description = db.Column(db.String)

    readings = db.relationship(
        "SensorReading",
        back_populates="sensor",
        cascade="all, delete-orphan",
    )

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
        }
