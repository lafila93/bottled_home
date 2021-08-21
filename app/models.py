from app import db
from datetime import datetime

class Sensor_Reading(db.Model):
    __tablename__ = "sensor_reading"
    id = db.Column(db.Integer, primary_key=True)
    sensor_id = db.Column(db.Integer, db.ForeignKey("sensor.id"), nullable=False)
    value = db.Column(db.Float)
    datetime = db.Column(db.DateTime, default=datetime.utcnow)

    sensor = db.relationship("Sensor", back_populates="readings")

    def __repr__(self):
        return "Sensor_Reading<id={}, sensor_id={}, value={}, datetime={}>".format(
            self.id, self.sensor_id, self.value, self.datetime
        )

    def to_dict(self):
        return {
            "value" : self.value,
            "datetime" : self.datetime.strftime('%Y-%m-%dT%H:%M:%SZ'),
        }

class Sensor(db.Model):
    __tablename__ = "sensor"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True)
    unit = db.Column(db.String)
    comment = db.Column(db.String)

    readings = db.relationship("Sensor_Reading", back_populates="sensor")

    def __repr__(self):
        return "Sensor<id={}, name={}, unit={}, comment={}>".format(
            self.id, self.name, self.unit, self.comment
        )

    def to_dict(self):
        return {
            "id" : self.id,
            "name" : self.name,
            "unit" : self.unit,
            "comment" : self.comment,
            "readings" : len(self.readings),
        }
