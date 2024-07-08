from flask import Blueprint, render_template, redirect, url_for, request, flash
# from flask_login import login_user, logout_user, login_required 
# from app import login_manager

auth_bp = Blueprint('auth', __name__)
@auth_bp.route('/login', methods = ['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password= request.form['password']
    return render_template('auth/login.html')
