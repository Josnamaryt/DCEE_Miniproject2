from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify, send_file
from flask_login import login_user, logout_user, login_required, current_user
from app import login_manager, mongo
from app.models import User, Sale
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime, timedelta
import re
import random
import string
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
import os
from bson.errors import InvalidId
import pandas as pd
from prophet import Prophet
import numpy as np
from app.routes.auth import no_cache
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO

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
@no_cache
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
@no_cache
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
@no_cache
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
@no_cache
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
@no_cache
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
@no_cache
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
@no_cache
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
@no_cache
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
@no_cache
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
@no_cache
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
@no_cache
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
@no_cache
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
@no_cache
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
@no_cache
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
@no_cache
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
@no_cache
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
@no_cache
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
@no_cache
def stock_management():
    # Load dummy data instead of fetching from the database
    dummy_data = load_dummy_data()
    #  # Fetch products for the current store owner
    # products = list(mongo.db.products.find({"store_owner_id": current_user.email}))
    
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

@storeowner_bp.route('/get_available_quizzes')
@login_required
def get_available_quizzes():
    try:
        # Get all available quizzes
        quizzes = list(mongo.db.quizzes.find({
            'status': 'active'
        }).sort('created_at', -1))
        
        # Process quiz data
        for quiz in quizzes:
            quiz['_id'] = str(quiz['_id'])
            if 'course_id' in quiz:
                quiz['course_id'] = str(quiz['course_id'])
                # Get course name
                course = mongo.db.courses.find_one({'_id': ObjectId(quiz['course_id'])})
                quiz['course_name'] = course['name'] if course else 'Unknown Course'
            else:
                quiz['course_name'] = 'No Course Assigned'
        
        return jsonify({
            'success': True,
            'data': quizzes
        })
    except Exception as e:
        print(f"Error in get_available_quizzes: {str(e)}")  # Debug print
        return jsonify({
            'success': False,
            'message': str(e)
        })

@storeowner_bp.route('/get_available_courses')
@login_required
@no_cache
def get_available_courses():
    try:
        # Fetch all active courses from MongoDB
        courses = list(mongo.db.courses.find({'status': 'active'}).sort('created_at', -1))
        
        # Process courses for JSON response
        for course in courses:
            course['_id'] = str(course['_id'])
            if 'created_at' in course:
                course['created_at'] = course['created_at'].isoformat()
        
        return jsonify({
            'success': True,
            'data': courses
        })
    except Exception as e:
        print(f"Error in get_available_courses: {str(e)}")  # Debug print
        return jsonify({
            'success': False,
            'message': str(e)
        })


