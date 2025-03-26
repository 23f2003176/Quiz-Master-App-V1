from flask import render_template, request, redirect, url_for, flash, session
import os
from datetime import datetime, timedelta
from functools import wraps
from datetime import datetime
from werkzeug.utils import secure_filename
from models import *

from db_instance import db
from app import app  # Import the app instance from app.py

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}



# Make sure thet user object is available in all templates
@app.context_processor
def inject_user():
    """Make current user available to all templates"""
    user = None
    if 'user_id' in session:
        user = Users.query.get(session['user_id'])
    return {'user': user}




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
        if not user:
            flash("User not found", 'danger')
            return redirect(url_for('login'))

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
    user_id = session.get('user_id')
    if not user_id:
        flash('User not logged in', 'danger')
        return redirect(url_for('login'))

    user = Users.query.get(user_id)
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('login'))

    # Redirect to admin dashboard if user is admin
    if user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
        
    ongoing_quizzes = Quiz.query.filter(Quiz.start_time <= datetime.now(), Quiz.end_time >= datetime.now()).all()
    upcoming_quizzes = Quiz.query.filter(Quiz.start_time > datetime.now()).all()

    ongoing_quizzes_chapters = {}
    for quiz in ongoing_quizzes:
        chapters = Chapter.query.filter_by(quiz_id=quiz.id).all()
        ongoing_quizzes_chapters[quiz.id] = chapters

    upcoming_quizzes_chapters = {}
    for quiz in upcoming_quizzes:
        chapters = Chapter.query.filter_by(quiz_id=quiz.id).all()
        upcoming_quizzes_chapters[quiz.id] = chapters

    return render_template('index.html', 
                          user=user,
                          ongoing_quizzes=ongoing_quizzes, 
                          upcoming_quizzes=upcoming_quizzes,
                          ongoing_quizzes_chapters=ongoing_quizzes_chapters,
                          upcoming_quizzes_chapters=upcoming_quizzes_chapters)



#----------------
# Search Quizzes
#----------------
@app.route('/search')
@auth_required
def search_quizzes():
    query = request.args.get('query', '').strip()
    filter_type = request.args.get('filter', 'all')  # Get filter parameter with default 'all'
    
    if not query:
        return redirect(url_for('index'))
        
    # Search in quiz titles and descriptions
    quizzes = Quiz.query.filter(
        db.or_(
            Quiz.title.ilike(f'%{query}%'),
            Quiz.description.ilike(f'%{query}%')
        )
    ).all()
    
    # Also search in chapter titles
    chapter_matches = Chapter.query.filter(Chapter.title.ilike(f'%{query}%')).all()
    
    # Get quizzes from chapter matches and add them to results if not already included
    chapter_quiz_ids = set(chapter.quiz_id for chapter in chapter_matches)
    quiz_ids = set(quiz.id for quiz in quizzes)
    additional_quiz_ids = chapter_quiz_ids - quiz_ids
    
    additional_quizzes = Quiz.query.filter(Quiz.id.in_(additional_quiz_ids)).all() if additional_quiz_ids else []
    
    all_quizzes = quizzes + additional_quizzes
    
    # Get chapters for each quiz
    quiz_chapters = {}
    for quiz in all_quizzes:
        chapters = Chapter.query.filter_by(quiz_id=quiz.id).all()
        quiz_chapters[quiz.id] = chapters

    # Organize quizzes into categories (ongoing, upcoming, past)
    now = datetime.now()
    ongoing_quizzes = []
    upcoming_quizzes = []
    past_quizzes = []
    
    for quiz in all_quizzes:
        if quiz.start_time and quiz.end_time:  # Check if dates exist
            if quiz.start_time <= now and quiz.end_time >= now:
                ongoing_quizzes.append(quiz)
            elif quiz.start_time > now:
                upcoming_quizzes.append(quiz)
            else:
                past_quizzes.append(quiz)
        else:
            # Handle quizzes with missing dates - consider as ongoing by default
            ongoing_quizzes.append(quiz)
    
    # Calculate the total result count based on the filter
    if filter_type == 'ongoing':
        filtered_count = len(ongoing_quizzes)
    elif filter_type == 'upcoming':
        filtered_count = len(upcoming_quizzes)
    elif filter_type == 'past':
        filtered_count = len(past_quizzes)
    else:  # 'all' or any other value
        filtered_count = len(all_quizzes)
    
    user = Users.query.get(session['user_id'])
    return render_template('search_results.html', 
                          user=user,
                          ongoing_quizzes=ongoing_quizzes,
                          upcoming_quizzes=upcoming_quizzes,
                          past_quizzes=past_quizzes,
                          quiz_chapters=quiz_chapters,
                          query=query,
                          filter=filter_type,  # Pass the filter parameter to the template
                          result_count=len(all_quizzes),
                          filtered_count=filtered_count)  # Pass filtered count for display




