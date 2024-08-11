from flask import Blueprint, render_template
from flask_login import login_required, current_user

customer_bp = Blueprint('customer', __name__)

@customer_bp.route('/dashboard')
@login_required
def dashboard():
    # Create a dictionary with the user information we need
    # user_data = {
    #     'name': current_user.name,  # Assuming there's a 'name' attribute
    #     'email': current_user.email,
    #     'role': 'Customer'  # Or use a role attribute if available on your user object
    # }
    
    return render_template('customer/dashboard.html')