@storeowner_bp.route('/quiz/<quiz_id>', methods=['GET'])
@login_required
def get_quiz(quiz_id):
    try:
        quiz = mongo.db.quizzes.find_one({'_id': ObjectId(quiz_id)})
        if not quiz:
            return jsonify({
                'success': False,
                'message': 'Quiz not found'
            })
        
        # Convert ObjectId to string for JSON serialization
        quiz['_id'] = str(quiz['_id'])
        if 'course_id' in quiz:
            quiz['course_id'] = str(quiz['course_id'])
        
        return jsonify({
            'success': True,
            'data': quiz
        })
    except Exception as e:
        print(f"Error in get_quiz: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

@storeowner_bp.route('/quiz/<quiz_id>/submit', methods=['POST'])
@login_required
def submit_quiz(quiz_id):
    try:
        # Check if user has already attempted this quiz
        existing_attempts = mongo.db.quiz_attempts.count_documents({
            'quiz_id': ObjectId(quiz_id),
            'user_id': str(current_user.id)
        })
        
        if existing_attempts >= 2:
            return jsonify({
                'success': False,
                'message': 'You have already used your maximum attempts for this quiz.'
            })

        data = request.json
        answers = data.get('answers', [])
        time_taken = data.get('time_taken', 0)
        total_questions = data.get('total_questions', 0)
        questions_attempted = data.get('questions_attempted', 0)
        correct_answers = data.get('correct_answers', 0)
        quiz_title = data.get('quiz_title', '')
        course_name = data.get('course_name', '')
        
        # Get quiz for verification
        quiz = mongo.db.quizzes.find_one({'_id': ObjectId(quiz_id)})
        if not quiz:
            return jsonify({
                'success': False,
                'message': 'Quiz not found'
            })
        
        # Calculate score percentage out of 100
        score_percentage = round((correct_answers / total_questions) * 100) if total_questions > 0 else 0
        
        # Create attempt record
        attempt = {
            'quiz_id': ObjectId(quiz_id),
            'quiz_title': quiz_title,
            'course_name': course_name,
            'user_id': str(current_user.id),
            'user_name': f"{current_user.first_name} {current_user.last_name}",
            'user_email': current_user.email,
            'answers': answers,
            'correct_answers': correct_answers,
            'questions_attempted': questions_attempted,
            'total_questions': total_questions,
            'score_percentage': score_percentage,
            'time_taken': time_taken,
            'submitted_at': datetime.utcnow(),
            'status': 'pass' if score_percentage >= 70 else 'fail'
        }
        
        # Insert into quiz_attempts collection
        result = mongo.db.quiz_attempts.insert_one(attempt)
        
        return jsonify({
            'success': True,
            'data': {
                'attempt_id': str(result.inserted_id),
                'score_percentage': score_percentage,
                'correct_answers': correct_answers,
                'total_questions': total_questions,
                'questions_attempted': questions_attempted,
                'time_taken': time_taken,
                'status': 'pass' if score_percentage >= 70 else 'fail'
            }
        })
    except Exception as e:
        print(f"Error in submit_quiz: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

@storeowner_bp.route('/quiz/<quiz_id>/attempts', methods=['GET'])
@login_required
def check_quiz_attempts(quiz_id):
    try:
        # Count attempts for this quiz by the current user
        attempts = mongo.db.quiz_attempts.count_documents({
            'quiz_id': ObjectId(quiz_id),
            'user_id': str(current_user.id)
        })
        
        return jsonify({
            'success': True,
            'attempts': attempts
        })
    except Exception as e:
        print(f"Error checking quiz attempts: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error checking quiz attempts'
        })

@storeowner_bp.route('/sales_analytics')
@login_required
@no_cache
def sales_analytics():
    try:
        # Fetch products for the current store owner
        products = list(mongo.db.products.find({"store_owner_id": current_user.email}))
        
        # Convert ObjectId to string for JSON serialization
        for product in products:
            product['_id'] = str(product['_id'])
        
        # Check if we have products
        if not products:
            flash("You don't have any products. Please add products first to view sales analytics.", "warning")
            return render_template('storefrontowner/sales_analytics.html', 
                                products=[], 
                                analytics={
                                    'product_performance': {},
                                    'seasonal_analysis': {'daily': {}, 'monthly': {}},
                                    'customer_patterns': {},
                                    'overall_summary': {
                                        'total_products': 0,
                                        'total_sales': 0,
                                        'total_revenue': 0,
                                        'avg_daily_revenue': 0,
                                        'top_products': {}
                                    }
                                },
                                insights={
                                    'summary': "No products found. Please add products to view sales analytics.",
                                    'product_insights': "",
                                    'seasonal_insights': "",
                                    'inventory_recommendations': "",
                                    'pricing_suggestions': ""
                                })
        
        # Fetch sales data (this would connect to actual sales data in production)
        sales_data = fetch_sales_data(current_user.email)
        
        # Generate analytics
        analytics = generate_sales_analytics(products, sales_data)
        
        # Use placeholder insights for now
        insights = generate_ai_insights(analytics)
        
        
        # Debug output
        print(f"Rendering sales_analytics template with {len(products)} products and {len(sales_data) if sales_data else 0} sales records")
        
        return render_template('storefrontowner/sales_analytics.html', 
                             products=products, 
                             analytics=analytics,
                             insights=insights)
    except Exception as e:
        # Log the error
        print(f"Error in sales_analytics route: {str(e)}")
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for('storeowner.dashboard'))

