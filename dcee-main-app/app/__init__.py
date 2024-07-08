from flask import Flask
# from flask_login import LoginManager
# from flask_pymongo import PyMongo
from app.routes import auth

# login_manager = LoginManager()
def create_app(config_class = 'config.DevelopmentConfig'):
    app = Flask(__name__)
    app.config.from_object(config_class)
    # login_manager.init_app(app)
    app.register_blueprint(auth.auth_bp, url_prefix = '/auth')
    return app
    
