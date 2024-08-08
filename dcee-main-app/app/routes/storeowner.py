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
from werkzeug.utils import secure_filename
import os

storeowner_bp = Blueprint('storeowner', __name__)

# Define the upload folder for product images
UPLOAD_FOLDER = 'static/images/products'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

# Store modal
@storeowner_bp.route('/get_stores', methods=['GET'])
@login_required
def get_stores():
    # Fetch stores from the 'stores' collection
    stores = list(mongo.db.stores.find())
    
    for store in stores:
        store['_id'] = str(store['_id'])
        store['store_established_date'] = store.get('store_established_date', '').strftime('%Y-%m-%d') if store.get('store_established_date') else None
        store['gstin'] = store.get('gstin', '') 
        
    # Return the stores as a JSON response
    return jsonify(stores)

@storeowner_bp.route('/register_product', methods=['POST'])
@login_required
def register_product():
    product_name = request.form.get('product_name')
    product_price = request.form.get('product_price')
    product_status = request.form.get('product_status')
    product_quantity = request.form.get('product_quantity')
    product_add_date = request.form.get('product_add_date')
    product_image = request.files.get('product_image')

    # Basic validation
    if not all([product_name, product_price, product_status, product_quantity, product_add_date, product_image]):
        return jsonify({'success': False, 'message': 'All fields are required'}), 400

    if not allowed_file(product_image.filename):
        return jsonify({'success': False, 'message': 'Invalid file type'}), 400

    # Save the product image
    filename = secure_filename(product_image.filename)
    image_path = os.path.join(UPLOAD_FOLDER, filename)
    product_image.save(image_path)

    product = {
        'product_name': product_name,
        'product_price': float(product_price),
        'product_status': product_status,
        'product_quantity': int(product_quantity),
        'product_add_date': product_add_date,
        'product_image': image_path,
        'store_owner_id': current_user.email
    }

    try:
        mongo.db.products.insert_one(product)
        return jsonify({'success': True, 'message': 'Product registered successfully'}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@storeowner_bp.route('/get_products', methods=['GET'])
@login_required
def get_products():
    # Fetch products from the 'products' collection
    products = list(mongo.db.products.find())
    
    for product in products:
        product['_id'] = str(product['_id'])
        product['product_add_date'] = product.get('product_add_date', '').strftime('%Y-%m-%d') if product.get('product_add_date') else None
        product['product_image'] = product.get('product_image', '')
        
    # Return the products as a JSON response
    return jsonify(products)