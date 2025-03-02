from flask import render_template, request, redirect, url_for, flash, session
import os
from datetime import datetime
from werkzeug.utils import secure_filename
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

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

#-------------
# Home Page
#-------------

@app.route('/')
def index():
    if 'user_id' not in session:
        flash("Login to continue")
        return redirect(url_for('login'))
    return render_template('index.html', user = Users.query.get(session['user_id']))


#-------------
# Profile
#-------------


@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash("Login to continue")
        return redirect(url_for('login'))
    user = Users.query.get(session['user_id'])
    return render_template('profile.html', user=user)

@app.route('/profile/update', methods=['GET','POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = Users.query.get(session['user_id'])
    
    # Update full name if provided
    full_name = request.form.get('full_name', '').strip()
    if full_name:
        user.full_name = full_name
    
    # Update qualification if provided
    qualification = request.form.get('qualification', '').strip()
    if qualification:
        user.qualification = qualification
    
    # Update DOB if provided
    dob = request.form.get('dob')
    if dob:
        try:
            user.dob = datetime.strptime(dob, '%Y-%m-%d')
        except ValueError:
            flash("Invalid date format")
            return redirect(url_for('profile'))
    
    # Handle profile image upload
    if 'profile_image' in request.files:
        file = request.files['profile_image']
        if file and file.filename != '':
            if file.filename.split('.')[-1].lower() in ALLOWED_EXTENSIONS:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                user.profile_image = filename
            else:
                flash("Invalid file type. Allowed types are: png, jpg, jpeg, gif")
                return redirect(url_for('profile'))

    db.session.commit()
    flash("Profile updated successfully!")
    return redirect(url_for('profile'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



#-------------
# Login
#-------------

@app.route('/login')
def login():
    return render_template('login.html') # Handles GET request

@app.route('/login', methods=["POST"])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')

    # Validate input
    if not username or not password:
        flash("Username and password are required")
        return redirect(url_for('login'))

    user = Users.query.filter_by(username=username).first()
    if not user:
        flash("User does not exist, check login details")
        return redirect(url_for('login'))

    if not user.check_password(password):
        flash("Incorrect password")
        return redirect(url_for('login'))

    # Login successful
    user.login()  # This will handle session creation and last_login update
    flash("Login successful!")
    return redirect(url_for('index'))



#-------------
# SIGNUP
#-------------

@app.route('/signup')
def signup():
    return render_template('signup.html')


@app.route('/signup', methods=["POST"])
def signup_post():
    email = request.form.get('email')
    username = request.form.get('username')
    password = request.form.get('password')


    # Check if email is actullay an email
    if not email or not email.strip():
        flash("Email cannot be empty")
        return redirect(url_for('signup'))

    #  Check if user is educated
    if '@' not in email:
        flash("Please enter a valid email address")
        return redirect(url_for('signup'))

    # Check if email already exists
    if Users.query.filter_by(email=email).first():
        flash("Email already registered")
        return redirect(url_for('signup'))

    # checking if username is already taken
    user = Users.query.filter_by(username=username).first()
    if user:
        flash("Username already exists")
        return redirect(url_for('signup'))
    
    if not username.strip() or not password.strip():
        flash("Username or password cannot be empty")
        return redirect(url_for('signup'))

    if len(password) < 8:
        flash("Password must be at least 8 characters long")
        return redirect(url_for('signup'))
    
    # Create new user with email, username and password
    new_user = Users(
        email=email.strip().lower(),
        username=username.strip(),
        password=password  # This will trigger the password.setter
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    flash("User successfully created")
    return redirect(url_for('login'))
    

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))