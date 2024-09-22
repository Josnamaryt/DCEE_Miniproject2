from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash, make_response, current_app
from flask_login import login_required, current_user
from app import mongo  # Import mongo from your app package
from bson import ObjectId  # Import ObjectId for proper ID handling
import razorpay
import logging
import os
from dotenv import load_dotenv

customer_bp = Blueprint('customer', __name__)

load_dotenv()
razorpay_client = razorpay.Client(auth=(os.environ.get('RAZORPAY_KEY_ID'), os.environ.get('RAZORPAY_SECRET_KEY')))

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
    print(f"Fetching store details for owner ID: {store_owner_id}")
    store_data = mongo.db.stores.find_one({"store_owner_id": store_owner_id})
    product_data = []
    products = mongo.db.products.find({"store_owner_id": store_owner_id})
    for product in products:
        image_path = product.get('product_image', '')
        print(f"Original image path: {image_path}")
        if image_path:
            # Replace backslashes with forward slashes and remove 'product_images' from the start
            image_path = image_path.replace('\\', '/').lstrip('product_images/')
            # Generate the correct URL for the image
            image_url = url_for('static', filename=f'images/product/product_images/{image_path}')
            print(f"Generated image URL: {image_url}")
        else:
            image_url = url_for('static', filename='images/placeholder.jpg')
        
        product_data.append({
            '_id': str(product['_id']),
            'product_name': product.get('product_name', ''),
            'product_price': product.get('product_price', ''),
            'product_status': product.get('product_status', ''),
            'product_quantity': product.get('product_quantity', ''),
            'product_description': product.get('product_description', ''),
            'product_image': image_url
        })
    print(f"Number of products found: {len(product_data)}")
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
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
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
    
    response = make_response(render_template('customer/cart.html', cart_items=cart_items, total=total))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

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
    
    return render_template('customer/checkout.html', cart_items=cart_items, total=total, razorpay_key_id="rzp_test_p9ccnzVHbdWZkL")

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

@customer_bp.route('/create_order', methods=['POST'])
@login_required
def create_order():
    try:
        amount = request.json.get('amount')
        order_currency = 'INR'
        
        # Create Razorpay Order
        razorpay_order = razorpay_client.order.create(dict(
            amount=amount,
            currency=order_currency,
            payment_capture='0'
        ))
        
        # Save order details to your database here
        
        return jsonify({
            'success': True,
            'order_id': razorpay_order['id']
        })
    except Exception as e:
        current_app.logger.error(f"Error creating Razorpay order: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@customer_bp.route('/payment_success', methods=['POST'])
@login_required
def payment_success():
    # Verify the payment signature
    params_dict = {
        'razorpay_payment_id': request.json.get('razorpay_payment_id'),
        'razorpay_order_id': request.json.get('razorpay_order_id'),
        'razorpay_signature': request.json.get('razorpay_signature')
    }
    
    try:
        razorpay_client.utility.verify_payment_signature(params_dict)
    except:
        return jsonify({'success': False})
    
    # If verification is successful, you can update your database to mark the order as paid
    # Also, you can clear the user's cart here
    
    return jsonify({'success': True})

@customer_bp.route('/order_confirmation')
@login_required
def order_confirmation():
    # Fetch the latest order for the current user
    order = mongo.db.orders.find_one(
        {"user_id": current_user.id},
        sort=[("date", -1)]
    )
    
    if not order:
        # Handle case where no order is found
        flash("No recent order found.", "error")
        return redirect(url_for('customer.stores'))
    
    # Format the order data for the template
    formatted_order = {
        "id": str(order["_id"]),
        "date": order["date"].strftime("%Y-%m-%d %H:%M:%S"),
        "total": order["total"],
        "items": order["items"],
        "address": order["address"]
    }
    
    return render_template('customer/order_confirmation.html', order=formatted_order)

@customer_bp.route('/orders')
@login_required
def orders():
    # Logic to fetch order details
    orders = get_orders_for_user(current_user.id)  # Example function to get orders
    return render_template('customer/orders.html', orders=orders)

@customer_bp.route('/get_product_details/<product_id>')
@login_required
def get_product_details(product_id):
    product = mongo.db.products.find_one({"_id": ObjectId(product_id)})
    if product:
        image_path = product.get('product_image', '')
        if image_path:
            # Replace backslashes with forward slashes and remove 'product_images' from the start
            image_path = image_path.replace('\\', '/').lstrip('product_images/')
            image_url = url_for('static', filename=f'images/product/product_images/{image_path}')
        else:
            image_url = url_for('static', filename='images/placeholder.jpg')
        
        return jsonify({
            'product_name': product.get('product_name', ''),
            'product_price': product.get('product_price', ''),
            'product_status': product.get('product_status', ''),
            'product_quantity': product.get('product_quantity', ''),
            'product_description': product.get('product_description', ''),
            'product_image': image_url
        })
    else:
        return jsonify({'error': 'Product not found'}), 404