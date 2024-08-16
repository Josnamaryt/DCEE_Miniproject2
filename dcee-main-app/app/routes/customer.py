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
        product = mongo.db.products.find_one({"_id": ObjectId(product_id)})
        if product:
            cart = session.get('cart', {})
            cart[str(product_id)] = cart.get(str(product_id), 0) + 1
            session['cart'] = cart
            return jsonify({"success": True, "message": "Product added to cart"})
        return jsonify({"success": False, "message": "Product not found"}), 404
    except Exception as e:
        print(f"Error adding to cart: {str(e)}")
        return jsonify({"success": False, "message": "An error occurred"}), 500

@customer_bp.route('/view_cart')
@login_required
def view_cart():
    cart = session.get('cart', {})
    cart_items = []
    total = 0
    for product_id, quantity in cart.items():
        product = mongo.db.products.find_one({"_id": ObjectId(product_id)})
        if product:
            item_total = float(product['product_price']) * quantity
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'item_total': item_total
            })
            total += item_total
    return render_template('customer/cart.html', cart_items=cart_items, total=total)

@customer_bp.route('/update_cart/<product_id>', methods=['POST'])
@login_required
def update_cart(product_id):
    cart = session.get('cart', {})
    change = int(request.json.get('change', 0))
    
    if product_id in cart:
        cart[product_id] += change
        if cart[product_id] <= 0:
            del cart[product_id]
    
    session['cart'] = cart
    return jsonify({"success": True, "message": "Cart updated successfully"})

@customer_bp.route('/remove_from_cart/<product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    if product_id in cart:
        del cart[product_id]
    
    session['cart'] = cart
    return jsonify({"success": True, "message": "Item removed from cart successfully"})

@customer_bp.route('/get_cart_count')
@login_required
def get_cart_count():
    cart = session.get('cart', {})
    count = sum(cart.values())
    return jsonify({"count": count})

@customer_bp.route('/get_cart_info')
@login_required
def get_cart_info():
    cart = session.get('cart', {})
    count = sum(cart.values())
    subtotal = 0
    for product_id, quantity in cart.items():
        product = mongo.db.products.find_one({"_id": ObjectId(product_id)})
        if product:
            subtotal += float(product['product_price']) * quantity
    return jsonify({"count": count, "subtotal": subtotal})

@customer_bp.route('/debug_session')
def debug_session():
    return jsonify(dict(session))