#---------------------------
# Search Students for admin
#---------------------------
@app.route('/search_students')
@auth_required
@admin_required
def search_students():
    query = request.args.get('query', '').strip()
    if not query:
        return redirect(url_for('admin_dashboard'))
    
    # Search for students by username, email or full name
    students = Users.query.filter(
        Users.role == 'student',
        db.or_(
            Users.username.ilike(f'%{query}%'),
            Users.email.ilike(f'%{query}%'),
            Users.full_name.ilike(f'%{query}%')
        )
    ).all()
    
    # Get statistics for each student
    for student in students:
        # Attach user statistics if available
        student.stats = UserStatistic.query.filter_by(user_id=student.id).first()
        
        # Get total completed quizzes
        student.completed_quizzes = QuizAttempts.query.filter_by(
            user_id=student.id,
            is_completed=True
        ).count()
        
        # Calculate average score
        completed_attempts = QuizAttempts.query.filter(
            QuizAttempts.user_id == student.id,
            QuizAttempts.score.isnot(None)
        ).all()
        
        if completed_attempts:
            student.avg_score = sum(float(a.score) for a in completed_attempts) / len(completed_attempts)
        else:
            student.avg_score = 0
    
    user = Users.query.get(session['user_id'])  # Admin user for navbar
    return render_template('search_students.html', 
                          user=user,
                          students=students, 
                          query=query,
                          result_count=len(students))







#-------------------------
# Student Quiz Details
#-------------------------

