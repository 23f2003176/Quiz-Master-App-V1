from flask import render_template, request, redirect, url_for, flash
from models import (
    Users,
    Quiz,
    Questions,
    Answers,
    QuizAttempts,
    UserResponse,
    UserSessions,
    PasswordResetToken,
    Category,
    QuizCategory,
    UserGroup,
    GroupMember,
    QuizAssignment,
    Feedback,
    UserStatistic,
    Leaderboard,
    LeaderboardEntry,
    Achievement,
    UserAchievement,
    Badge,
    UserBadge,
    ActivityFeed
)
from db_instance import db
from app import app  # Import the app instance from app.py

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login', methods=["POST"])
def login_post():
    
    username = request.form.get('username')
    password = request.form.get('password')
    user = Users.query.filter_by(username=username).first()
    if not user:
        flash("User does not exist, check login details")
        return redirect(url_for('login'))
    if not user.check_password(password):
        flash("Incorrect password")
        return redirect(url_for('login'))
    
    # if all the above checks are passed that means username and password are correct and redirect the user to his page
    return redirect(url_for('index'))

@app.route('/signup')
def signup():
    return render_template('signup.html')


    