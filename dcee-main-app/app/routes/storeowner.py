from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
# from app import login_manager

storeowner_bp = Blueprint('storefrontowner', __name__)

@storeowner_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('storefrontowner/dashboard.html')

@storeowner_bp.route('/get_profile', methods=['GET'])
@login_required
def get_profile():
    # Assuming current_user has attributes first_name, last_name, email, and gstin
    user_data = {
        'first_name': current_user.first_name,
        'last_name': current_user.last_name,
        'email': current_user.email,
        'gstin': current_user.gstin
    }
    return jsonify(user_data)