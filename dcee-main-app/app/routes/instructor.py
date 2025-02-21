from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
# from app import login_manager
from app import mongo
from datetime import datetime
from bson import ObjectId

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

@instructor_bp.route('/add_course', methods=['POST'])
@login_required
def add_course():
    try:
        data = request.json
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
        # Get all quizzes for the current instructor
        quizzes = list(mongo.db.quizzes.find({
            'instructor_id': current_user.id
        }).sort('created_at', -1))
        
        # Debug print
        print(f"Found {len(quizzes)} quizzes for instructor {current_user.id}")
        
        # Process each quiz
        for quiz in quizzes:
            quiz['_id'] = str(quiz['_id'])
            quiz['course_id'] = str(quiz['course_id'])
            quiz['created_at'] = quiz['created_at'].isoformat()
            quiz['question_count'] = len(quiz['questions'])
        
        return jsonify({
            'success': True,
            'data': quizzes
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

