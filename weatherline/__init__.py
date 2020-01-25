from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

import requests
import os


app = Flask(__name__)
app.static_folder = 'static'
SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

from weatherline import routes

#guest session
#profile picture
#geocoding (global)
#copyright

#climeline
#temperaline