def fetch_sales_data(store_owner_id):
    # Check if there's actual sales data in the database
    sales_collection = mongo.db.sales
    actual_sales = list(sales_collection.find({"store_owner_id": store_owner_id}))
    
    # If we have actual sales data, use it
    if actual_sales:
        # Convert date objects to string for JSON serialization
        for sale in actual_sales:
            if 'sale_date' in sale and isinstance(sale['sale_date'], datetime):
                sale['date'] = sale['sale_date']  # Create a 'date' field for consistency
            if '_id' in sale:
                sale['_id'] = str(sale['_id'])
        return actual_sales
    
    # Otherwise, generate dummy data for demonstration
    sales_data = []
    
    # Fetch products for the store owner
    products = list(mongo.db.products.find({"store_owner_id": store_owner_id}))
    
    # Create dummy sales data for each product
    for product in products:
        # Generate sales for the last 90 days
        for i in range(90, 0, -1):
            date = datetime.now() - timedelta(days=i)
            # Random sales quantity between 0 and 20
            quantity = random.randint(0, 20)
            # Random revenue based on quantity and product price
            revenue = quantity * float(product.get('product_price', 10))
            
            # Create a Sale object using the model
            sale = Sale(
                product_id=str(product['_id']),
                product_name=product['product_name'],
                store_owner_id=store_owner_id,
                quantity=quantity,
                revenue=revenue,
                sale_date=date,
                customer_id=None  # Not using customer data for demo
            )
            
            # Convert to dictionary for database storage
            sale_data = sale.to_dict()
            sale_data['date'] = date  # Add a date field for analytics
            
            # Save the dummy data to the sales collection for future use
            try:
                # Only insert if not already in database
                mongo.db.sales.update_one(
                    {
                        'product_id': sale_data['product_id'],
                        'store_owner_id': sale_data['store_owner_id'],
                        'sale_date': sale_data['sale_date']
                    },
                    {'$setOnInsert': sale_data},
                    upsert=True
                )
            except Exception as e:
                print(f"Error saving dummy sales data: {str(e)}")
            
            sales_data.append(sale_data)
    
    return sales_data

def generate_sales_analytics(products, sales_data):
    # Initialize analytics object with default empty structures
    analytics = {
        'product_performance': {},
        'seasonal_analysis': {
            'daily': {},
            'monthly': {}
        },
        'customer_patterns': {},  # This will be empty for now
        'overall_summary': {
            'total_products': len(products),
            'total_sales': 0,
            'total_revenue': 0.0,
            'avg_daily_revenue': 0.0,
            'top_products': {}
        }
    }
    
    # If no sales data, return empty analytics
    if not sales_data or len(sales_data) == 0:
        print("No sales data available for analytics")
        return analytics
    
    try:
        # Process sales data to generate analytics
        df = pd.DataFrame(sales_data)
        
        # Convert date strings to datetime objects if needed
        if 'date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['date']):
            df['date'] = pd.to_datetime(df['date'])
        
        # 1. Product Performance Tracking
        for product in products:
            product_id = str(product['_id'])
            product_sales = df[df['product_id'] == product_id]
            
            if not product_sales.empty:
                # Calculate weekly sales for trend
                weekly_sales = product_sales.groupby(pd.Grouper(key='date', freq='W'))['quantity'].sum()
                
                analytics['product_performance'][product_id] = {
                    'name': product['product_name'],
                    'total_sales': int(product_sales['quantity'].sum()),
                    'total_revenue': float(product_sales['revenue'].sum()),
                    'avg_daily_sales': float(product_sales['quantity'].mean()),
                    'sales_trend': weekly_sales.tolist(),
                    'trend_dates': [d.strftime('%Y-%m-%d') for d in weekly_sales.index]
                }
                
                # Debug output to verify data structure
                print(f"Product {product['product_name']} performance data generated")
        
        # 2. Seasonal and Time-Based Analysis
        if not df.empty and 'date' in df.columns:
            df['day_of_week'] = df['date'].dt.day_name()
            df['month'] = df['date'].dt.month_name()
            
            # Sort days of week in correct order
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            day_sales = df.groupby('day_of_week')['quantity'].sum().reindex(day_order).fillna(0).to_dict()
            
            # Sort months in correct order
            month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                          'July', 'August', 'September', 'October', 'November', 'December']
            month_sales = df.groupby('month')['quantity'].sum().reindex(month_order).fillna(0).to_dict()
            
            analytics['seasonal_analysis'] = {
                'daily': day_sales,
                'monthly': month_sales
            }
        
        # 3. Overall Summary
        if not df.empty:
            analytics['overall_summary'] = {
                'total_products': len(products),
                'total_sales': int(df['quantity'].sum()),
                'total_revenue': float(df['revenue'].sum()),
                'avg_daily_revenue': float(df.groupby(pd.Grouper(key='date', freq='D'))['revenue'].sum().mean()),
                'top_products': df.groupby('product_name')['quantity'].sum().nlargest(5).to_dict()
            }
            
            # Debug output
            print(f"Generated overall summary with {len(analytics['overall_summary']['top_products'])} top products")
        
        return analytics
    
    except Exception as e:
        print(f"Error generating sales analytics: {str(e)}")
        # Return basic analytics structure in case of error
        return analytics

