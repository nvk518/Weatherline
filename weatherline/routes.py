import requests
import json
import os

from requests_oauthlib.compliance_fixes import facebook_compliance_fix
from requests_oauthlib import OAuth2Session
from flask import render_template, url_for, redirect, flash, request
from weatherline import app, db, login_manager
from weatherline.forms import LocationsForm, PartialLocationsForm
from datetime import datetime, timedelta
from flask_login import login_user, current_user, logout_user, login_required, UserMixin
from sqlalchemy import func, desc
from geocodio import GeocodioClient

def generate_weather(month, day, year, lat, lng):
	print('UPDATES')
	url = 'https://api.weatherbit.io/v2.0/forecast/daily?lat='+ str(lat) +'&lon='+ str(lng) +'&key='+ key + '&units=I'
	r = requests.get(url)
	data = json.loads(r.text)
	#ensuring month and day fit two digit representations (eg. 03 instead of 3)
	str_month = str(month)
	str_day = str(day)

	if month < 10:
		str_month = '0' + str_month

	if day < 10:
		str_day = '0' + str_day

	date_form = str(year) + '-' + str_month + '-' + str_day
	
	forecast = None
	for d in range(0, 16):
		if data.get('data')[d].get("valid_date") == date_form:
			forecast = data['data'][d]
			break

	def round_two_decimals(val):
		return round(val, 2)

	if forecast:
		weather = {
			'max_temp': round_two_decimals(forecast.get('high_temp')),
			'min_temp': round_two_decimals(forecast.get('low_temp')),
			'clouds': round_two_decimals(forecast.get('clouds')),
			'precip': round_two_decimals(forecast.get('pop')),
			'snow': round_two_decimals(forecast.get('snow'))
		}
	else:
		na = 'N/A'
		weather = {
			'max_temp': na,
			'min_temp': na,
			'clouds': na,
			'precip': na,
			'snow': na
		}
	return weather

def generate_geocoding(address):
	api_key = 'API_KEY'
	client = GeocodioClient(api_key)
	location = client.geocode(address)
	components = location.get('results')[0].get('address_components')
	print(location)
	latlong = location.get('results')[0].get('location')
	city = components.get('city')
	state = components.get('state')
	country = components.get('country')
	latitude = latlong.get('lat')
	longitude = latlong.get('lng')
	result = {
	'city': city,
	'state': state,
	'country': country,
	'lat': latitude,
	'lng': longitude
	}
	return result

class Day(db.Model):
	# cities = []
	id = db.Column(db.Integer, primary_key=True)
	user_email = db.Column(db.String(120), nullable=False)
	set_id = db.Column(db.Integer, nullable=False)
	city = db.Column(db.String(100), nullable=False)
	state = db.Column(db.String(100), nullable=False)
	country = db.Column(db.String(100), nullable=False)
	lat = db.Column(db.String(100), nullable=False)
	lng = db.Column(db.String(100), nullable=False)
	day = db.Column(db.Integer, nullable=False)
	month = db.Column(db.Integer, nullable=False)
	year = db.Column(db.Integer, nullable=False)
	max_temp = db.Column(db.Integer, nullable=False)
	min_temp = db.Column(db.Integer, nullable=False)
	clouds = db.Column(db.Integer, nullable=False)
	precip = db.Column(db.String(100), nullable=False)
	snow = db.Column(db.Integer, nullable=False)

	def report(self):
		return {
		'id': self.id, 
		'city': self.city, 
		'state': self.state, 
		'max_temp': self.max_temp,
		'min_temp': self.min_temp,
		'clouds': self.clouds, 
		'precip': self.precip, 
		'snow': self.snow
		}

	def update(self):
		report = generate_weather(self.month, self.day, self.year, self.lat, self.lng)
		self.max_temp = report.get('max_temp')
		self.min_temp = report.get('min_temp')
		self.clouds = report.get('clouds')
		self.precip = report.get('precip')
		self.snow = report.get('snow')

	def __repr__(self):
		return f"Day('{self.id}', '{self.set_id}', '{self.city}', '{self.state}', '{self.lat}', '{self.lng}', '{self.month}', '{self.day}', '{self.year}')"

@login_manager.user_loader
def load_user(user_id):
	return User.query.get(int(user_id))

class User(db.Model, UserMixin):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(20), unique=True, nullable=False)
	email = db.Column(db.String(120), unique=True, nullable=False)
	image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
	def __repr__(self):
		return f"User('{self.name}', '{self.email}', '{self.image_file}')"

