from flask import Flask
from flask_pymongo import PyMongo
from flask_login import LoginManager, UserMixin
from bson import ObjectId
from flask_mail import Mail

mongo = PyMongo()
login_manager = LoginManager()
mail = Mail()

def create_app(config_class='config.DevelopmentConfig'):
    app = Flask(__name__)
    app.config.from_object(config_class)

    try:
        mongo.init_app(app)
    except Exception as e:
        print(f"Error initializing Flask-PyMongo: {str(e)}")
    
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'


    from app.routes import admin, storeowner, customer, instructor, auth
    app.register_blueprint(auth.auth_bp, url_prefix='/auth')
    app.register_blueprint(admin.admin_bp, url_prefix='/admin')
    app.register_blueprint(storeowner.storeowner_bp, url_prefix='/storeowner')
    app.register_blueprint(customer.customer_bp, url_prefix='/customer')
    app.register_blueprint(instructor.instructor_bp, url_prefix='/instructor')

    return app