def generate_insights(analytics):
    """Generate insights from sales analytics data"""
    try:
        # For now, return placeholder insights
        insights = {
            'summary': "Based on your sales data, we've identified key insights to optimize your business performance. Your store shows a healthy sales pattern with opportunities for growth.",
            'product_insights': "Your top-performing product is generating approximately 45% of your total revenue. Consider expanding inventory for this item and creating bundled offers with lower-performing products to boost their sales.",
            'seasonal_insights': "Sales peak on weekends and at month-end. Consider running targeted promotions during weekday slumps to even out your sales distribution and improve overall revenue.",
            'inventory_recommendations': "Based on your sales patterns, we recommend increasing stock levels for your top 3 products by 15-20% for the upcoming month, while reducing inventory of slower-moving items to optimize your working capital.",
            'pricing_suggestions': "Products in similar categories show price elasticity. Consider testing a 5-10% price increase on your premium products, which shouldn't significantly impact demand based on current purchase patterns."
        }
        
        return insights
        
    except Exception as e:
        print(f"Error generating insights: {str(e)}")
        # Fallback insights if API call fails
        return {
            'summary': "Your store shows stable sales performance. Analyze the data to identify growth opportunities.",
            'product_insights': "Some products are performing better than others. Focus on your top-sellers while improving visibility of other items.",
            'seasonal_insights': "Sales patterns vary throughout the week and month. Consider this when planning promotions.",
            'inventory_recommendations': "Maintain adequate stock of popular items to avoid lost sales opportunities.",
            'pricing_suggestions': "Review your pricing strategy regularly to maximize profitability."
        }

@storeowner_bp.route('/export_sales_data', methods=['GET'])
@login_required
@no_cache
def export_sales_data():
    try:
        # Fetch sales data
        sales_data = fetch_sales_data(current_user.email)
        
        # Convert to DataFrame
        df = pd.DataFrame(sales_data)
        
        # Create a CSV in memory
        from io import StringIO
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        
        # Create response with CSV data
        from flask import Response
        response = Response(
            csv_buffer.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment; filename=sales_data.csv',
                'Content-Type': 'text/csv'
            }
        )
        
        return response
    except Exception as e:
        flash(f"Error exporting data: {str(e)}", "error")
        return redirect(url_for('storeowner.sales_analytics'))