@app.route('/quiz_details/<int:quiz_id>')
@auth_required
def student_quiz_details(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    chapters = Chapter.query.filter_by(quiz_id=quiz_id).all()
    questions = Questions.query.filter_by(quiz_id=quiz_id).all()
    
    # Get user's attempts for this quiz
    user = Users.query.get(session['user_id'])
    attempts = QuizAttempts.query.filter_by(user_id=user.id, quiz_id=quiz_id).all()
    
    # Get user's best attempt - handle None scores properly
    best_attempt = None
    if attempts:
        # Filter out attempts with None scores before finding max
        valid_attempts = [a for a in attempts if a.score is not None]
        if valid_attempts:
            best_attempt = max(valid_attempts, key=lambda a: a.score)
    
    # Calculate max attempts from categories
    max_attempts = 0
    for category in quiz.categories:
        if category.max_attempts and category.max_attempts > max_attempts:
            max_attempts = category.max_attempts
    
    return render_template('student_quiz_details.html', 
                          quiz=quiz,
                          chapters=chapters,
                          questions=questions,
                          attempts=attempts,
                          best_attempt=best_attempt,
                          max_attempts=max_attempts) 


#----------------
# Start Quiz
#----------------
@app.route('/start_quiz/<int:quiz_id>', methods=['GET', 'POST'])
@app.route('/start_quiz/<int:quiz_id>/<int:chapter_id>', methods=['GET', 'POST'])
@auth_required
def start_quiz(quiz_id, chapter_id=None):
    # Get quiz and verify it exists
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Get all chapters for this quiz
    chapters = Chapter.query.filter_by(quiz_id=quiz_id).all()
    
    # Handle chapter selection
    current_chapter = None
    if chapter_id:
        # If chapter_id is specified in URL, use that chapter
        current_chapter = Chapter.query.get_or_404(chapter_id)
        questions = Questions.query.filter_by(quiz_id=quiz_id, chapter_id=chapter_id).all()
    else:
        # If no chapter_id specified, use the first chapter if available
        if chapters:
            current_chapter = chapters[0]
            questions = Questions.query.filter_by(quiz_id=quiz_id, chapter_id=current_chapter.id).all()
        else:
            # If no chapters exist, get all questions
            questions = Questions.query.filter_by(quiz_id=quiz_id).all()
    
    # Make sure we have questions
    if not questions:
        flash('This quiz does not have any questions yet.', 'warning')
        return redirect(url_for('student_quiz_details', quiz_id=quiz_id))
    
    # Check attempt limits for THIS SPECIFIC QUIZ only
    try:
        user_id = session['user_id']
        
        # Count attempts for THIS quiz only
        user_quiz_attempts = QuizAttempts.query.filter_by(
            quiz_id=quiz_id,
            user_id=user_id,
            is_completed=True
        ).count()
        
        # Get max attempts from quiz or use default
        quiz_max_attempts = quiz.max_attempts if quiz.max_attempts else 1
        
        # Check if user has reached max attempts for this quiz
        if user_quiz_attempts >= quiz_max_attempts:
            flash(f'You have reached the maximum number of attempts ({quiz_max_attempts}) for this quiz.', 'warning')
            return redirect(url_for('student_quiz_details', quiz_id=quiz_id))
        
    except Exception as e:
        print(f"Error checking quiz attempt limits: {e}")
    
    # Create a consistent session key for this quiz
    quiz_session_key = f'quiz_{quiz_id}_session'
    
    # Initialize quiz session if needed
    if quiz_session_key not in session:
        # Create a new quiz attempt
        quiz_attempt = QuizAttempts(
            quiz_id=quiz_id,
            user_id=session['user_id'],
            start_time=datetime.now(),
            is_completed=False
        )
        db.session.add(quiz_attempt)
        db.session.commit()
        
        # Initialize session with basic data - ALWAYS start at question 0
        session[quiz_session_key] = {
            'attempt_id': quiz_attempt.id,
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'current_question': 0,  # Always start at the first question
            'visited_questions': [],
            'answered_questions': [],
            'user_answers': {}
        }
        session.modified = True
    
    # Get the current quiz session
    quiz_session = session.get(quiz_session_key, {})
    current_idx = int(quiz_session.get('current_question', 0))  # Ensure this is an integer
    
    # Handle POST requests (form submissions)
    if request.method == 'POST':
        question_id = request.form.get('question_id')
        action = request.form.get('action', '')
        
        # Process the user's answers
        if question_id:
            # Mark question as visited
            visited = quiz_session.get('visited_questions', [])
            if int(question_id) not in visited:
                visited.append(int(question_id))
                quiz_session['visited_questions'] = visited
            
            # Handle answer submission
            answer_values = request.form.getlist('answer')
            if answer_values:
                # Convert to string keys for JSON serialization in session
                question_id_str = str(question_id)
                user_answers = quiz_session.get('user_answers', {})
                user_answers[question_id_str] = answer_values
                quiz_session['user_answers'] = user_answers
                
                answered = quiz_session.get('answered_questions', [])
                if int(question_id) not in answered:
                    answered.append(int(question_id))
                    quiz_session['answered_questions'] = answered
            
            # Handle specific actions
            if action == 'clear':
                # Clear the answer for this question
                if 'user_answers' in quiz_session and str(question_id) in quiz_session['user_answers']:
                    del quiz_session['user_answers'][str(question_id)]
                
                if 'answered_questions' in quiz_session and int(question_id) in quiz_session['answered_questions']:
                    quiz_session['answered_questions'].remove(int(question_id))
                
            elif action == 'next' and current_idx < len(questions) - 1:
                # Move to next question
                quiz_session['current_question'] = current_idx + 1
                print(f"Moving to next question: {current_idx + 1}")
                
            elif action == 'prev' and current_idx > 0:
                # Move to previous question
                quiz_session['current_question'] = current_idx - 1
                print(f"Moving to previous question: {current_idx - 1}")
                
            elif action == 'submit':
                # Process submission and save all answers to database
                attempt_id = quiz_session.get('attempt_id')
                
                # Get the attempt from database
                attempt = QuizAttempts.query.get(attempt_id)
                
                # If attempt doesn't exist, create a new one
                if attempt is None:
                    start_time = datetime.strptime(quiz_session.get('start_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')), '%Y-%m-%d %H:%M:%S')
                    attempt = QuizAttempts(
                        quiz_id=quiz_id,
                        user_id=session['user_id'],
                        start_time=start_time,
                        is_completed=False
                    )
                    db.session.add(attempt)
                    db.session.commit()
                    quiz_session['attempt_id'] = attempt.id
                
                # Save answers to database
                user_answers = quiz_session.get('user_answers', {})
                for q_id_str, answers in user_answers.items():
                    q_id = int(q_id_str)
                    question = Questions.query.get(q_id)
                    if not question:
                        continue
                    
                    # Handle different question types
                    if question.question_type == 'multiple_choice':
                        for answer_id in answers:
                            answer = Answers.query.get(int(answer_id))
                            if answer:
                                # Create user response record
                                response = UserResponse(
                                    question_id=q_id,
                                    answer_id=int(answer_id),
                                    attempt_id=attempt.id,
                                    is_correct=answer.is_correct,
                                    points_earned=question.points if answer.is_correct else 0
                                )
                                db.session.add(response)
                
                # Update attempt status
                attempt.end_time = datetime.now()
                attempt.is_completed = True
                
                # Calculate time taken
                if attempt.start_time:
                    attempt.time_taken = int((attempt.end_time - attempt.start_time).total_seconds())
                
                # Calculate score
                total_points = sum(q.points for q in questions if q.points) or 1
                correct_responses = UserResponse.query.filter_by(
                    attempt_id=attempt.id, is_correct=True
                ).all()
                earned_points = sum(float(r.points_earned or 0) for r in correct_responses)
                attempt.score = (earned_points / total_points) * 100
                
                db.session.commit()
                
                # Clean up session
                if quiz_session_key in session:
                    del session[quiz_session_key]
                    session.modified = True
                
                flash('Quiz completed successfully!', 'success')
                return redirect(url_for('student_quiz_details', quiz_id=quiz_id))
        
        # Save session changes
        session[quiz_session_key] = quiz_session
        session.modified = True
        
        # Redirect to maintain form state
        if chapter_id:
            return redirect(url_for('start_quiz', quiz_id=quiz_id, chapter_id=chapter_id))
        else:
            return redirect(url_for('start_quiz', quiz_id=quiz_id))
    
    # For GET requests: Prepare data for rendering
    if questions:
        # Make sure current_idx is in bounds
        if current_idx >= len(questions):
            current_idx = 0
            quiz_session['current_question'] = 0
            session[quiz_session_key] = quiz_session
            session.modified = True
        
        current_question = questions[current_idx]
        answers = Answers.query.filter_by(question_id=current_question.question_id).all()
    else:
        current_question = None
        answers = []
    
    # Calculate time remaining
    time_remaining = None
    if quiz.time_limit and 'start_time' in quiz_session:
        try:
            start_time = datetime.strptime(quiz_session.get('start_time'), '%Y-%m-%d %H:%M:%S')
            elapsed_seconds = (datetime.now() - start_time).total_seconds()
            time_limit_seconds = quiz.time_limit * 60
            remaining_seconds = max(0, time_limit_seconds - elapsed_seconds)
            
            # Format time for display
            hours = int(remaining_seconds // 3600)
            minutes = int((remaining_seconds % 3600) // 60)
            seconds = int(remaining_seconds % 60)
            time_remaining = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        except Exception as e:
            print(f"Error calculating time: {e}")
    
    # Return the template with all required data
    return render_template('start_quiz.html', 
                          quiz=quiz,
                          current_chapter=current_chapter,
                          chapters=chapters,
                          questions=questions,
                          answers=answers,
                          current_question=current_idx,
                          current_question_data=current_question,
                          visited_questions=quiz_session.get('visited_questions', []),
                          answered_questions=quiz_session.get('answered_questions', []),
                          user_answers=quiz_session.get('user_answers', {}),
                          time_remaining=time_remaining)


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
            return redirect(url_for('edit_quiz', quiz_id=quiz.id))

        except Exception as e:
            db.session.rollback()
            flash('Error creating quiz: ' + str(e), 'danger')
            return redirect(url_for('create_quiz'))

    categories = Category.query.all()
    return render_template('create_quiz.html', categories=categories)



#----------------
# view Quiz
#----------------
@app.route('/view_quiz/<int:quiz_id>')
@auth_required
def view_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    return render_template('view_quiz.html', quiz=quiz)

#----------------
# edit Quiz
#----------------
@app.route('/edit_quiz/<int:quiz_id>', methods=['GET', 'POST'])
@auth_required
@admin_required
def edit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    chapter_id = request.args.get('chapter_id', type=int)
    if request.method == 'POST':
        try:
            chapter_title = request.form.get('title')
            chapter_description = request.form.get('description')
            
            
            chapter_image = None
            if 'chapter_image' in request.files:
                file = request.files['chapter_image']
                if file and file.filename != '':
                    if file.filename.split('.')[-1].lower() in ALLOWED_EXTENSIONS:
                        filename = secure_filename(file.filename)
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        chapter_image = filename
                    else:
                        flash('Invalid file type. Allowed types are: png, jpg, jpeg, gif', 'danger')
                        return redirect(url_for('edit_quiz', quiz_id=quiz_id))


            # Create new chapter
            new_chapter = Chapter(
                title=chapter_title,
                description=chapter_description,
                quiz_id=quiz_id,
                Chapter_image=chapter_image
            )
            
            db.session.add(new_chapter)
            db.session.commit()
            
            flash('Chapter added successfully!', 'success')
            return redirect(url_for('edit_quiz', quiz_id=quiz_id))
            
        except Exception as e:
            db.session.rollback()
            flash('Error adding chapter: ' + str(e), 'danger')
            return redirect(url_for('edit_quiz', quiz_id=quiz_id))
    
    return render_template('edit_quiz.html', quiz=quiz)
    


#----------------
# delete chapters
#----------------
@app.route('/delete_chapter/<int:quiz_id>/<int:chapter_id>', methods=['POST'])
@auth_required
@admin_required
def delete_chapter(quiz_id, chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)

    # Verify chapter belongs to quiz
    if chapter.quiz_id != quiz_id:
        flash('Chapter does not belong to this quiz', 'danger')
        return redirect(url_for('edit_quiz', quiz_id=quiz_id))

    # Manual deletion of related records to ensure they're removed
    questions = Questions.query.filter_by(chapter_id=chapter_id).all()

    for question in questions:
        # Delete all answers for this question
        Answers.query.filter_by(question_id=question.question_id).delete()

    # Delete all questions for this chapter
    Questions.query.filter_by(chapter_id=chapter_id).delete()

    # Delete chapter image if it exists
    if chapter.Chapter_image:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], chapter.Chapter_image)
        if os.path.exists(image_path):
            os.remove(image_path)

    # Delete the chapter
    db.session.delete(chapter)
    db.session.commit()

    flash('Chapter deleted successfully!', 'success')
    return redirect(url_for('edit_quiz', quiz_id=quiz_id))





