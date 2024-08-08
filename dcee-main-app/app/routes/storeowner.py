from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify
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
from flask import request

storeowner_bp = Blueprint('storeowner', __name__)

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

@storeowner_bp.route('/dashboard')
@login_required
def dashboard():
    user_email = current_user.email
    print("Current user email:", user_email)
    store_owner = mongo.db.users.find_one({'email': user_email})
    if store_owner:
        store_owner['_id'] = str(store_owner['_id'])
        print("MongoDB user document:", store_owner)
    else:
        print("No matching document found in MongoDB")
        store_owner = {}
    current_user_dict = {
        'email': current_user.email,
        'first_name': store_owner.get('first_name', ''),
        'last_name': store_owner.get('last_name', ''),
    }
    return render_template('storefrontowner/dashboard.html', current_user_dict=current_user_dict)

@storeowner_bp.route('/register_store', methods=['POST'])
@login_required
def register_store():
    store_name = request.form.get('store_name')
    store_address = request.form.get('store_address')
    store_gstin = request.form.get('store_gstin')
    store_owner_id = current_user.email
    store_type = request.form.get('store_type')
    store_established_date = request.form.get('store_established_date')
    
    # Basic validation
    if not all([store_name, store_address, store_gstin, store_type, store_established_date]):
        return jsonify({'success': False, 'message': 'All fields are required'}), 400

    store = {
        'store_name': store_name,
        'store_type': store_type,
        'store_address': store_address,
        'store_gstin': store_gstin,
        'store_owner_id': store_owner_id,
        'store_established_date': store_established_date
    }
    
    try:
        mongo.db.stores.insert_one(store)
        return jsonify({'success': True, 'message': 'Store registered successfully'}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500