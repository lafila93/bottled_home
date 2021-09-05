from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired


class SensorForm(FlaskForm):
    name = StringField("Name", [DataRequired()])
    unit = StringField("Unit")
    description = StringField("Description")
