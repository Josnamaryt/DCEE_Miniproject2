"""
Models package initialization file.

This file re-exports models from the parent models.py file to maintain compatibility.
"""
# Import path handling
import os
import importlib.util

# Get the absolute path to the models.py file
models_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models.py')

# Load the models.py module
spec = importlib.util.spec_from_file_location('parent_models', models_path)
parent_models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parent_models)

# Import the classes from the loaded module
User = parent_models.User
Sale = parent_models.Sale

# Export these classes
__all__ = ['User', 'Sale']

# This file is intentionally left mostly empty to make the directory a proper Python package. 