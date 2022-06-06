from flask_wtf import FlaskForm
from wtforms import SelectField
from wtforms.validators import DataRequired

class TimezoneForm(FlaskForm):
    timezone = SelectField(
        'timezone',
        [DataRequired()],
        # choices=[
        #         ('Africa/Abidjan', 'Africa/Abidjan'),
        #         ('Africa/Accra', 'Africa/Accra'),
        #         ('Africa/Addis_Ababa', 'Africa/Addis_Ababa'),
        #     ],
        choices = [],
        )