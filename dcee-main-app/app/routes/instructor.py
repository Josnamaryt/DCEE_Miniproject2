from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
# from app import login_manager
from app import mongo
from datetime import datetime

instructor_bp = Blueprint('instructor', __name__)

@instructor_bp.route('/dashboard')
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
                'name': current_user.name,
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

