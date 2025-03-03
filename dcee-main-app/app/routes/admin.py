from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import login_manager, mongo
from bson import ObjectId
from app.routes.auth import no_cache

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard', methods=['POST', 'GET'])
@login_required
@no_cache
def dashboard():
    print("getting inside dashboard")  # debugging
    return render_template('admin/dashboard.html')

# customers list view
@admin_bp.route('/get_customers', methods=['GET'])
@login_required
@no_cache
def get_customers():
    # Fetch customers
    customers = list(mongo.db.customers.find())
    # Fetch user information with user_type 'customer'
    users_info = list(mongo.db.users.find({'user_type': 'customer'}))
    # Map email to user information
    user_info_dict = {user['email']: user for user in users_info}
    
    for customer in customers:
        customer['_id'] = str(customer['_id'])
        customer['createdAt'] = customer['createdAt'].strftime('%Y-%m-%d %H:%M:%S') if customer.get('createdAt') else None
        customer['updatedAt'] = customer['updatedAt'].strftime('%Y-%m-%d %H:%M:%S') if customer.get('updatedAt') else None
        
        # Get the user information from the user info dictionary
        user_info = user_info_dict.get(customer['email'])
        if user_info:
            customer['first_name'] = user_info.get('first_name')
            customer['last_name'] = user_info.get('last_name')
            customer['role'] = user_info.get('role')
    
    # Return the customers as a JSON response
    return jsonify(customers)

#instructor list view
@admin_bp.route('/get_instructors', methods=['GET'])
@login_required
@no_cache
def get_instructors():
    # Fetch instructors from the 'instructor' collection
    instructors = list(mongo.db.instructor.find())
    # Fetch user information with user_type 'instructor'
    users_info = list(mongo.db.users.find({'user_type': 'instructor'}))
    # Map email to user information
    user_info_dict = {user['email']: user for user in users_info}
    
    for instructor in instructors:
        instructor['_id'] = str(instructor['_id'])
        # Update the field names to match the database
        instructor['createdAt'] = instructor.get('created_at', '').strftime('%Y-%m-%d %H:%M:%S') if instructor.get('created_at') else None
        instructor['updatedAt'] = instructor.get('updated_at', '').strftime('%Y-%m-%d %H:%M:%S') if instructor.get('updated_at') else None
        
        # Get the user information from the user info dictionary
        user_info = user_info_dict.get(instructor['email'])
        if user_info:
            instructor['first_name'] = user_info.get('first_name')
            instructor['last_name'] = user_info.get('last_name')
            instructor['role'] = user_info.get('role')
    
    # Return the instructors as a JSON response
    return jsonify(instructors)

#storefront owner list
@admin_bp.route('/get_storefrontowners', methods=['GET'])
@login_required
@no_cache
def get_storefrontowners():
    # Fetch storefront owners from the 'storefrontowner' collection
    storefrontowners = list(mongo.db.storefrontowner.find())
    # Fetch user information with user_type 'storefrontowner'
    users_info = list(mongo.db.users.find({'user_type': 'storefrontowner'}))
    # Map email to user information
    user_info_dict = {user['email']: user for user in users_info}
    
    for storefrontowner in storefrontowners:
        storefrontowner['_id'] = str(storefrontowner['_id'])
        storefrontowner['createdAt'] = storefrontowner.get('created_at', '').strftime('%Y-%m-%d %H:%M:%S') if storefrontowner.get('created_at') else None
        storefrontowner['updatedAt'] = storefrontowner.get('updated_at', '').strftime('%Y-%m-%d %H:%M:%S') if storefrontowner.get('updated_at') else None
        storefrontowner['gstin'] = storefrontowner.get('gstin', '')  # Add GSTIN field
        
        # Get the user information from the user info dictionary
        user_info = user_info_dict.get(storefrontowner['email'])
        if user_info:
            storefrontowner['first_name'] = user_info.get('first_name')
            storefrontowner['last_name'] = user_info.get('last_name')
            storefrontowner['role'] = user_info.get('role')
    
    # Return the storefront owners as a JSON response
    return jsonify(storefrontowners)

@admin_bp.route('/get_stores', methods=['GET'])
@login_required
@no_cache
def get_stores():
    stores = list(mongo.db.stores.find({}, {'store_name': 1, '_id': 0}))
    return jsonify(stores)

@admin_bp.route('/get_products', methods=['GET'])
@login_required
@no_cache
def get_products():
    products = list(mongo.db.products.find({}, {'product_name': 1, '_id': 0}))
    return jsonify(products)


@admin_bp.route('/get_admin_profile', methods=['GET'])
@login_required
@no_cache
def get_admin_profile():
    admin = current_user
    return jsonify({
        'first_name': admin.first_name,
        'last_name': admin.last_name,
        'email': admin.email
    })