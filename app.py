from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import ENUM

# Create an instance of the Flask class for the web application.
# The __name__ parameter helps Flask determine the root path of the application.
# It allows Flask to locate resources such as templates and static files relative to the location of the module.
app = Flask(__name__)


# Set the SQLALCHEMY_DATABASE_URI configuration variable.
# This tells SQLAlchemy where to find the database.
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Create an instance of the SQLAlchemy class for database management.
# Pass the app object to SQLAlchemy to bind it to the Flask application.
db = SQLAlchemy(app)

import config

# Models

# Users table 
class Users(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    name = db.Column(db.String(32), nullable=False)
    username = db.Column(db.String(10), nullable=False)
    email = db.Column(db.varchar(100,unique = True, nullable = False ))
    role = db.Column(ENUM('admin', 'teacher', 'student', name = 'user_roles'), nullable = False, default = 'student')
    created_at = db.Column(db.DateTime, default = db.func.current_timestamp())
    last_login = db.ccolumn(db.Column(db.DateTime))
    is_active = db.Column(db.Boolean, default = True)
    profile_image = db.Column(db.String(255))
    passhash = db.Column(db.String(512), nullable=False)


class Quiz(db.Model):
    __tablename__ = 'quiz'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    title = db.Column(db.Varchar(100), nullable = False)
    description = db.Column(db.Text)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    time_limit = db.Column(db.Integer)
    passing_score = db.Column(db.Integer)
    is_public = db.Column(db.Boolean, default = False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    max_attempts = db.Column(db.Integer, default = 1)
    shuffle_questions = db.Column(db.Boolean, default=False)


class Questions(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('qiz.id', ondelete = 'CASCADE'))
    question_text = db.Column(db.Text, nullable = False)
    question_type = db.Column(ENUM('multiple_choice', 'true_false', 'short_answer','matching',name= 'question_types'),nullable = False)
    difficulty_level = db.Column(ENUM('easy', 'medium', 'hard', name='difficulty_levels'), default='medium')
    media_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Answers(db.Model):
    __tablename__ = 'answers'
    id = db.Column(db.Integer, autoincrement = True, primary_key = True )
    question_id = db.Column(db.Integer, db.Foreignkey('questions.id', ondelete = 'CASCADE'))
    answer_text = db.Column(db.Text, nullable = False)
    is_correct = db.Column(db.Boolean, nullable = False)
    explaination = db.Column(db.Text)

class Quiz_Attempts(db.Model):
    __tablename__ = 'quiz_attempts'
    id = db.Column(db.Integer, autoincrement = True, primary_key = True )
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id') )
    
    

    
    
    
    
    
    

    