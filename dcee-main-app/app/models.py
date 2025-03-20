from flask_login import UserMixin
from app import mongo
from bson import ObjectId
from datetime import datetime

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.email = user_data.get('email', '')
        self.first_name = user_data.get('first_name', '')
        self.last_name = user_data.get('last_name', '')
        self.password_hash = user_data['password']
        self.role = user_data['role']
        self.status = user_data['status']

    def get_id(self):
        return self.id

    @staticmethod
    def get(user_id):
        user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        if not user_data:
            return None
        return User(user_data)

class Sale:
    def __init__(self, product_id, product_name, store_owner_id, quantity, revenue, sale_date=None, customer_id=None):
        self.product_id = product_id
        self.product_name = product_name
        self.store_owner_id = store_owner_id
        self.quantity = quantity
        self.revenue = revenue
        self.sale_date = sale_date or datetime.now()
        self.customer_id = customer_id
    
    def to_dict(self):
        return {
            'product_id': self.product_id,
            'product_name': self.product_name,
            'store_owner_id': self.store_owner_id,
            'quantity': self.quantity,
            'revenue': self.revenue,
            'sale_date': self.sale_date,
            'customer_id': self.customer_id
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            product_id=data.get('product_id'),
            product_name=data.get('product_name'),
            store_owner_id=data.get('store_owner_id'),
            quantity=data.get('quantity'),
            revenue=data.get('revenue'),
            sale_date=data.get('sale_date'),
            customer_id=data.get('customer_id')
        )