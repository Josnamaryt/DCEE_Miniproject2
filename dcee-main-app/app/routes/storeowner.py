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
from bson.errors import InvalidId
from flask import jsonify
import pandas as pd
from prophet import Prophet
import numpy as np

storeowner_bp = Blueprint('storeowner', __name__)

# Define the upload folder for product images
UPLOAD_FOLDER = os.path.join('dcee-main-app', 'app', 'static', 'images', 'product')
PRODUCT_IMAGES_FOLDER = os.path.join('dcee-main-app', 'app', 'static', 'images', 'product', 'product_images')

# Ensure the product_images folder exists
os.makedirs(PRODUCT_IMAGES_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@storeowner_bp.route('/get_profile', methods=['GET'])
@login_required
def get_profile():
    user = mongo.db.users.find_one({'email': current_user.email})
    if user:
        profile_data = {
            'first_name': user.get('first_name', ''),
            'email': user.get('email', ''),
            'phone': user.get('phone', '')
        }
        return jsonify({'success': True, 'data': profile_data})
    else:
        return jsonify({'success': False, 'message': 'User not found'}), 404

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
    store_type = request.form.get('store_type')
    store_address = request.form.get('store_address')
    store_gstin = request.form.get('store_gstin')
    store_established_date = request.form.get('store_established_date')

    # Server-side validation
    if not all([store_name, store_type, store_address, store_gstin, store_established_date]):
        return jsonify({'success': False, 'message': 'All fields are required'}), 400

    # Validate store name and type
    if not re.match(r'^[A-Za-z\s]+$', store_name) or not re.match(r'^[A-Za-z\s]+$', store_type):
        return jsonify({'success': False, 'message': 'Store name and type should not contain numbers'}), 400

    # Validate GSTIN
    if not re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$', store_gstin):
        return jsonify({'success': False, 'message': 'Invalid GSTIN format'}), 400

    # Check if store already exists
    existing_store = mongo.db.stores.find_one({
        '$or': [
            {'store_name': store_name},
            {'store_gstin': store_gstin}
        ]
    })
    if existing_store:
        return jsonify({'success': False, 'message': 'A store with this name or GSTIN already exists'}), 400

    store = {
        'store_name': store_name,
        'store_type': store_type,
        'store_address': store_address,
        'store_gstin': store_gstin,
        'store_established_date': store_established_date,
        'store_owner_id': current_user.email
    }

    try:
        mongo.db.stores.insert_one(store)
        return jsonify({'success': True, 'message': 'Store registered successfully'}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Store data
@storeowner_bp.route('/fetch_stores', methods=['GET'])
@login_required
def fetch_stores():
    user_email = current_user.email
    stores = list(mongo.db.stores.find({'store_owner_id': user_email}))
    formatted_stores = []
    for store in stores:
        formatted_store = {
            'id': str(store['_id']),  # Include the store ID to help with debugging
            'name': store.get('store_name', ''),
            'type': store.get('store_type', ''),
            'address': store.get('store_address', ''),
            'gstin': store.get('store_gstin', ''),
            'established_date': store.get('store_established_date', ''),
        }
        formatted_stores.append(formatted_store)
    print("Fetched Stores:", formatted_stores)
    return jsonify({'data': formatted_stores})

@storeowner_bp.route('/get_stores', methods=['GET'])
@login_required
def get_stores():
    response = fetch_stores()
    stores = response.get_json().get('data', [])
    user_data = {
        'first_name': 'NA',
        'last_name': 'NA',
        'email': 'NA',
        'gstin': 'NA'
    }
    return render_template('storefrontowner/stores.html', user_data=user_data, stores=stores)

@storeowner_bp.route('/register_product', methods=['POST'])
@login_required
def register_product():
    print("flag1")
    product_name = request.form.get('product_name')
    product_price = request.form.get('product_price')
    product_status = request.form.get('product_status')
    product_quantity = request.form.get('product_quantity')
    product_add_date = request.form.get('product_add_date')
    product_description = request.form.get('product_description')
    print("flag2")
    print(product_description)
    product_image = request.files.get('product_image')
    print(product_image)

    # Basic validation
    if not all([product_name, product_price, product_status, product_quantity, product_add_date, product_description, product_image]):
        return jsonify({'success': False, 'message': 'All fields are required'}), 400

    if not allowed_file(product_image.filename):
        return jsonify({'success': False, 'message': 'Invalid file type'}), 400

    # Save the product image
    try:
        filename = secure_filename(product_image.filename)
        image_path = os.path.join('product_images', filename)
        full_path = os.path.join(PRODUCT_IMAGES_FOLDER, filename)
        product_image.save(full_path)
        print(f"Image saved at: {full_path}")
    except Exception as e:
        print(f"Error saving image: {str(e)}")
        return jsonify({'success': False, 'message': f'Error saving image: {str(e)}'}), 500

    product = {
        'product_name': product_name,
        'product_price': float(product_price),
        'product_status': product_status,
        'product_quantity': int(product_quantity),
        'product_add_date': product_add_date,
        'product_description': product_description,
        'product_image': image_path,
        'store_owner_id': current_user.email
    }
    print(product)

    try:
        mongo.db.products.insert_one(product)
        print(f"Product registered: {product}")
        return jsonify({'success': True, 'message': 'Product registered successfully'}), 201
    except Exception as e:
        print(f"Error inserting product into database: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


# @storeowner_bp.route('/get_products', methods=['GET'])
# @login_required
# def get_products():
#     # Fetch products from the 'products' collection where store_owner_id matches the current user's email
#     products = list(mongo.db.products.find({'store_owner_id': current_user.email}))
#     for product in products:
#         product['_id'] = str(product['_id'])
#         # Convert product_add_date to datetime object before formatting
#         product_add_date = product.get('product_add_date')
#         if product_add_date and isinstance(product_add_date, datetime):
#             product['product_add_date'] = product_add_date.strftime('%Y-%m-%d')
#         else:
#             product['product_add_date'] = None
#         product['product_image'] = product.get('product_image', '')
#     # Return the products as a JSON response
#     return render_template('storefrontowner/products.html', products=products)

@storeowner_bp.route('/fetch_products', methods=['GET'])
@login_required
def fetch_products():
    user_email = current_user.email
    products = list(mongo.db.products.find({'store_owner_id': user_email}))
    formatted_products = []
    for product in products:
        formatted_product = {
            'id': str(product['_id']),
            'name': product.get('product_name', ''),
            'price': f"${product.get('product_price', 0):.2f}",
            'status': product.get('product_status', ''),
            'quantity': product.get('product_quantity', 0),
            'added_date': product.get('product_add_date', '') if isinstance(product.get('product_add_date'), str) else (product.get('product_add_date').strftime('%Y-%m-%d') if product.get('product_add_date') else ''),
            
            'image': product.get('product_image', ''),
            'added_date': product.get('product_add_date', '') if isinstance(product.get('product_add_date'), str) else (product.get('product_add_date').strftime('%Y-%m-%d') if product.get('product_add_date') else ''),
            'actions': f'<button onclick="editProduct(\'{str(product["_id"])}\')">Edit</button> <button onclick="deleteProduct(\'{str(product["_id"])}\')">Delete</button>'
        }
        formatted_products.append(formatted_product)
    print("Fetched Products:", formatted_products)
    return jsonify({'data': formatted_products})

@storeowner_bp.route('/get_products', methods=['GET'])
@login_required
def get_products():
    response = fetch_products()
    products = response.get_json().get('data', [])
    user_data = {
        'first_name': 'NA',
        'last_name': 'NA',
        'email': 'NA'
    }
    
    return render_template('storefrontowner/products.html', user_data=user_data, product=products)

@storeowner_bp.route('/delete_store/<store_id>', methods=['DELETE'])
@login_required
def delete_store(store_id):
    try:
        result = mongo.db.stores.delete_one({'_id': ObjectId(store_id), 'store_owner_id': current_user.email})
        if result.deleted_count:
            return jsonify({'success': True, 'message': 'Store deleted successfully'}), 200
        else:
            return jsonify({'success': False, 'message': 'Store not found or you do not have permission to delete it'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@storeowner_bp.route('/delete_product/<product_id>', methods=['GET','DELETE'])
@login_required
def delete_product(product_id):
    try:
        result = mongo.db.products.delete_one({'_id': ObjectId(product_id), 'store_owner_id': current_user.email})
        if result.deleted_count:
            return jsonify({'success': True, 'message': 'Product deleted successfully'}), 200
        else:
            return jsonify({'success': False, 'message': 'Product not found or you do not have permission to delete it'}), 404
    except InvalidId:
        return jsonify({'success': False, 'message': 'Invalid product ID'}), 400
    except Exception as e:
        print(f"Error deleting product: {str(e)}")  # Log the error
        return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500

@storeowner_bp.route('/get_store/<store_id>', methods=['GET'])
@login_required
def get_store(store_id):
    try:
        store = mongo.db.stores.find_one({'_id': ObjectId(store_id), 'store_owner_id': current_user.email})
        if store:
            formatted_store = {
                'id': str(store['_id']),
                'name': store.get('store_name', ''),
                'type': store.get('store_type', ''),
                'address': store.get('store_address', ''),
                'gstin': store.get('store_gstin', ''),
                'established_date': store.get('store_established_date', ''),
            }
            return jsonify({'success': True, 'store': formatted_store})
        else:
            return jsonify({'success': False, 'message': 'Store not found or you do not have permission to edit it'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@storeowner_bp.route('/update_store/<store_id>', methods=['PUT'])
@login_required
def update_store(store_id):
    try:
        data = request.json
        result = mongo.db.stores.update_one(
            {'_id': ObjectId(store_id), 'store_owner_id': current_user.email},
            {'$set': {
                'store_name': data['name'],
                'store_type': data['type'],
                'store_address': data['address'],
                'store_gstin': data['gstin'],
                'store_established_date': data['established_date']
            }}
        )
        if result.modified_count:
            return jsonify({'success': True, 'message': 'Store updated successfully'}), 200
        else:
            return jsonify({'success': False, 'message': 'Store not found or you do not have permission to update it'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@storeowner_bp.route('/get_product/<product_id>', methods=['GET'])
@login_required
def get_product(product_id):
    try:
        product = mongo.db.products.find_one({'_id': ObjectId(product_id), 'store_owner_id': current_user.email})
        if product:
            formatted_product = {
                'id': str(product['_id']),
                'name': product.get('product_name', ''),
                'price': product.get('product_price', 0),
                'status': product.get('product_status', ''),
                'quantity': product.get('product_quantity', 0),
                'added_date': product.get('product_add_date', '') if isinstance(product.get('product_add_date'), str) else (product.get('product_add_date').strftime('%Y-%m-%d') if product.get('product_add_date') else ''),
            }
            return jsonify({'success': True, 'product': formatted_product})
        else:
            return jsonify({'success': False, 'message': 'Product not found or you do not have permission to edit it'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@storeowner_bp.route('/update_product/<product_id>', methods=['PUT'])
@login_required
def update_product(product_id):
    try:
        data = request.json
        result = mongo.db.products.update_one(
            {'_id': ObjectId(product_id), 'store_owner_id': current_user.email},
            {'$set': {
                'product_name': data['name'],
                'product_price': data['price'],
                'product_status': data['status'],
                'product_quantity': data['quantity'],
                'product_add_date': data['added_date']
            }}
        )
        if result.modified_count:
            return jsonify({'success': True, 'message': 'Product updated successfully'}), 200
        else:
            return jsonify({'success': False, 'message': 'Product not found or you do not have permission to update it'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@storeowner_bp.route('/get_product_overview', methods=['GET'])
@login_required
def get_product_overview():
    try:
        # Get the total number of products
        total_products = mongo.db.products.count_documents({'store_owner_id': current_user.email})

        # Get the number of products by status
        available_products = mongo.db.products.count_documents({'store_owner_id': current_user.email, 'product_status': 'available'})
        out_of_stock_products = mongo.db.products.count_documents({'store_owner_id': current_user.email, 'product_status': 'out_of_stock'})
        discontinued_products = mongo.db.products.count_documents({'store_owner_id': current_user.email, 'product_status': 'discontinued'})

        # Get the top 5 products by quantity
        top_products = list(mongo.db.products.find(
            {'store_owner_id': current_user.email},
            {'product_name': 1, 'product_quantity': 1, '_id': 0}
        ).sort('product_quantity', -1).limit(5))

        return render_template('storefrontowner/product_overview.html',
                               total_products=total_products,
                               available_products=available_products,
                               out_of_stock_products=out_of_stock_products,
                               discontinued_products=discontinued_products,
                               top_products=top_products)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@storeowner_bp.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    first_name = request.form.get('first_name')
    email = request.form.get('email')
    phone = request.form.get('phone')

    if not all([first_name, email, phone]):
        return jsonify({'success': False, 'message': 'All fields are required'}), 400

    try:
        mongo.db.users.update_one(
            {'email': current_user.email},
            {'$set': {
                'first_name': first_name,
                'email': email,
                'phone': phone
            }}
        )
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

def load_dummy_data():
    df = pd.read_csv('app/routes/dummydata.txt')
    df['ds'] = pd.to_datetime(df['date'])
    return df

@storeowner_bp.route('/stock_management')
@login_required
def stock_management():
    # Load dummy data instead of fetching from the database
    dummy_data = load_dummy_data()
    
    # Group the data by product_id to create a list of products
    products = []
    for product_id, group in dummy_data.groupby('product_id'):
        product = {
            '_id': str(product_id),
            'product_name': group['product_name'].iloc[0],
            'product_quantity': group['quantity'].iloc[-1],
            'stock_history': group[['ds', 'quantity']].rename(columns={'ds': 'date'}).to_dict('records')
        }
        products.append(product)
    
    # Prepare data for stock prediction
    stock_data = prepare_stock_data(products)
    
    # Generate predictions
    predictions = generate_stock_predictions(stock_data)
    
    # Convert predictions to a format suitable for JSON serialization
    serializable_predictions = {}
    for product_id, pred in predictions.items():
        serializable_predictions[product_id] = pred.to_dict('records')
    
    return render_template('storefrontowner/stock_management.html', products=products, predictions=serializable_predictions)

def prepare_stock_data(products):
    stock_data = []
    for product in products:
        if 'stock_history' in product:
            for entry in product['stock_history']:
                stock_data.append({
                    'product_id': str(product['_id']),
                    'product_name': product['product_name'],
                    'ds': pd.to_datetime(entry['date']),
                    'y': float(entry['quantity'])
                })
    return pd.DataFrame(stock_data)

def generate_stock_predictions(stock_data):
    predictions = {}
    for product_id in stock_data['product_id'].unique():
        product_data = stock_data[stock_data['product_id'] == product_id]
        if len(product_data) > 1:  # Prophet requires at least 2 data points
            model = Prophet()
            model.fit(product_data[['ds', 'y']])
            future = model.make_future_dataframe(periods=30)  # Predict for the next 30 days
            forecast = model.predict(future)
            predictions[product_id] = forecast.tail(30)[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
    return predictions