def generate_ai_insights(analytics):
    """Generate AI-powered insights from sales analytics data using Google's Gemini API"""
    import os
    import json
    import google.generativeai as genai
    
    print("Starting generate_ai_insights function")
    
    try:
        # Initialize the Gemini API client with the API key from environment variables
        api_key = os.environ.get('GEMINI_API_KEY')
        print(f"API key found: {bool(api_key)}")
        
        if not api_key:
            print("GEMINI_API_KEY not found in environment variables")
            return generate_insights(analytics)  # Fallback to static insights
        
        print("Configuring Gemini API")    
        genai.configure(api_key=api_key)
        
        print("Creating Gemini model instance")
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Prepare analytics data for the prompt
        print("Preparing analytics data for prompt")
        analytics_json = json.dumps(analytics, indent=2)
        
        # Construct a detailed prompt for Gemini with explicit instructions for JSON format
        print("Constructing prompt")
        prompt = """
        You are a retail business analytics expert. Analyze the following sales data and provide actionable insights.
        
        Based on this data, please provide insights in these categories:
        1. Overall Summary
        2. Product Insights 
        3. Seasonal Insights
        4. Inventory Recommendations
        5. Pricing Suggestions
        
        Format your response as a valid JSON object with these keys: summary, product_insights, seasonal_insights, inventory_recommendations, pricing_suggestions.
        
        Here is the sales analytics data:
        """ + analytics_json
        
        # Generate structured output with Gemini
        generation_config = {
            "response_mime_type": "application/json",
            "temperature": 0.2,
        }
        
        # Call the Gemini API
        print("Calling Gemini API")
        try:
            response = model.generate_content(
                prompt,
                generation_config=generation_config
            )
            print("Received response from Gemini API")
            
            if not response.text:
                print("Empty response from API")
                return generate_insights(analytics)
                
            print(f"Response text: {response.text[:100]}...")  # Print first 100 chars for debugging
            
        except Exception as api_error:
            print(f"Error calling Gemini API: {str(api_error)}")
            return generate_insights(analytics)  # Fallback to static insights
        
        # Parse the response
        print("Parsing API response")
        try:
            # Try to find JSON content in the response
            import re
            json_pattern = r'({[\s\S]*})'
            json_match = re.search(json_pattern, response.text)
            
            if json_match:
                json_str = json_match.group(1)
                insights = json.loads(json_str)
                print("Successfully parsed JSON response")
            else:
                # Create structured insights from text response
                insights = {
                    'summary': "Based on your sales data analysis, your business shows potential for growth with some strategic adjustments.",
                    'product_insights': extract_key_points(response.text, ["product", "top seller", "performance"]),
                    'seasonal_insights': extract_key_points(response.text, ["seasonal", "weekly", "monthly", "pattern"]),
                    'inventory_recommendations': extract_key_points(response.text, ["inventory", "stock", "reorder"]),
                    'pricing_suggestions': extract_key_points(response.text, ["price", "pricing", "discount"])
                }
                print("Created structured insights from text response")
            
            # Ensure all required keys are present
            required_keys = ['summary', 'product_insights', 'seasonal_insights', 
                            'inventory_recommendations', 'pricing_suggestions']
            
            for key in required_keys:
                if key not in insights or not insights[key]:
                    insights[key] = f"No specific {key.replace('_', ' ')} could be generated from the available data."
            
            return insights
                
        except Exception as parsing_error:
            print(f"Error parsing response: {str(parsing_error)}")
            # Fallback to static insights in case of parsing error
            return generate_insights(analytics)
        
    except Exception as e:
        print(f"Error generating AI insights: {str(e)}")
        import traceback
        print(traceback.format_exc())
        # Fallback to static insights in case of any error
        return generate_insights(analytics)

def extract_key_points(text, keywords):
    """Extract sentences containing keywords from text"""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    relevant_sentences = []
    
    for sentence in sentences:
        if any(keyword.lower() in sentence.lower() for keyword in keywords):
            relevant_sentences.append(sentence)
    
    if relevant_sentences:
        return " ".join(relevant_sentences)
    else:
        return "No specific insights could be extracted from the available data."


