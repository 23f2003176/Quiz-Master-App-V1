from flask_sqlalchemy import SQLAlchemy
from flask import session
from sqlalchemy.dialects.postgresql import ENUM
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
    
    # Relationships
    quizzes_created = db.relationship('Quiz', backref='quiz_creator', foreign_keys='Quiz.creator_id', lazy=True)
    quiz_attempts = db.relationship('QuizAttempts', backref='attempting_user', lazy=True)
    sessions = db.relationship('UserSessions', backref='session_user', lazy=True)
    reset_tokens = db.relationship('PasswordResetToken', backref='reset_user', lazy=True)
    groups_created = db.relationship('UserGroup', backref='group_creator', lazy=True)
    groups = db.relationship('UserGroup', secondary='group_members', back_populates='members', lazy=True)
    statistics = db.relationship('UserStatistic', uselist=False, backref='statistic_user', cascade="all, delete-orphan", lazy=True)
    achievements = db.relationship('Achievement', secondary='user_achievements', back_populates='users', lazy=True)
    badges = db.relationship('Badge', secondary='user_badges', back_populates='users', lazy=True)
    activities = db.relationship('ActivityFeed', backref='activity_user', lazy=True)
    feedback_given = db.relationship('Feedback', backref='feedback_provider', foreign_keys='Feedback.provided_by', lazy=True)

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
    
    # Relationships
    categories = db.relationship('Category', secondary='quiz_categories',backref=db.backref('quizzes', lazy=True)) 
                               
    questions = db.relationship('Questions', backref='quiz', cascade="all, delete-orphan", lazy=True)



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
    
    
    # Relationship with Quiz
    quiz = db.relationship('Quiz', backref=db.backref('chapters', lazy=True, order_by='Chapter.order'))
    # Relationship with Questions
    questions = db.relationship('Questions', backref='chapter', lazy=True)



# Questions Model
class Questions(db.Model):
    __tablename__ = 'questions'
    
    question_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id', ondelete='CASCADE'))
    question_text = db.Column(db.Text, nullable=False)
    # Use native_enum=False so that SQLite stores simple string values.
    question_type = db.Column(db.Enum('multiple_choice', 'true_false', 'short_answer', 'matching',
                                        name='question_types', native_enum=False),
                              nullable=False)
    points = db.Column(db.Integer, default=1)
    difficulty_level = db.Column(db.Enum('easy', 'medium', 'hard', name='difficulty_levels', native_enum=False),
                                 default='medium')
    media_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    answers = db.relationship('Answers', backref='question', cascade="all, delete-orphan", lazy=True)
    user_responses = db.relationship('UserResponse', backref='question', lazy=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.id', ondelete='SET NULL'), nullable=True)



# Answers Model
class Answers(db.Model):
    __tablename__ = 'answers'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.question_id', ondelete='CASCADE'))
    answer_text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    explanation = db.Column(db.Text)
    
    # Relationships
    user_responses = db.relationship('UserResponse', backref='selected_answer', lazy=True)

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
    
    # Relationships
    user_responses = db.relationship('UserResponse', backref='attempt', cascade="all, delete-orphan", lazy=True)
    feedback = db.relationship('Feedback', backref='attempt', lazy=True)

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

# PasswordResetToken Model
class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    token = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)

# Category Model
class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Enum('General Knowledge', 'Science', 'History', 'Geography', 'Mathematics', 'Computer Science', 'Literature', 'Music', 'Movies', 'Sports', 'Art', 'Language', 'Miscellaneous', name='categories', native_enum=False), nullable=False)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    
    subcategories = db.relationship('Category', backref=db.backref('parent', remote_side=[id]), lazy=True)
    quizzes = db.relationship('Quiz', secondary='quiz_categories', back_populates='categories', lazy=True)

# Add a back_populates relationship for Quiz for categories:
Quiz.categories = db.relationship('Category', secondary='quiz_categories', back_populates='quizzes', lazy=True)

# QuizCategory (Junction) Model
class QuizCategory(db.Model):
    __tablename__ = 'quiz_categories'
    
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), primary_key=True)

# UserGroup Model
class UserGroup(db.Model):
    __tablename__ = 'user_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    members = db.relationship('Users', secondary='group_members', back_populates='groups', lazy=True)
    assignments = db.relationship('QuizAssignment', backref='group', lazy=True)

