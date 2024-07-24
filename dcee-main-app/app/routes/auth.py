from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app import login_manager, mongo
from app.models import User
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime
import re
import random
import string
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from flask_mail import Mail, Message

auth_bp = Blueprint('auth', __name__)
customers_bp = Blueprint('customers', __name__)

mail = Mail()
s = URLSafeTimedSerializer('Thisisasecret!')

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

        # Insert into different collection as per role
        if role == 'customer':
            add_customer = {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'created_at': created_at,
                'updated_at': updated_at
            }
            mongo.db.customers.insert_one(add_customer)
            flash('Customer registration successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        
        elif role == 'storefrontowner':
            gstin = request.form['gstin']  # Add this line to get the GSTIN from the form
            add_storefrontowner = {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'gstin': gstin,  # Add GSTIN to the storefrontowner document
                'created_at': created_at,
                'updated_at': updated_at
            }
            mongo.db.storefrontowner.insert_one(add_storefrontowner)
            flash('Storefront owner registration successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        
        elif role == 'instructor':
            add_instructor = {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'created_at': created_at,
                'updated_at': updated_at
            }
            mongo.db.instructor.insert_one(add_instructor)
            flash('Instructor registration successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/sign-up.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))

@customers_bp.route('/customers', methods=['GET'])
@login_required
def list_customers():
    customers = list(mongo.db.customers.find())
    return render_template('customers/list.html', customers=customers)

@customers_bp.route('/customers/add', methods=['GET', 'POST'])
@login_required
def add_customer():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        created_at = datetime.now()
        updated_at = datetime.now()

        customer_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'created_at': created_at,
            'updated_at': updated_at
        }
        mongo.db.customers.insert_one(customer_data)

        flash('Customer added successfully!', 'success')
        return redirect(url_for('customers.list_customers'))

    return render_template('customers/add.html')

@customers_bp.route('/customers/edit/<customer_id>', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    customer = mongo.db.customers.find_one({'_id': ObjectId(customer_id)})

    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        updated_at = datetime.now()

        mongo.db.customers.update_one(
            {'_id': ObjectId(customer_id)},
            {'$set': {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'updated_at': updated_at
            }}
        )

        flash('Customer updated successfully!', 'success')
        return redirect(url_for('customers.list_customers'))

    return render_template('customers/edit.html', customer=customer)

@customers_bp.route('/customers/delete/<customer_id>', methods=['POST'])
@login_required
def delete_customer(customer_id):
    mongo.db.customers.delete_one({'_id': ObjectId(customer_id)})
    flash('Customer deleted successfully!', 'success')
    return redirect(url_for('customers.list_customers'))

#FORGET AND RESET PASSWORD CRED
@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = mongo.db.users.find_one({'email': email})
    return render_template('auth/forgot_password.html')

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = s.loads(token, salt='password-reset', max_age=3600)
    except SignatureExpired:
        flash('The password reset link is expired.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    except BadTimeSignature:
        flash('The password reset link is invalid.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('auth.reset_password', token=token))

        password_hash = generate_password_hash(password)
        mongo.db.users.update_one({'email': email}, {'$set': {'password': password_hash}})
        flash('Your password has been updated! You are now able to log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html')