class SiteDescription(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	email = db.Column(db.String(120), nullable=False)
	set_id = db.Column(db.Integer, nullable=False)
	description = db.Column(db.String(60), nullable=False)

# db.drop_all()
db.create_all()
db.session.commit()




FB_CLIENT_ID='CLIENT_ID'
FB_CLIENT_SECRET='CLIENT_SECRET'

FB_AUTHORIZATION_BASE_URL = "https://www.facebook.com/dialog/oauth"
FB_TOKEN_URL = "https://graph.facebook.com/oauth/access_token"

#running locally
URL = "http://localhost:5000"

FB_SCOPE = ["email"]


#Weatherbit API key
key = 'API_KEY'

current_set_id = 1



@app.route("/")
@app.route("/home")
def home():
	return render_template('home.html')


@app.route('/plan', methods=['GET','POST'])
@login_required
def plan():
	print(Day.query.all())
	global current_set_id


	has_set = False
	

	for d in Day.query.filter_by(user_email = current_user.email):
		has_set = True
	if has_set:
		if request.method == 'POST':
			set_id = request.form.get('add')
			set_id_edit = request.form.get('edit')
			edit_day = request.form.get('edit_loc')
			delete_day = request.form.get('delete_day')

			if set_id is not None:
				#makes the current_set_id to the last existing + 1
				current_set_id = int(set_id) + 1
			elif set_id_edit is not None:
				#makes the current_set_id to the set being edited
				current_set_id = set_id_edit
			elif edit_day is not None:
				#edit the day
				form = PartialLocationsForm()
				day = Day.query.filter_by(id = edit_day).first()
				try:
					parse = generate_geocoding(form.location.data)
				except:
					flash('Location not found. Only cities in the United States and Canada are supported at this time.', 'danger')
					return redirect(url_for("plan"))
				day.city = parse.get('city')
				day.state = parse.get('state')
				day.country = parse.get('country')
				day.lat = parse.get('lat')
				day.lng = parse.get('lng')
				day.update()
				db.session.commit()
				flash('City changed successfully', 'success')
				return redirect(url_for("plan"))
			elif delete_day is not None:
				selection = Day.query.filter_by(id = delete_day)
				d = selection.first()
				mon = d.month
				day = d.day
				year = d.year
				city = d.city
				state = d.state
				deleted_set_id = d.set_id
				selection.delete()
				if not Day.query.filter_by(user_email = current_user.email, set_id=deleted_set_id).all():
					SiteDescription.query.filter_by(email = current_user.email, set_id=deleted_set_id).delete()
				else:
					# change ones after to one day before
					for d in Day.query.filter_by(user_email = current_user.email, set_id=current_set_id).filter(int(delete_day) < Day.id).all():
						subtract_day = datetime(month=d.month, day=d.day, year=d.year) 
						subtract_day -= timedelta(days=1)
						d.day = subtract_day.day
						d.month = subtract_day.month
						d.year = subtract_day.year
						d.update()			
				db.session.commit()
				

				flash(city + ', ' + state + ' on ' + str(mon) + '/' + str(day) + '/' + str(year) + ' has been deleted', 'success')
				return redirect(url_for("plan"))

	else:
		current_set_id = 1

	not_empty = False
	for d in Day.query.filter_by(user_email = current_user.email, set_id=current_set_id):
		not_empty = True


	if not_empty:
		last = db.session.query(Day).filter_by(user_email = current_user.email, set_id=current_set_id).order_by(Day.id.desc()).first()
		next_day = datetime(month=last.month, day=last.day, year=last.year) 
		next_day += timedelta(days=1)
		form = PartialLocationsForm()
	else:
		form = LocationsForm()



	if form.validate_on_submit() and not not_empty:
		#first item of the set added
		try:
			parse = generate_geocoding(form.location.data)
		except:
			flash('Location not found. Only cities in the United States and Canada are supported at this time.', 'danger')
			return redirect(url_for("plan"))
		city = parse.get('city')
		state = parse.get('state')
		country = parse.get('country')
		lat = parse.get('lat')
		lng = parse.get('lng')
		weather = generate_weather(form.m.data, form.d.data, form.y.data, lat, lng)
		day = Day(set_id=current_set_id, user_email = current_user.email, city=city, state=state, country=country, lat=lat, lng=lng, day=form.d.data, month=form.m.data, year=form.y.data, max_temp=weather.get('max_temp'), min_temp=weather.get('min_temp'), clouds=weather.get('clouds'), precip=weather.get('precip'), snow=weather.get('snow'))
		sd = SiteDescription(set_id=current_set_id, email=current_user.email, description=form.description.data)
		db.session.add(day)
		db.session.add(sd)
		db.session.commit()
		flash('Day added', 'success')
		next_day = datetime(month=day.month, day=day.day, year=day.year) 
		next_day += timedelta(days=1)
		return render_template('plan.html', SiteDescription=SiteDescription, current_set_id=current_set_id, desc=desc, db=db, form=form, adding=True, mon=next_day.month, day=next_day.day, year=next_day.year, Day=Day)
	elif form.validate_on_submit() and not_empty:
		try:
			parse = generate_geocoding(form.location.data)
		except:
			flash('Location not found. Only cities in the United States and Canada are supported at this time.', 'danger')
			return redirect(url_for("plan"))
		city = parse.get('city')
		state = parse.get('state')
		country = parse.get('country')
		lat = parse.get('lat')
		lng = parse.get('lng')
		weather = generate_weather(next_day.month, next_day.day, next_day.year, lat, lng)
		day = Day(set_id=current_set_id, user_email = current_user.email, city=city, state=state, country=country, lat=lat, lng=lng, day=next_day.day, month=next_day.month, year=next_day.year, max_temp=weather.get('max_temp'), min_temp=weather.get('min_temp'), clouds=weather.get('clouds'), precip=weather.get('precip'), snow=weather.get('snow'))
		db.session.add(day)
		db.session.commit()
		flash('Day added', 'success')
		return render_template('plan.html', SiteDescription=SiteDescription, current_set_id=current_set_id, desc=desc, db=db, form=form, adding=not_empty, mon=next_day.month, day=next_day.day, year=next_day.year, Day=Day)
	elif form.add_day.data and form.is_submitted() and form.errors.items():
		for a, b in form.errors.items():
			flash(b, 'danger')
		return redirect(url_for("plan"))
	elif not_empty:
		return render_template('plan.html', SiteDescription=SiteDescription, current_set_id=current_set_id, desc=desc, db=db, form=form, adding=not_empty, mon=next_day.month, day=next_day.day, year=next_day.year, Day=Day)
	else:
		print('adding page')
		return render_template('plan.html', SiteDescription=SiteDescription, current_set_id=current_set_id, desc=desc, form=form, adding=not_empty, Day=Day)

@app.route('/login')
def login():
	if current_user.is_authenticated:
		return redirect(url_for('account'))
	else:
		facebook = OAuth2Session(
			FB_CLIENT_ID, redirect_uri=URL + "/fb-callback", scope=FB_SCOPE
		)
		authorization_url, _ = facebook.authorization_url(FB_AUTHORIZATION_BASE_URL)
		return redirect(authorization_url)




@app.route("/fb-callback")
def callback():
	facebook = OAuth2Session(
		FB_CLIENT_ID, scope=FB_SCOPE, redirect_uri=URL + "/fb-callback"
	)

	facebook = facebook_compliance_fix(facebook)

	facebook.fetch_token(
		FB_TOKEN_URL,
		client_secret=FB_CLIENT_SECRET,
		authorization_response=request.url,
	)


	facebook_user_data = facebook.get(
		"https://graph.facebook.com/me?fields=id,name,email,picture{url}"
	).json()

	email = facebook_user_data["email"]
	name = facebook_user_data["name"]
	picture_url = facebook_user_data.get("picture", {}).get("data", {}).get("url")
	user = User.query.filter_by(email = email).first()
	if not user:
		user = User(name=name, email=email, image_file=picture_url)
		db.session.add(user)
		db.session.commit()
	login_user(user)
	flash('Successfully logged in!', 'success')
	return redirect(url_for("account"))


@app.route('/logout')
def logout():
	logout_user()
	flash('Successfully logged out!', 'success')
	return redirect(url_for('home'))

@app.route('/account', methods=['GET','POST'])
@login_required
def account():
	if request.method == 'POST':
		set_id = request.form.get('update')
		if set_id is not None:
			#makes the current_set_id to the last existing + 1
			for day in Day.query.filter_by(user_email = current_user.email, set_id=set_id):
				day.update()
		set_id = request.form.get('delete')
		if set_id is not None:
			Day.query.filter_by(user_email = current_user.email, set_id=set_id).delete()
			SiteDescription.query.filter_by(email = current_user.email, set_id=set_id).delete()
			db.session.commit()
				
	return render_template('account.html', SiteDescription=SiteDescription, Day=Day, desc=desc)



@app.route('/result')
def result():
	return render_template('result.html')