#----------------
# Add Questions
#----------------
@app.route('/add_questions/<int:quiz_id>/<int:chapter_id>', methods=['GET', 'POST'])
@auth_required
@admin_required
def add_questions(quiz_id, chapter_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    chapter = Chapter.query.get_or_404(chapter_id)
    
    if request.method == 'POST':
        # Check if this is a "set number of questions" request
        if 'num_questions' in request.form and not any(key.endswith('[text]') for key in request.form.keys()):
            num_questions = int(request.form.get('num_questions', 1))
            return render_template('questions.html', quiz=quiz, chapter=chapter, num_questions=num_questions)
        
        try:
            form_data = request.form
            files = request.files
            num_questions = len([k for k in form_data.keys() if k.endswith('[text]')])
            
            for i in range(num_questions):
                # Handle media upload
                media_url = None
                if f'questions[{i}][question_image]' in files:
                    file = files[f'questions[{i}][question_image]']
                    if file and file.filename != '':
                        if file.filename.split('.')[-1].lower() in ALLOWED_EXTENSIONS:
                            filename = secure_filename(file.filename)
                            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                            media_url = filename
                
                # Create question using media_url field
                question = Questions(
                    quiz_id=quiz_id,
                    chapter_id=chapter_id,
                    question_text=form_data[f'questions[{i}][text]'],
                    media_url=media_url,
                    question_type='multiple_choice'
                )
                db.session.add(question)
                db.session.flush()
                
                # Add options
                for j in range(1, 5):
                    option = form_data[f'questions[{i}][option{j}]']
                    is_correct = form_data[f'questions[{i}][correct_option]'] == str(j)
                    answer = Answers(
                        question_id=question.question_id,
                        answer_text=option,
                        is_correct=is_correct
                    )
                    db.session.add(answer)
            
            db.session.commit()
            flash('Questions added successfully!', 'success')
            return redirect(url_for('edit_quiz', quiz_id=quiz_id))
            
        except Exception as e:
            db.session.rollback()
            flash('Error adding questions: ' + str(e), 'danger')
            return redirect(url_for('edit_quiz', quiz_id=quiz_id))
    
    # Important: Pass chapter to the template
    return render_template('questions.html', quiz=quiz, chapter=chapter, num_questions=1)


#----------------
# delete Question
#----------------
@app.route('/delete_question/<int:quiz_id>/<int:question_id>', methods=['POST'])
@auth_required
@admin_required
def delete_question(quiz_id, question_id):
    # Get the question and verify it exists
    question = Questions.query.get_or_404(question_id)
    
    
    if question.quiz_id != quiz_id:
        flash('Question does not belong to this quiz', 'danger')
        return redirect(url_for('view_quiz', quiz_id=quiz_id))
    
    # Remember the chapter ID for redirection
    chapter_id = question.chapter_id
    
    
    if question.media_url:
        try:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], question.media_url)
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception as e:
            # some bug here
            print(f"Error deleting question image: {e}")
    
    
    Answers.query.filter_by(question_id=question_id).delete()
    
    # Delete the question
    db.session.delete(question)
    db.session.commit()
    
    flash('Question deleted successfully!', 'success')
    return redirect(url_for('view_quiz', quiz_id=quiz_id))





