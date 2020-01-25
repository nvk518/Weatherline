from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField
from wtforms.validators import DataRequired, NumberRange, Length
from datetime import datetime

class LocationsForm(FlaskForm):
	m = IntegerField('Month', validators=[DataRequired(), NumberRange(min=1,max=12)])
	d = IntegerField('Day', validators=[DataRequired(), NumberRange(min=1,max=31)])
	y = IntegerField('Year', validators=[DataRequired(), NumberRange(min=2020)])
	location = StringField('Location (City, Zip, Place)', validators=[DataRequired()])
	description = StringField('Description', validators=[])	
	edit_loc = SubmitField('Edit')
	add_day = SubmitField('Add day')

	# requires validation for date

class PartialLocationsForm(FlaskForm):
	location = StringField('Location (City, Zip, Place)', validators=[DataRequired()])
	add_day = SubmitField('Add day')
