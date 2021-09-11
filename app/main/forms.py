from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField
from wtforms.validators import DataRequired


class SensorForm(FlaskForm):
    id = IntegerField("Id")
    name = StringField("Name", [DataRequired()])
    unit = StringField("Unit")
    description = StringField("Description")