# GroupMember (Junction) Model
class GroupMember(db.Model):
    __tablename__ = 'group_members'
    
    group_id = db.Column(db.Integer, db.ForeignKey('user_groups.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    joined_at = db.Column(db.DateTime, default=datetime.now)

# QuizAssignment Model
class QuizAssignment(db.Model):
    __tablename__ = 'quiz_assignments'
    
    assignment_id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('user_groups.id'))
    assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    assigned_at = db.Column(db.DateTime, default=datetime.now)
    due_date = db.Column(db.DateTime)
    instructions = db.Column(db.Text)
    
    assigner = db.relationship('Users', foreign_keys=[assigned_by], lazy=True)

# Feedback Model
class Feedback(db.Model):
    __tablename__ = 'feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('quiz_attempts.id'))
    provided_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    feedback_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

# LeaderboardEntry Model
class LeaderboardEntry(db.Model):
    __tablename__ = 'leaderboard_entries'
    
    entry_id = db.Column(db.Integer, primary_key=True)
    leaderboard_id = db.Column(db.Integer, db.ForeignKey('leaderboards.leaderboard_id', ondelete='CASCADE'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    score = db.Column(db.Integer, nullable=False)
    rank = db.Column(db.Integer)
    previous_rank = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # user = db.relationship('Users', backref='leaderboard_entries', lazy=True)

# UserStatistic Model 
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


# Leaderboard Model
class Leaderboard(db.Model):
    __tablename__ = 'leaderboards'
    
    leaderboard_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    type = db.Column(db.Enum('global', 'category', 'quiz', 'group', 'custom',name='leaderboard_types', native_enum=False), nullable=False)
    reference_id = db.Column(db.Integer)  # depends on type
    time_period = db.Column(db.Enum('all_time', 'yearly', 'monthly', 'weekly', 'daily',name='time_periods', native_enum=False), default='all_time')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    reset_frequency = db.Column(db.Enum('never', 'yearly', 'monthly', 'weekly', 'daily',name='reset_frequencies', native_enum=False), default='never')
    last_reset = db.Column(db.DateTime)
    
    entries = db.relationship('LeaderboardEntry', backref='leaderboard', cascade="all, delete-orphan", lazy=True)



# Achievement Model
class Achievement(db.Model):
    __tablename__ = 'achievements'
    
    achievement_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    icon_url = db.Column(db.String(255))
    points = db.Column(db.Integer, default=0)
    requirement_type = db.Column(db.Enum('quiz_count', 'score_threshold', 'streak', 'time_based', 'perfect_score',
                                         'category_mastery', 'custom', name='requirement_types', native_enum=False),nullable=False)
    requirement_value = db.Column(db.Integer)
    is_hidden = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    users = db.relationship('Users', secondary='user_achievements', back_populates='achievements', lazy=True)

# UserAchievement (Junction) Model
class UserAchievement(db.Model):
    __tablename__ = 'user_achievements'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievements.achievement_id'), primary_key=True)
    earned_at = db.Column(db.DateTime, default=datetime.now)
    displayed = db.Column(db.Boolean, default=False)

# Badge Model
class Badge(db.Model):
    __tablename__ = 'badges'
    
    badge_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    icon_url = db.Column(db.String(255), nullable=False)
    level = db.Column(db.Integer, default=1)
    requirement_points = db.Column(db.Integer, nullable=False)
    
    users = db.relationship('Users', secondary='user_badges', back_populates='badges', lazy=True)

# UserBadge (Junction) Model
class UserBadge(db.Model):
    __tablename__ = 'user_badges'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    badge_id = db.Column(db.Integer, db.ForeignKey('badges.badge_id'), primary_key=True)
    awarded_at = db.Column(db.DateTime, default=datetime.now)
    is_displayed = db.Column(db.Boolean, default=True)

# ActivityFeed Model
class ActivityFeed(db.Model):
    __tablename__ = 'activity_feed'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    activity_type = db.Column(db.Enum('quiz_completion', 'achievement_earned', 'rank_change', 'badge_earned',
                                       'streak_milestone', 'perfect_score', name='activity_types', native_enum=False),nullable=False)
    reference_id = db.Column(db.Integer)
    points_earned = db.Column(db.Integer, default=0)
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    is_public = db.Column(db.Boolean, default=True)