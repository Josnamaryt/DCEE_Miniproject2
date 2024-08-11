from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import mongo  # Import mongo from your app package
from bson import ObjectId  # Import ObjectId for proper ID handling


customer_bp = Blueprint('customer', __name__)

@customer_bp.route('/dashboard')
@login_required
def dashboard():
    # Fetch all stores from the database
    stores = list(mongo.db.stores.find({}, {'name': 1}))
    return render_template('customer/dashboard.html', user=current_user, stores=stores)

@customer_bp.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    data = request.json
    try:
        result = mongo.db.users.update_one(
            {"_id": ObjectId(current_user.id)},
            {"$set": {
                "first_name": data['first_name'],
                "last_name": data['last_name'],
                "email": data['email']
            }}
        )
        if result.modified_count > 0:
            return jsonify({"success": True, "message": "Profile updated successfully"})
        else:
            return jsonify({"success": False, "message": "No changes were made"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@customer_bp.route('/get_profile', methods=['GET'])
@login_required
def get_profile():
    user_data = mongo.db.users.find_one({"_id": ObjectId(current_user.id)})
    if user_data:
        profile_data = {
            'first_name': user_data.get('first_name', ''),
            'last_name': user_data.get('last_name', ''),
            'email': user_data.get('email', '')
        }
        return jsonify({'success': True, 'data': profile_data})
    else:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    

@customer_bp.route('/stores', methods=['GET', 'POST'])
@login_required
def stores():
    if request.method == 'GET':
        user_data = mongo.db.users.find_one({"_id": ObjectId(current_user.id)})
        stores = mongo.db.stores.find()
        store_data = []
        for store in stores:
            store_data.append({
            'store_name': store.get('store_name', ''),
            'store_type': store.get('store_type', ''),
            'store_address': store.get('store_address', ''),
            'store_gstin': store.get('store_gstin', ''),
            'store_owner_id': store.get('store_owner_id', '')
            })
        print(store_data)
        return render_template('customer/stores.html', user=user_data, stores=store_data)

@customer_bp.route('/store_details/<store_owner_id>', methods=['GET'])
@login_required
def store_details(store_owner_id):
    store_data = mongo.db.stores.find_one({"store_owner_id": store_owner_id})
    print(store_data)
    product_data = []
    products = mongo.db.products.find({"store_owner_id": store_owner_id})
    for product in products:
        product_data.append({
            'product_name': product.get('product_name', ''),
            'product_price': product.get('product_price', ''),
            'product_status': product.get('product_status', ''),
            'product_quantity': product.get('product_quantity', '')
        })
        print(product_data)
    if store_data:
        return render_template('customer/store_details.html', store=store_data, product_data=product_data)
    else:
        return 'Store not found', 404