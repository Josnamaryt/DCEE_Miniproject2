from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
# from app import login_manager

instructor_bp = Blueprint('instructor', __name__)

@instructor_bp.route('/dashboard')
@login_required
def dashboard():
    user_name = f"{current_user.first_name} {current_user.last_name}"
    return render_template('instructor/dashboard.html', user_name=user_name)