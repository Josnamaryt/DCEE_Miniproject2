from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_file
from flask_login import login_user, logout_user, login_required, current_user
# from app import login_manager
from app import mongo
from datetime import datetime
from bson import ObjectId
import pandas as pd
from io import BytesIO
from openpyxl import Workbook

instructor_bp = Blueprint('instructor', __name__)

@instructor_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    user_name = f"{current_user.first_name} {current_user.last_name}"
    return render_template('instructor/dashboard.html', user_name=user_name)

@instructor_bp.route('/get_profile')
def get_profile():
    try:
        return jsonify({
            'success': True,
            'data': {
                'name': f"{current_user.first_name} {current_user.last_name}",
                'email': current_user.email
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@instructor_bp.route('/check_course_name', methods=['POST'])
@login_required
def check_course_name():
    try:
        data = request.json
        course_name = data.get('name')
        
        # Check if course already exists (case-insensitive)
        existing_course = mongo.db.courses.find_one({
            'name': {'$regex': f'^{course_name}$', '$options': 'i'}
        })
        
        return jsonify({
            'success': True,
            'exists': existing_course is not None
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@instructor_bp.route('/add_course', methods=['POST'])
@login_required
def add_course():
    try:
        data = request.json
        
        # Check if course already exists
        existing_course = mongo.db.courses.find_one({
            'name': {'$regex': f'^{data["name"]}$', '$options': 'i'}
        })
        
        if existing_course:
            return jsonify({
                'success': False,
                'message': 'A course with this name already exists'
            })
        
        course = {
            'name': data['name'],
            'description': data['description'],
            'level': data['level'],
            'duration': data['duration'],
            'course_link': data['course_link'],
            'status': data['status'],
            'instructor_id': str(current_user.id),
            'instructor_email': current_user.email,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Insert into MongoDB
        mongo.db.courses.insert_one(course)
        
        return jsonify({
            'success': True,
            'message': 'Course added successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@instructor_bp.route('/get_courses')
@login_required
def get_courses():
    try:
        # Fetch courses for the current instructor
        courses = list(mongo.db.courses.find({'instructor_email': current_user.email}))
        
        # Convert ObjectId to string for JSON serialization
        for course in courses:
            course['_id'] = str(course['_id'])
            course['created_at'] = course['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            course['updated_at'] = course['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({
            'success': True,
            'data': courses
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@instructor_bp.route('/add_announcement', methods=['POST'])
@login_required
def add_announcement():
    try:
        data = request.json
        course = mongo.db.courses.find_one({'_id': ObjectId(data['course_id'])})
        
        announcement = {
            'course_id': ObjectId(data['course_id']),
            'course_name': course['name'],
            'instructor_id': current_user.id,
            'instructor_name': f"{current_user.first_name} {current_user.last_name}",
            'title': data['title'],
            'message': data['message'],
            'created_at': datetime.utcnow()
        }
        
        mongo.db.announcements.insert_one(announcement)
        
        return jsonify({
            'success': True,
            'message': 'Announcement added successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@instructor_bp.route('/get_announcements')
@login_required
def get_announcements():
    try:
        announcements = list(mongo.db.announcements.find({
            'instructor_id': current_user.id
        }).sort('created_at', -1))
        
        for announcement in announcements:
            announcement['_id'] = str(announcement['_id'])
            announcement['course_id'] = str(announcement['course_id'])
            announcement['created_at'] = announcement['created_at'].isoformat()
        
        return jsonify({
            'success': True,
            'data': announcements
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@instructor_bp.route('/announcement/<announcement_id>', methods=['DELETE'])
@login_required
def delete_announcement(announcement_id):
    try:
        result = mongo.db.announcements.delete_one({
            '_id': ObjectId(announcement_id),
            'instructor_id': current_user.id
        })
        
        if result.deleted_count:
            return jsonify({
                'success': True,
                'message': 'Announcement deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Announcement not found'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@instructor_bp.route('/add_quiz', methods=['POST'])
@login_required
def add_quiz():
    try:
        data = request.json
        course = mongo.db.courses.find_one({'_id': ObjectId(data['course_id'])})
        
        quiz = {
            'course_id': ObjectId(data['course_id']),
            'course_name': course['name'],
            'instructor_id': current_user.id,
            'instructor_name': f"{current_user.first_name} {current_user.last_name}",
            'title': data['title'],
            'description': data['description'],
            'questions': data['questions'],
            'created_at': datetime.utcnow()
        }
        
        mongo.db.quizzes.insert_one(quiz)
        
        return jsonify({
            'success': True,
            'message': 'Quiz added successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@instructor_bp.route('/get_quizzes')
@login_required
def get_quizzes():
    try:
        print(f"Getting quizzes for instructor: {current_user.id}")  # Debug print
        
        # Get all quizzes for the current instructor
        quizzes = list(mongo.db.quizzes.find({
            'instructor_id': current_user.id
        }).sort('created_at', -1))
        
        print(f"Found {len(quizzes)} quizzes")  # Debug print
        
        # Process each quiz
        processed_quizzes = []
        for quiz in quizzes:
            processed_quiz = {
                '_id': str(quiz['_id']),
                'title': quiz.get('title', 'Untitled Quiz'),
                'description': quiz.get('description', 'No description'),
                'course_name': quiz.get('course_name', 'No course'),
                'questions': quiz.get('questions', []),
                'created_at': quiz['created_at'].isoformat() if 'created_at' in quiz else None
            }
            processed_quizzes.append(processed_quiz)
            print(f"Processed quiz: {processed_quiz['title']}")  # Debug print
        
        return jsonify({
            'success': True,
            'data': processed_quizzes
        })
    except Exception as e:
        print(f"Error in get_quizzes: {str(e)}")  # Debug print
        return jsonify({
            'success': False,
            'message': str(e)
        })

@instructor_bp.route('/quiz/<quiz_id>', methods=['DELETE'])
@login_required
def delete_quiz(quiz_id):
    try:
        result = mongo.db.quizzes.delete_one({
            '_id': ObjectId(quiz_id),
            'instructor_id': current_user.id
        })
        
        if result.deleted_count:
            return jsonify({
                'success': True,
                'message': 'Quiz deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Quiz not found'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@instructor_bp.route('/download_template')
@login_required
def download_template():
    wb = Workbook()
    ws = wb.active
    ws.title = "Quiz Questions"
    
    # Add headers
    headers = ['Question', 'Option1', 'Option2', 'Option3', 'Option4', 'CorrectAnswer(1-4)']
    ws.append(headers)
    
    # Add sample row
    sample = ['What is Python?', 'A programming language', 'A snake', 'A movie', 'A book', '1']
    ws.append(sample)
    
    # Save to BytesIO
    excel_file = BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)
    
    return send_file(
        excel_file,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='quiz_template.xlsx'
    )

@instructor_bp.route('/process_quiz_excel', methods=['POST'])
@login_required
def process_quiz_excel():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'})
            
        file = request.files['file']
        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'success': False, 'message': 'Invalid file format. Please upload an Excel file (.xlsx or .xls)'})
        
        # Read Excel file
        df = pd.read_excel(file)
        
        # Print the columns for debugging
        print("Columns in Excel:", df.columns.tolist())
        
        # Get the actual column names from the Excel file
        excel_columns = df.columns.tolist()
        
        # Find question column - look for any column containing 'question'
        question_col = None
        for col in excel_columns:
            if 'question' in str(col).lower().replace(" ", ""):
                question_col = col
                break
        
        if not question_col:
            return jsonify({
                'success': False,
                'message': 'Could not find question column in Excel file'
            })
            
        # Find option columns - look for columns containing 'option'
        option_cols = []
        for col in excel_columns:
            col_lower = str(col).lower().replace(" ", "")
            if 'option' in col_lower:
                option_cols.append(col)
        
        # Find correct answer column
        correct_answer_col = None
        for col in excel_columns:
            col_lower = str(col).lower().replace(" ", "")
            if 'correcta' in col_lower or 'correct_a' in col_lower or 'correctanswer' in col_lower:
                correct_answer_col = col
                break
        
        if not correct_answer_col:
            return jsonify({
                'success': False,
                'message': 'Could not find correct answer column in Excel file'
            })
            
        if len(option_cols) < 2:
            return jsonify({
                'success': False,
                'message': f'Could not find enough option columns in Excel file. Found columns: {option_cols}'
            })
            
        questions = []
        for index, row in df.iterrows():
            try:
                # Get options that are not empty
                options = [str(row[col]).strip() for col in option_cols if pd.notna(row[col])]
                
                # Skip rows where question is empty
                if pd.isna(row[question_col]) or not str(row[question_col]).strip():
                    continue
                    
                # Get correct answer
                correct_answer = str(row[correct_answer_col]).strip()
                
                # Try to find the correct answer index
                try:
                    # First try to convert to integer (1-based index)
                    correct_index = int(correct_answer) - 1
                except ValueError:
                    # If not a number, try to find the matching option
                    try:
                        correct_index = options.index(correct_answer)
                    except ValueError:
                        return jsonify({
                            'success': False,
                            'message': f'Invalid correct answer in row {index + 2}: {correct_answer}'
                        })
                
                if not 0 <= correct_index < len(options):
                    return jsonify({
                        'success': False,
                        'message': f'Invalid correct answer index in row {index + 2}: {correct_answer}'
                    })
                
                question = {
                    'question': str(row[question_col]).strip(),
                    'options': options,
                    'correct_answer': correct_index
                }
                
                questions.append(question)
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'Error processing row {index + 2}: {str(e)}'
                })
        
        if not questions:
            return jsonify({
                'success': False,
                'message': 'No valid questions found in the Excel file'
            })
        
        print(f"Successfully processed {len(questions)} questions")  # Debug print
        return jsonify({
            'success': True,
            'data': questions
        })
        
    except Exception as e:
        print(f"Error processing Excel: {str(e)}")  # Debug print
        return jsonify({
            'success': False,
            'message': f'Error processing Excel file: {str(e)}'
        })

@instructor_bp.route('/quiz/<quiz_id>/attempts')
@login_required
def get_quiz_attempts(quiz_id):
    try:
        # First verify that the quiz belongs to the current instructor
        quiz = mongo.db.quizzes.find_one({
            '_id': ObjectId(quiz_id),
            'instructor_id': current_user.id
        })
        
        if not quiz:
            return jsonify({
                'success': False,
                'message': 'Quiz not found or unauthorized'
            })

        # Get all attempts for this quiz
        attempts = list(mongo.db.quiz_attempts.find({
            'quiz_id': ObjectId(quiz_id)
        }).sort('submitted_at', -1))

        # Process the attempts
        for attempt in attempts:
            attempt['_id'] = str(attempt['_id'])
            attempt['quiz_id'] = str(attempt['quiz_id'])
            if 'submitted_at' in attempt:
                attempt['submitted_at'] = attempt['submitted_at'].isoformat()
            
            # Calculate score percentage if not already calculated
            if 'score' not in attempt:
                correct = attempt.get('correct_answers', 0)
                total = attempt.get('total_questions', len(quiz['questions']))
                attempt['score'] = round((correct / total) * 100) if total > 0 else 0

        return jsonify({
            'success': True,
            'data': attempts
        })

    except Exception as e:
        print(f"Error in get_quiz_attempts: {str(e)}")  # Debug print
        return jsonify({
            'success': False,
            'message': str(e)
        })

@instructor_bp.route('/attempt/<attempt_id>')
@login_required
def get_attempt_details(attempt_id):
    try:
        # Get the attempt details
        attempt = mongo.db.quiz_attempts.find_one({'_id': ObjectId(attempt_id)})
        
        if not attempt:
            return jsonify({
                'success': False,
                'message': 'Attempt not found'
            })

        # Get the quiz to verify ownership and get questions
        quiz = mongo.db.quizzes.find_one({
            '_id': attempt['quiz_id'],
            'instructor_id': current_user.id
        })

        if not quiz:
            return jsonify({
                'success': False,
                'message': 'Unauthorized to view this attempt'
            })

        # Process the attempt data
        attempt['_id'] = str(attempt['_id'])
        attempt['quiz_id'] = str(attempt['quiz_id'])
        if 'submitted_at' in attempt:
            attempt['submitted_at'] = attempt['submitted_at'].isoformat()

        # Add quiz questions and student answers
        attempt['questions'] = []
        student_answers = attempt.get('answers', [])
        
        for idx, question in enumerate(quiz['questions']):
            student_answer = student_answers[idx] if idx < len(student_answers) else None
            question_data = {
                'question': question['question'],
                'options': question['options'],
                'correct_answer': question['correct_answer'],
                'student_answer': student_answer
            }
            attempt['questions'].append(question_data)

        # Remove the raw answers array
        if 'answers' in attempt:
            del attempt['answers']

        return jsonify({
            'success': True,
            'data': attempt
        })

    except Exception as e:
        print(f"Error in get_attempt_details: {str(e)}")  # Debug print
        return jsonify({
            'success': False,
            'message': str(e)
        })

