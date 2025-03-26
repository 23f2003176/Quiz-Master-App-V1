from flask_sqlalchemy import SQLAlchemy
from flask import session
from sqlalchemy.orm import relationship
from sqlalchemy import Text, text
from sqlalchemy import event
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from db_instance import db  # Import the existing db instance

# Models

# Users table 
class Users(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    username = db.Column(db.String(50), nullable=False)
    passhash = db.Column(db.String(512), nullable=False)
    role = db.Column(db.Enum('admin','student', name='user_roles', native_enum=False),
                     nullable=False, default='student')
    full_name = db.Column(db.String(100), default = 'Student')
    qualification = db.Column(db.String(100))
    dob = db.Column(db.Date)  # Date of birth
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)
    is_active = db.Column(db.Boolean, default=True)
    profile_image = db.Column(db.String(255))

    def login(self):
        self.last_login = datetime.now()

        # Set session variables
        session['user_id'] = self.id
        session['username'] = self.username
        session['role'] = self.role

        db.session.commit()

    @property
    def password(self):
        raise AttributeError('Password is not a readable attribute')
    
    @password.setter
    def password(self,password):
        self.passhash = generate_password_hash(password)

    def check_password(self, password):
        if not password or not self.passhash:
            return False
        return check_password_hash(self.passhash, password)

# Event listener to enforce single admin
@event.listens_for(Users, "before_insert")
def check_single_admin(mapper, connection, target):
    """Checks if an admin already exists before inserting a new admin user"""
    if target.role == 'admin':
        # Get current admin count
        admin_count = connection.execute(
            text("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        ).scalar()
        
        # If there's no admin yet, allow creation
        if admin_count == 0:
            return
            
        # If table is empty, allow first admin
        total_users = connection.execute(
            text("SELECT COUNT(*) FROM users")
        ).scalar()
        if total_users == 0:
            return
            
        # Otherwise prevent additional admins
        raise ValueError("Only one admin allowed. The admin is already predefined.")

# Quiz Model
class Quiz(db.Model):
    __tablename__ = 'quiz'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))  # Direct foreign key
    time_limit = db.Column(db.Integer)  # in minutes
    passing_score = db.Column(db.Integer)
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    max_attempts = db.Column(db.Integer, default=1)
    shuffle_questions = db.Column(db.Boolean, default=False)

# Chapter Model
class Chapter(db.Model):
    __tablename__ = 'chapters'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id', ondelete='CASCADE'))
    order = db.Column(db.Integer)  # For chapter ordering
    created_at = db.Column(db.DateTime, default=datetime.now)
    Chapter_image = db.Column(db.String(255))

# Questions Model
class Questions(db.Model):
    __tablename__ = 'questions'
    
    question_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id', ondelete='CASCADE'))
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.id', ondelete='SET NULL'), nullable=True)
    question_text = db.Column(db.Text, nullable=False)
    # Use native_enum=False so that SQLite stores simple string values.
    question_type = db.Column(db.Enum('multiple_choice',name='question_types', native_enum=False),
                              nullable=False)
    points = db.Column(db.Integer, default=1)
    difficulty_level = db.Column(db.Enum('easy', 'medium', 'hard', name='difficulty_levels', native_enum=False),
                                 default='medium')
    media_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now)

# Answers Model
class Answers(db.Model):
    __tablename__ = 'answers'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.question_id', ondelete='CASCADE'))
    answer_text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    explanation = db.Column(db.Text)

# QuizAttempts Model
class QuizAttempts(db.Model):
    __tablename__ = 'quiz_attempts'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    start_time = db.Column(db.DateTime, default=datetime.now)
    end_time = db.Column(db.DateTime)
    score = db.Column(db.Numeric(5, 2))
    is_completed = db.Column(db.Boolean, default=False)
    time_taken = db.Column(db.Integer)  # in seconds
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)

# UserResponse Model
class UserResponse(db.Model):
    __tablename__ = 'user_responses'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.question_id'))
    answer_id = db.Column(db.Integer, db.ForeignKey('answers.id'))
    attempt_id = db.Column(db.Integer, db.ForeignKey('quiz_attempts.id'))
    text_response = db.Column(db.Text)
    is_correct = db.Column(db.Boolean)
    points_earned = db.Column(db.Numeric(5, 2))
    response_time = db.Column(db.Integer)

# UserSessions Model
class UserSessions(db.Model):
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    token = db.Column(db.String(45))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

# Category Model
class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Enum('General Knowledge', 'Science', 'History', 'Geography', 'Mathematics', 'Computer Science', 'Literature', 'Music', 'Movies', 'Sports', 'Art', 'Language', 'Miscellaneous', name='categories', native_enum=False), nullable=False)
    description = db.Column(db.Text)
    max_attempts = db.Column(db.Integer, default=1)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'))

# QuizCategory (Junction) Model
class QuizCategory(db.Model):
    __tablename__ = 'quiz_categories'
    
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), primary_key=True)

# UserStatistic Model
class UserStatistic(db.Model):
    __tablename__ = 'user_statistics'

    stat_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    total_quizzes_taken = db.Column(db.Integer, default=0)
    total_correct_answers = db.Column(db.Integer, default=0)
    total_questions_attempted = db.Column(db.Integer, default=0)
    total_points_earned = db.Column(db.Integer, default=0)
    average_score = db.Column(db.Numeric(5, 2), default=0)
    fastest_completion_time = db.Column(db.Integer) # in seconds
    longest_streak = db.Column(db.Integer, default=0)
    current_streak = db.Column(db.Integer, default=0)
    last_quiz_date = db.Column(db.DateTime)
    rank_points = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.now)

# Define relationships after all models are defined
# User relationships
Users.quizzes_created = db.relationship('Quiz', backref='creator', foreign_keys='Quiz.creator_id', lazy=True)
Users.quiz_attempts = db.relationship('QuizAttempts', backref='user', lazy=True)
Users.sessions = db.relationship('UserSessions', backref='user', lazy=True)
Users.statistics = db.relationship('UserStatistic', uselist=False, backref='user', lazy=True)



# Quiz relationships
Quiz.questions = db.relationship('Questions', backref='quiz', cascade="all, delete-orphan", lazy=True)
Quiz.chapters = db.relationship('Chapter', backref='quiz', lazy=True, order_by='Chapter.order')
Quiz.attempts = db.relationship('QuizAttempts', backref='quiz', lazy=True)
# Fix the problematic relationship - use backref only
Quiz.categories = db.relationship('Category', secondary='quiz_categories', backref=db.backref('quizzes', lazy=True), lazy=True)




# Questions relationships
Questions.answers = db.relationship('Answers', backref='question', cascade="all, delete-orphan", lazy=True)
Questions.user_responses = db.relationship('UserResponse', backref='question', lazy=True)




# Chapter relationships  
Chapter.questions = db.relationship('Questions', backref='chapter', lazy=True)



# Answer relationships
Answers.user_responses = db.relationship('UserResponse', backref='selected_answer', lazy=True)




# QuizAttempts relationships
QuizAttempts.user_responses = db.relationship('UserResponse', backref='attempt', cascade="all, delete-orphan", lazy=True)