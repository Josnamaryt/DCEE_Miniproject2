import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb+srv://dceedb:dceedb@dcee-cluster.xi5arq8.mongodb.net/dceedb'

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
