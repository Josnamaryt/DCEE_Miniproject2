from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from flask_login import login_required, current_user
from app import mongo  # Import mongo from your app package
from bson import ObjectId  # Import ObjectId for proper ID handling


customer_bp = Blueprint('customer', __name__)

@customer_bp.route('/dashboard')
@login_required
def dashboard():
    # Fetch all stores from the database
    stores = list(mongo.db.stores.find({}, {'name': 1}))
    
    # Sample featured products for different store types
    featured_products = [
        {"name": "Vanilla Ice Cream", "image": "ice_cream_vanilla.jpg", "store_type": "Ice Cream Parlour"},
        {"name": "Chocolate Ice Cream", "image": "ice_cream_chocolate.jpg", "store_type": "Ice Cream Parlour"},
        {"name": "Fresh Apples", "image": "apples.jpg", "store_type": "Grocery Store"},
        {"name": "Whole Wheat Bread", "image": "bread.jpg", "store_type": "Grocery Store"},
        {"name": "Latest Smartphone", "image": "smartphone.jpg", "store_type": "Mobile Shop"},
        {"name": "Wireless Earbuds", "image": "earbuds.jpg", "store_type": "Mobile Shop"},
    ]
    
    return render_template('customer/dashboard.html', user=current_user, stores=stores, featured_products=featured_products)

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
            '_id': str(product['_id']),  # Convert ObjectId to string
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

@customer_bp.route('/add_to_cart/<product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    try:
        data = request.json
        quantity = int(data.get('quantity', 1))
        product = mongo.db.products.find_one({"_id": ObjectId(product_id)})
        
        if not product:
            return jsonify({"success": False, "message": "Product not found"}), 404
        
        if quantity > product['product_quantity']:
            return jsonify({"success": False, "message": "Requested quantity exceeds available stock"}), 400
        
        email = current_user.email
        existing_item = mongo.db.cart.find_one({"email": email, "product_id": str(product_id)})
        
        if existing_item:
            new_quantity = existing_item['quantity'] + quantity
            if new_quantity > product['product_quantity']:
                return jsonify({"success": False, "message": "Requested quantity exceeds available stock"}), 400
            
            mongo.db.cart.update_one(
                {"email": email, "product_id": str(product_id)},
                {"$set": {"quantity": new_quantity}}
            )
        else:
            cart_item = {
                "email": email,
                "product_id": str(product_id),
                "quantity": quantity
            }
            mongo.db.cart.insert_one(cart_item)
        
        return jsonify({"success": True, "message": "Product added to cart"})
    except Exception as e:
        print(f"Error adding to cart: {str(e)}")
        return jsonify({"success": False, "message": "An error occurred"}), 500

        
@customer_bp.route('/view_cart')
@login_required
def view_cart():
    cart_items = []
    total = 0
    email = current_user.email
    cart_data = mongo.db.cart.find({"email": email})
    
    for item in cart_data:
        product = mongo.db.products.find_one({"_id": ObjectId(item['product_id'])})
        if product:
            item_total = float(product['product_price']) * item['quantity']
            cart_items.append({
                'product': product,
                'quantity': item['quantity'],
                'item_total': item_total
            })
            total += item_total
    
    return render_template('customer/cart.html', cart_items=cart_items, total=total)

@customer_bp.route('/update_cart/<product_id>', methods=['POST'])
@login_required

def update_cart(product_id):
    try:
        data = request.json
        new_quantity = int(data.get('quantity', 0))
        
        product = mongo.db.products.find_one({"_id": ObjectId(product_id)})
        if not product:
            return jsonify({"success": False, "message": "Product not found"}), 404
        
        email = current_user.email
        cart_item = mongo.db.cart.find_one({"email": email, "product_id": str(product_id)})
        
        if not cart_item:
            return jsonify({"success": False, "message": "Item not found in cart"}), 404
        
        if new_quantity < 1:
            return jsonify({"success": False, "message": "Quantity cannot be less than 1"}), 400
        
        if new_quantity > product['product_quantity']:
            return jsonify({"success": False, "message": f"Available stock is {product['product_quantity']}"}), 400
        
        mongo.db.cart.update_one(
            {"email": email, "product_id": str(product_id)},
            {"$set": {"quantity": new_quantity}}
        )
        
        return jsonify({"success": True, "message": "Cart updated successfully", "new_quantity": new_quantity})
    except Exception as e:
        print(f"Error updating cart: {str(e)}")
        return jsonify({"success": False, "message": "An error occurred"}), 500

@customer_bp.route('/remove_from_cart/<product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    email = current_user.email
    result = mongo.db.cart.delete_one({"email": email, "product_id": product_id})
    
    if result.deleted_count > 0:
        return jsonify({"success": True, "message": "Item removed from cart successfully"})
    else:
        return jsonify({"success": False, "message": "Failed to remove item from cart"}), 400

@customer_bp.route('/get_cart_count')
@login_required
def get_cart_count():
    cart = session.get('cart', {})
    count = sum(cart.values())
    return jsonify({"count": count})

@customer_bp.route('/get_cart_info')
@login_required
def get_cart_info():
    email = current_user.email
    cart_data = mongo.db.cart.find({"email": email})
    count = 0
    subtotal = 0
    for item in cart_data:
        product = mongo.db.products.find_one({"_id": ObjectId(item['product_id'])})
        if product:
            count += item['quantity']
            subtotal += float(product['product_price']) * item['quantity']
    return jsonify({"count": count, "subtotal": subtotal})

@customer_bp.route('/debug_session')
def debug_session():
    return jsonify(dict(session))

@customer_bp.route('/checkout')
@login_required
def checkout():
    cart_items = []
    total = 0
    email = current_user.email
    cart_data = mongo.db.cart.find({"email": email})
    
    for item in cart_data:
        product = mongo.db.products.find_one({"_id": ObjectId(item['product_id'])})
        if product:
            item_total = float(product['product_price']) * item['quantity']
            cart_items.append({
                'product': product,
                'quantity': item['quantity'],
                'item_total': item_total
            })
            total += item_total
    
    return render_template('customer/checkout.html', cart_items=cart_items, total=total)

@customer_bp.route('/save_address', methods=['POST'])
@login_required
def save_address():
    try:
        address_data = request.json
        address_data['user_id'] = str(current_user.id)
        
        # Save the address to the database
        result = mongo.db.addresses.update_one(
            {'user_id': str(current_user.id)},
            {'$set': address_data},
            upsert=True
        )

        if result.acknowledged:
            return jsonify({"success": True, "message": "Address saved successfully"})
        else:
            return jsonify({"success": False, "message": "Failed to save address"}), 400
    except Exception as e:
        print(f"Error saving address: {str(e)}")
        return jsonify({"success": False, "message": "An error occurred"}), 500