#----------------
# delete Quiz
#----------------
@app.route('/delete_quiz/<int:quiz_id>', methods=['POST'])
@auth_required
@admin_required
def delete_quiz(quiz_id):
    try:
        quiz = Quiz.query.get_or_404(quiz_id)
        
        db.session.delete(quiz)
        db.session.commit()
        flash('Quiz deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error deleting quiz: ' + str(e), 'danger')
    
    return redirect(url_for('admin_dashboard'))





#-------------
# Dashboard
#-------------

@app.route('/dashboard')
@auth_required
def dashboard():
    # Get user
    user = Users.query.get(session['user_id'])
    
    # Statistics
    statistics = {
        'total_quizzes_taken': 0,
        'average_score': 0,
        'current_streak': 0,
        'total_questions_attempted': 0,
        'total_correct_answers': 0,
        'total_points_earned': 0
    }
    
    # Get user statistics
    user_statistic = UserStatistic.query.filter_by(user_id=user.id).first()
    if user_statistic:
        statistics = {
            'total_quizzes_taken': user_statistic.total_quizzes_taken,
            'average_score': user_statistic.average_score,
            'current_streak': user_statistic.current_streak,
            'total_questions_attempted': user_statistic.total_questions_attempted,
            'total_correct_answers': user_statistic.total_correct_answers
        }
    
    # Get all completed quiz attempts for charts
    completed_attempts = QuizAttempts.query.filter_by(
        user_id=user.id, 
        is_completed=True
    ).order_by(QuizAttempts.start_time).all()
    
    # Get recent attempts (latest 5)
    recent_attempts = QuizAttempts.query.filter_by(
        user_id=user.id
    ).order_by(QuizAttempts.start_time.desc()).limit(5).all()
    
    # Add quiz titles to attempts
    for attempt in recent_attempts:
        quiz = Quiz.query.get(attempt.quiz_id)
        attempt.quiz_title = quiz.title if quiz else f"Quiz #{attempt.quiz_id}"
    
    # --------- SUBJECT-WISE PERFORMANCE DATA ---------
    
    # Get time range for chart (last 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Group attempts by date and subject
    subject_performance = {}
    date_labels = []
    
    # Loop through each attempt
    for attempt in completed_attempts:
        if attempt.score is None or attempt.start_time < start_date:
            continue
            
        # Get quiz categories
        quiz = Quiz.query.get(attempt.quiz_id)
        if not quiz:
            continue
            
        # Format date for grouping (YYYY-MM-DD)
        attempt_date = attempt.start_time.strftime('%Y-%m-%d')
        
        # Track unique dates for x-axis labels
        if attempt_date not in date_labels:
            date_labels.append(attempt_date)
            
        # Group by category
        for category in quiz.categories:
            if category.name not in subject_performance:
                subject_performance[category.name] = {}
                
            if attempt_date not in subject_performance[category.name]:
                subject_performance[category.name][attempt_date] = []
                
            subject_performance[category.name][attempt_date].append(attempt.score)
    
    # Sort dates chronologically
    date_labels.sort()
    
    # Format dates for display (Apr 15, etc.)
    formatted_dates = [datetime.strptime(d, '%Y-%m-%d').strftime('%b %d') for d in date_labels]
    
    # Calculate average score per subject per day
    subject_datasets = []
    all_subjects = list(subject_performance.keys())
    
    # Colors for subjects (can be extended for more subjects)
    colors = [
        {'bg': 'rgba(54, 162, 235, 0.2)', 'border': 'rgba(54, 162, 235, 1)'},
        {'bg': 'rgba(255, 99, 132, 0.2)', 'border': 'rgba(255, 99, 132, 1)'},
        {'bg': 'rgba(75, 192, 192, 0.2)', 'border': 'rgba(75, 192, 192, 1)'},
        {'bg': 'rgba(255, 159, 64, 0.2)', 'border': 'rgba(255, 159, 64, 1)'},
        {'bg': 'rgba(153, 102, 255, 0.2)', 'border': 'rgba(153, 102, 255, 1)'}
    ]
    
    # Create dataset for each subject
    for i, subject in enumerate(all_subjects):
        color_index = i % len(colors)
        
        data_points = []
        for date in date_labels:
            if date in subject_performance[subject]:
                avg_score = sum(subject_performance[subject][date]) / len(subject_performance[subject][date])
                data_points.append(round(avg_score, 1))
            else:
                data_points.append(None)  # No data for this date
        
        subject_datasets.append({
            'label': subject,
            'data': data_points,
            'fill': False,
            'backgroundColor': colors[color_index]['bg'],
            'borderColor': colors[color_index]['border'],
            'tension': 0.1
        })
    
    # Score distribution (for pie chart - unchanged)
    score_distribution = {
        'excellent': 0,
        'good': 0,
        'average': 0,
        'poor': 0,
        'total': 0
    }
    
    for attempt in completed_attempts:
        if attempt.score is not None:
            score_distribution['total'] += 1
            if attempt.score >= 90:
                score_distribution['excellent'] += 1
            elif attempt.score >= 75:
                score_distribution['good'] += 1
            elif attempt.score >= 60:
                score_distribution['average'] += 1
            else:
                score_distribution['poor'] += 1
    
    # Subject overall performance (for radar chart)
    subject_names = []
    subject_scores = []
    
    # Get scores by category/subject
    categories = Category.query.all()
    for category in categories:
        # Find quizzes with this category
        quiz_ids = db.session.query(QuizCategory.quiz_id).filter_by(category_id=category.id).all()
        quiz_ids = [q[0] for q in quiz_ids]
        
        if not quiz_ids:
            continue
            
        # Find attempts for these quizzes
        subject_attempts = QuizAttempts.query.filter(
            QuizAttempts.user_id == user.id,
            QuizAttempts.quiz_id.in_(quiz_ids),
            QuizAttempts.score.isnot(None)
        ).all()
        
        if subject_attempts:
            avg_score = sum(a.score for a in subject_attempts) / len(subject_attempts)
            subject_names.append(category.name)
            subject_scores.append(round(avg_score, 1))
    
    return render_template('dashboard.html', 
                          user=user, 
                          statistics=statistics,
                          recent_attempts=recent_attempts,
                          date_labels=formatted_dates,  # Changed from quiz_labels
                          subject_datasets=subject_datasets,  # Changed from quiz_scores
                          score_distribution=score_distribution,
                          subject_names=subject_names,
                          subject_scores=subject_scores)






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



