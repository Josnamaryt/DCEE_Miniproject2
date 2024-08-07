from flask_login import UserMixin
from app import mongo
from bson import ObjectId

class User(UserMixin):
    def __init__(self, _id, email, password_hash, role, status, *args, **kwargs):
        self.id = str(_id)
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.status = status

    def get_id(self):
        return self.id

    @staticmethod
    def get(user_id):
        user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        if not user:
            return None
        return User(
            _id=user['_id'],
            email=user['email'],
            password_hash=user['password'],
            role=user['role'],
            status=user['status']
        )
