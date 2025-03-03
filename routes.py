from flask import render_template, request, redirect, url_for, flash, session
import os
from functools import wraps
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
    ActivityFeed,
)

from db_instance import db
from app import app  # Import the app instance from app.py

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def auth_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Login to continue")
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return decorated_function

def admin_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Login to continue")
            return redirect(url_for('login'))
        
        user = Users.query.get(session['user_id'])
        if user.role != 'admin':
            flash("You do not have permission to view this page")
            return redirect(url_for('index'))
        return func(*args, **kwargs)
    return decorated_function


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
    cnf_password = request.form.get('confirm_password')

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
    
    if cnf_password != password:
        flash("Password does not match")
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
# Home Page
#-------------

@app.route('/')
@auth_required 
def index():
    # if 'user_id' not in session:
    #     flash("Login to continue")    not required as alredy handed by the auth_required
    #     return redirect(url_for('login'))


    # Redirect to admin dashboard if user is admin
    user = Users.query.get(session['user_id'])
    if user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    return render_template('index.html', user = user)


#----------------
# Admin Dashboard
#----------------

@app.route('/admin_dashboard')
@auth_required 
@admin_required
def admin_dashboard():
    student_count = Users.query.filter_by(role='student').count()
    subject_count = Category.query.count()
    quiz_count = Quiz.query.count()
    total_questions = Questions.query.count()  # Renamed to avoid conflict
    quizzes = Quiz.query.order_by(Quiz.created_at.desc()).limit(5).all()
    quiz_question_counts = [Questions.query.filter_by(quiz_id=quiz.id).count() for quiz in quizzes]  # Renamed

    return render_template('admin_dashboard.html',
                         student_count=student_count,
                         subject_count=subject_count,
                         quiz_count=quiz_count,
                         question_count=total_questions,  # For stats card
                         quiz_question_counts=quiz_question_counts,  # For quiz table
                         quizzes=quizzes)

#----------------
# Create Quiz
#----------------
@app.route('/create_quiz', methods=['GET','POST'])
@auth_required 
@admin_required
def create_quiz():
    if request.method == 'POST':
        try:
            # Get form data
            subject_name = request.form.get('name')
            
            # Get existing category or create new one
            category = Category.query.filter_by(name=subject_name).first()
            if not category:
                category = Category(name=subject_name)
                db.session.add(category)
                db.session.flush()

            # Create new quiz
            quiz = Quiz(
                title=request.form.get('title'),
                description=request.form.get('description'),
                creator_id=session['user_id'],
                time_limit=int(request.form.get('time_limit')) if request.form.get('time_limit') else None,
                passing_score=int(request.form.get('passing_score')) if request.form.get('passing_score') else None,
                start_time=datetime.strptime(request.form.get('start_time'), '%Y-%m-%dT%H:%M') if request.form.get('start_time') else None,
                end_time=datetime.strptime(request.form.get('end_time'), '%Y-%m-%dT%H:%M') if request.form.get('end_time') else None,
                max_attempts=int(request.form.get('max_attempts')) if request.form.get('max_attempts') else 1,
                is_public=request.form.get('is_public') == 'on'
            )
            
            # Add category to quiz
            quiz.categories.append(category)
            
            db.session.add(quiz)
            db.session.commit()

            flash('Quiz created successfully!', 'success')
            return redirect(url_for('add_questions', quiz_id=quiz.id))

        except Exception as e:
            db.session.rollback()
            flash('Error creating quiz: ' + str(e), 'danger')
            return redirect(url_for('create_quiz'))

    categories = Category.query.all()
    return render_template('create_quiz.html', categories=categories)

#----------------
# Add Questions
#----------------
@app.route('/add_questions/<int:quiz_id>', methods=['GET','POST'])
@auth_required
@admin_required
def add_questions(quiz_id):
    return render_template('questions.html', quiz_id=quiz_id)

#----------------
# edit Quiz
#----------------
@app.route('/edit_quiz/<int:quiz_id>',methods = ['GET', 'POST'])
@auth_required
@admin_required
def edit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    return render_template('edit_quiz.html', quiz=quiz)



#-------------
# Dashboard
#-------------


@app.route('/dashboard')
@auth_required 
def dashboard():
    # if 'user_id' not in session:
    #     flash("Login to continue")
    #     return redirect(url_for('login'))
    user = Users.query.get(session['user_id'])
    return render_template('dashboard.html', user=user)






#-------------
# Profile
#-------------

@app.route('/profile')
@auth_required 
def profile():
    # if 'user_id' not in session:
    #     flash("Login to continue")
    #     return redirect(url_for('login'))
    user = Users.query.get(session['user_id'])
    return render_template('profile.html', user=user)


@app.route('/profile/update', methods=['GET','POST'])
@auth_required 
def update_profile():
    # if 'user_id' not in session:
    #     return redirect(url_for('login'))
    
    user = Users.query.get(session['user_id'])
    

    # Update password
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if current_password and new_password and confirm_password:
        if not user.check_password(current_password):
            flash('Current password is incorrect', 'danger')
            return redirect(url_for('profile'))
            
        if new_password != confirm_password:
            flash('New passwords do not match', 'danger')
            return redirect(url_for('profile'))
            
        if len(new_password) < 8:
            flash('Password must be at least 8 characters long', 'danger')
            return redirect(url_for('profile'))
            
        user.password = new_password
    

    # Update full name 
    full_name = request.form.get('full_name', '').strip()
    if full_name:
        user.full_name = full_name
    
    # Update qualification 
    qualification = request.form.get('qualification', '').strip()
    if qualification:
        user.qualification = qualification
    
    # Update DOB 
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



    

@app.route('/logout')
@auth_required 
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))