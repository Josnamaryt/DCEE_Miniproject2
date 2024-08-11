from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app import login_manager, mongo
from app.models import User
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime, timedelta
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

@auth_bp.route('/')
def home():
    return render_template('home.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user_data = mongo.db.users.find_one({'email': email})
        if user_data:
            if check_password_hash(user_data['password'], password):
                user = User(user_data)
                login_user(user)
                flash('Login successful!', 'success')
                # Redirect based on user role
                if user_data['role'] == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif user_data['role'] == 'customer':
                    return redirect(url_for('customer.dashboard'))
                elif user_data['role'] == 'instructor':
                    return redirect(url_for('instructor.dashboard'))
                elif user_data['role'] == 'storefrontowner':
                    return redirect(url_for('storeowner.dashboard'))
                else:
                    flash('Invalid user role.', 'danger')
                    return redirect(url_for('auth.login'))
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
        gstin = request.form.get('gstin')  # Add this line to get GSTIN
        
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
            'gstin': gstin,  # Add GSTIN to user data
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

# Initialize Flask-Mail
mail = Mail()

# Function to generate OTP
def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

@auth_bp.route('/forget-password', methods=['GET', 'POST'])
def forget_password():
    if request.method == 'POST':
        email = request.form['email']
        user = mongo.db.users.find_one({'email': email})
        
        if user:
            otp = generate_otp()
            expiration_time = datetime.now() + timedelta(minutes=15)
            
            # Store OTP in the database
            mongo.db.password_reset.update_one(
                {'email': email},
                {'$set': {'otp': otp, 'expiration_time': expiration_time}},
                upsert=True
            )
            
            # Send OTP via email
            msg = Message('Password Reset OTP',
                          sender='your-email@example.com',
                          recipients=[email])
            msg.body = f'''To reset your password, use the following OTP:

{otp}

This OTP is valid for 15 minutes.
If you did not request a password reset, please ignore this email.
'''
            mail.send(msg)
            
            flash('An OTP has been sent to your email. Please check your inbox.', 'info')
            return redirect(url_for('auth.reset_password'))
        else:
            flash('Email not found. Please check the email address and try again.', 'danger')
    
    return render_template('auth/forget_password.html')

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form['email']
        otp = request.form['otp']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        if new_password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('auth.reset_password'))
        
        reset_request = mongo.db.password_reset.find_one({
            'email': email,
            'otp': otp,
            'expiration_time': {'$gt': datetime.now()}
        })
        
        if reset_request:
            # Update password in users collection
            password_hash = generate_password_hash(new_password)
            mongo.db.users.update_one(
                {'email': email},
                {'$set': {'password': password_hash}}
            )
            
            # Update password in login collection
            mongo.db.login.update_one(
                {'email': email},
                {'$set': {'password': password_hash}}
            )
            
            # Remove the used OTP
            mongo.db.password_reset.delete_one({'email': email})
            
            flash('Your password has been reset successfully. You can now log in with your new password.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Invalid or expired OTP. Please try again.', 'danger')
    
    return render_template('auth/forget_password.html')