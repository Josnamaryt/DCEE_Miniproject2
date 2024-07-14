from flask import Blueprint, render_template, redirect, url_for, request, flash
# from flask_login import login_user, logout_user, login_required 
# from app import login_manager

storeowner_bp = Blueprint('storeowner', __name__)