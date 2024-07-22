from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required
from app import login_manager, mongo
from app.models import User
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime
import re

auth_bp = Blueprint('auth', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

def is_valid_email(email):
    # Basic email format validation
    regex = r'^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.match(regex, email)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = mongo.db.users.find_one({'email': email})
        if user:
            if check_password_hash(user['password'], password):
                user_obj = User(
                    _id=user['_id'],
                    email=user['email'],
                    password_hash=user['password'],
                    role=user.get('role'),
                    status=user.get('status')
                )
                login_user(user_obj)
                flash('Login successful!', 'success')
                return redirect(url_for('admin.dashboard'))
            else:
                flash('Invalid password.', 'danger')
        else:
            flash('Email not registered.', 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Email format validation
        if not is_valid_email(email):
            flash('Invalid email format.', 'danger')
            return redirect(url_for('auth.register'))

        # Email uniqueness check
        if mongo.db.users.find_one({'email': email}):
            flash('Email is already in use. Please use a different email.', 'danger')
            return redirect(url_for('auth.register'))

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('auth.register'))

        first_name = request.form['first_name']
        last_name = request.form['last_name']
        role = request.form['role']
        password_hash = generate_password_hash(password)
        created_at = datetime.now()
        updated_at = datetime.now()
        status = 'active'

        # Insert user into the users collection
        user_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'password': password_hash,
            'role': role,
            'created_at': created_at,
            'updated_at': updated_at,
            'status': status
        }
        mongo.db.users.insert_one(user_data)

        # Insert user into the login collection
        login_data = {
            'email': email,
            'password': password_hash,
            'role': role,
            'status': status,
            'created_at': created_at,
        }
        mongo.db.login.insert_one(login_data)

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/sign-up.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))
