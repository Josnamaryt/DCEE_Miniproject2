from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required
from app import login_manager, mongo

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard', methods=['POST', 'GET'])
def dashboard():
    print("getting inside dashboard")  # debugging
    return render_template('admin/dashboard.html')

# customers list view
@admin_bp.route('/get_customers', methods=['GET'])
@login_required
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
