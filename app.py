from flask import Flask, render_template, request, redirect, url_for, flash
from db_instance import db  # Import the db instance from db_instance.py
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import relationship
from sqlalchemy import Text, text
from sqlalchemy import event
from datetime import datetime

# Create an instance of the Flask class for the web application.
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Set the SQLALCHEMY_DATABASE_URI configuration variable.
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the SQLAlchemy instance with the Flask app.
db.init_app(app)

import config  # bringing the config files
import models  # bringing the models from models.py file

# Ensure models are registered with the db instance
with app.app_context():
    db.create_all()

import routes  # Import routes after db initialization

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

