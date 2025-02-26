from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

# Create an instance of the Flask class for the web application.
# The __name__ parameter helps Flask determine the root path of the application.
# It allows Flask to locate resources such as templates and static files relative to the location of the module.
app = Flask(__name__)

# Create an instance of the SQLAlchemy class for database management.
# Pass the app object to SQLAlchemy to bind it to the Flask application.
db = SQLAlchemy(app)

import config

# Models

class Users(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    username = db.Column(db.String(10), nullable=False)
    name = db.Column(db.String(32), nullable=False)
    passhash = db.Column(db.String(512), nullable=False)

class Subjects(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    subject_name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(100), nullable=True)
    date_created = db.Column(db.Date, nullable=False, default=db.func.current_date())

class Chapters(db.Model):
    __tablename__ = 'chapters'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    chapter_name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(100), nullable=True)
    date_created = db.Column(db.Date, nullable=False, default=db.func.current_date())

class Quiz(db.Model):
    __tablename__ = 'quiz'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.id'), nullable=False)
    quiz_name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(100), nullable=True)
    date_created = db.Column(db.Date, nullable=False, default=db.func.current_date())
    duration = db.Column(db.Time, nullable=False)
    nqs = db.Column(db.Integer, nullable=False)