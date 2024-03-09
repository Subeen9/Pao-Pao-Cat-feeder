import os
import secrets

class Config:
    # Set the secret key from the environment variable or use a default value
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'default_secret_key') or secrets.token_hex(16) 