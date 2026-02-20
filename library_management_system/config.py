import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'lms-secret-key-change-in-production-2024')
    
    # Database - defaults to SQLite for easy local development
    # For MySQL: set DATABASE_URL=mysql+pymysql://user:pass@host/library_db
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///library.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    # Fine per day (in Rupees)
    FINE_PER_DAY = 2

    # Max borrow days
    BORROW_DAYS = 14

    # Max books a member can borrow at once
    MAX_BORROW_LIMIT = 3