#-------------
# Profile Update
#-------------
@app.route('/profile/update', methods=['GET', 'POST'])
@auth_required 
def update_profile():
    if request.method != 'POST':
        return redirect(url_for('profile'))
        
    user = Users.query.get(session['user_id'])
    password_update = False
    profile_update = False
    
    # Check if this is a password update request
    if 'update_password' in request.form:
        password_update = True
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate password fields
        if not current_password or not new_password or not confirm_password:
            flash('All password fields are required for password update', 'warning')
            return redirect(url_for('profile'))
            
        # Verify current password
        if not user.check_password(current_password):
            flash('Current password is incorrect', 'danger')
            return redirect(url_for('profile'))
            
        # Validate new password
        if new_password != confirm_password:
            flash('New passwords do not match', 'danger')
            return redirect(url_for('profile'))
            
        if len(new_password) < 8:
            flash('Password must be at least 8 characters long', 'danger')
            return redirect(url_for('profile'))
            
        user.password = new_password
        flash('Password updated successfully', 'success')
    
    # Process profile updates (separate from password)
    else:
        # Update basic profile information
        full_name = request.form.get('full_name', '').strip()
        if full_name:
            user.full_name = full_name
            profile_update = True
        
        # Update qualification 
        qualification = request.form.get('qualification', '').strip()
        if qualification:
            user.qualification = qualification
            profile_update = True
        
        # Update DOB 
        dob = request.form.get('dob')
        if dob:
            try:
                user.dob = datetime.strptime(dob, '%Y-%m-%d')
                profile_update = True
            except ValueError:
                flash("Invalid date format", 'danger')
                return redirect(url_for('profile'))
        
        # Handle profile image upload
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and file.filename != '':
                if file.filename.split('.')[-1].lower() in ALLOWED_EXTENSIONS:
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    user.profile_image = filename
                    flash("Profile image updated successfully", 'success')
                    profile_update = True
                else:
                    flash("Invalid file type. Allowed types are: png, jpg, jpeg, gif", 'danger')
                    return redirect(url_for('profile'))

        # Show success message for profile updates
        if profile_update:
            flash("Profile updated successfully!", 'success')
    
    # Save changes to database
    db.session.commit()
    return redirect(url_for('profile'))






def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



    

@app.route('/logout')
@auth_required 
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))