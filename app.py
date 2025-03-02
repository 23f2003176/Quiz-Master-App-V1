from flask import Flask, render_template, request, redirect, url_for, flash
from db_instance import db  # Import the db instance from db_instance.py
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import relationship
from sqlalchemy import Text, text
import os
from sqlalchemy import event
from datetime import datetime
from dotenv import load_dotenv

# Create an instance of the Flask class for the web application.
app = Flask(__name__)
app.config['SESSION_PERMANENT'] = False  # Session expires when browser closes


# Load environment variables
load_dotenv()

# File upload configurations
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Set the SQLALCHEMY_DATABASE_URI configuration variable.
DB_PATH = 'db.sqlite3'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the SQLAlchemy instance with the Flask app.
db.init_app(app)

import config  # bringing the config files
import models  # bringing the models from models.py file

# Delete existing database if it exists
def reset_database():
    db_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_PATH)

    # Close any existing connections
    db.session.remove()
    db.engine.dispose()

    if os.path.exists(db_file):
        os.remove(db_file)

    #create new db
    db.create_all()

    #Creating admin
    try:
        # Check if admin exists
        admin = models.Users.query.filter_by(role='admin').first()
        if not admin:
            # Create admin user
            admin = models.Users(
                username='admin',
                password='admin123',
                email='admin@kuizu.com',
                role='admin',
                full_name='Administrator'
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully")
    except Exception as e:
        db.session.rollback()
        print(f"Error creating admin: {str(e)}")
        raise

with app.app_context():
    reset_database() # will call the reset function
    

import routes  # Import routes after db initialization

# Add after existing configurations
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