@storeowner_bp.route('/certificate/<attempt_id>')
@login_required
def generate_certificate(attempt_id):
    try:
        # Get the quiz attempt details
        attempt = mongo.db.quiz_attempts.find_one({'_id': ObjectId(attempt_id)})
        if not attempt:
            return jsonify({'success': False, 'message': 'Quiz attempt not found'}), 404
            
        # Verify this is the user's attempt
        if attempt['user_id'] != str(current_user.id):
            return jsonify({'success': False, 'message': 'Unauthorized access'}), 403

        # Create PDF certificate
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=landscape(letter))
        width, height = landscape(letter)
        
        try:
            # Set up background color
            c.setFillColorRGB(0.98, 0.98, 0.98)  # Light gray background
            c.rect(0, 0, width, height, fill=True)
            
            # Try to add DCEE logo if it exists
            try:
                logo_path = os.path.join('app', 'static', 'images', 'dcee_logo.png')
                if os.path.exists(logo_path):
                    c.drawImage(logo_path, width/2 - inch, height-2*inch, width=2*inch, height=1*inch)
            except Exception as logo_error:
                print(f"Warning: Could not add logo: {str(logo_error)}")
            
            # Add outer decorative border
            c.setStrokeColorRGB(0.2, 0.4, 0.6)  # Navy blue color
            c.setLineWidth(4)
            c.roundRect(0.75*inch, 0.75*inch, width - 1.5*inch, height - 1.5*inch, 20)
            
            # Add inner decorative border
            c.setStrokeColorRGB(0.8, 0.8, 0.8)
            c.setLineWidth(1)
            c.roundRect(1.25*inch, 1.25*inch, width - 2.5*inch, height - 2.5*inch, 10)
            
            # Title
            c.setFillColorRGB(0.2, 0.4, 0.6)  # Navy blue color
            c.setFont("Helvetica-Bold", 36)
            c.drawCentredString(width/2, height - 3*inch, "Certificate of Completion")
            
            # Certificate text
            c.setFillColorRGB(0.2, 0.2, 0.2)  # Dark gray
            c.setFont("Helvetica", 20)
            c.drawCentredString(width/2, height - 4*inch, "This is to certify that")
            
            # Recipient name
            c.setFont("Helvetica-Bold", 28)
            name = f"{current_user.first_name} {current_user.last_name}"
            c.drawCentredString(width/2, height - 4.8*inch, name)
            
            # Underline for name
            name_width = c.stringWidth(name, "Helvetica-Bold", 28)
            c.setLineWidth(1)
            c.line(width/2 - name_width/2, height - 4.9*inch, width/2 + name_width/2, height - 4.9*inch)
            
            # Course completion text
            c.setFont("Helvetica", 20)
            c.drawCentredString(width/2, height - 5.6*inch, 
                "has successfully completed the course quiz for")
                
            # Course name
            c.setFont("Helvetica-Bold", 24)
            course_name = attempt.get('course_name', 'Course Name Not Available')
            c.drawCentredString(width/2, height - 6.2*inch, course_name)
            
            # Score
            c.setFont("Helvetica-Bold", 22)
            score = attempt.get('score_percentage', 0)
            c.setFillColorRGB(0.2, 0.6, 0.2) if score >= 70 else c.setFillColorRGB(0.8, 0.2, 0.2)  # Green for pass, red for fail
            c.drawCentredString(width/2, height - 6.8*inch, f"Score: {score}%")
            
            # Date and Certificate ID
            c.setFillColorRGB(0.2, 0.2, 0.2)  # Back to dark gray
            c.setFont("Helvetica", 14)
            date_str = datetime.now().strftime("%B %d, %Y")
            
            # Left side: Date
            c.drawString(1.5*inch, 2*inch, f"Date: {date_str}")
            
            # Right side: Certificate ID
            cert_id = f"Certificate ID: {str(attempt['_id'])}"
            cert_id_width = c.stringWidth(cert_id, "Helvetica", 14)
            c.drawString(width - 1.5*inch - cert_id_width, 2*inch, cert_id)
            
            # Add DCEE footer text
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(width/2, 1.5*inch, "Digital Commerce Entrepreneurship Ecosystem")
            
            # Save and close the PDF
            c.showPage()
            c.save()
            buffer.seek(0)
            
            # Send the PDF file
            return send_file(
                buffer,
                as_attachment=True,
                download_name=f"certificate_{attempt.get('course_name', 'course').replace(' ', '_')}.pdf",
                mimetype='application/pdf'
            )
            
        except Exception as pdf_error:
            print(f"Error generating PDF: {str(pdf_error)}")
            buffer.close()
            return jsonify({'success': False, 'message': f'Error generating certificate PDF: {str(pdf_error)}'}), 500

    except Exception as e:
        print(f"Error in certificate generation: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@storeowner_bp.route('/my-certificates')
@login_required
def get_my_certificates():
    try:
        # Get all passed quiz attempts for the user
        certificates = list(mongo.db.quiz_attempts.find({
            'user_id': str(current_user.id),
            'status': 'pass'
        }).sort('submitted_at', -1))
        
        # Format the certificates
        for cert in certificates:
            cert['_id'] = str(cert['_id'])
            cert['submitted_at'] = cert['submitted_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({
            'success': True,
            'data': certificates
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@storeowner_bp.route('/view-certificates')
@login_required
def view_certificates():
    try:
        # Get all passed quiz attempts for the user
        certificates = list(mongo.db.quiz_attempts.find({
            'user_id': str(current_user.id),
            'status': 'pass'
        }).sort('submitted_at', -1))
        
        # Format the certificates
        for cert in certificates:
            cert['_id'] = str(cert['_id'])
            if isinstance(cert.get('submitted_at'), datetime):
                cert['submitted_at'] = cert['submitted_at'].strftime('%Y-%m-%d %H:%M')
            
        return render_template('storefrontowner/certificates.html', certificates=certificates)
    except Exception as e:
        flash(f"Error loading certificates: {str(e)}", "error")
        return redirect(url_for('storeowner.dashboard'))

