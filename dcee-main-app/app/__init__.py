from flask import Flask
from flask_pymongo import PyMongo
from flask_login import LoginManager, UserMixin
from bson import ObjectId
from flask_mail import Mail
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

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
    
    # Mail configuration
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'josnamarythomas2025@mca.ajce.in'
    app.config['MAIL_PASSWORD'] = 'JOSNA#987dd'
    app.config['MAIL_DEFAULT_SENDER'] = 'josnamarythomas2025@mca.ajce.in'
    mail.init_app(app)
    
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'


    from app.routes import admin, storeowner, customer, instructor, auth
    app.register_blueprint(auth.auth_bp, url_prefix='/auth')
    app.register_blueprint(admin.admin_bp, url_prefix='/admin')
    app.register_blueprint(storeowner.storeowner_bp, url_prefix='/storeowner')
    app.register_blueprint(customer.customer_bp, url_prefix='/customer')
    app.register_blueprint(instructor.instructor_bp, url_prefix='/instructor')

    return app