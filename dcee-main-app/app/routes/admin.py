from flask import Blueprint, render_template, redirect, url_for, request, flash
# from flask_login import login_user, logout_user, login_required 
# from app import login_manager

admin_bp = Blueprint('admin', __name__)
@admin_bp.route('/dashboard', methods = ['POST', 'GET'])
def dashboard():
    print("getting inside dashboard") #debugging
    return render_template('admin/dashboard.html')