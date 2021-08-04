from flask_wtf import FlaskForm
from wtforms import SubmitField


class DeleteForm(FlaskForm):
    submit = SubmitField()
