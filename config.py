"""
Configuration for Flask app - handles environment-based settings
"""
import os
from urllib.parse import urlparse

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database configuration
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    # Google Cloud detection
    K_SERVICE = os.environ.get('K_SERVICE')  # Cloud Run service name
    GOOGLE_CLOUD_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT')
    
    @property
    def is_production(self):
        """Check if running in production"""
        return self.DATABASE_URL is not None or self.is_gcp
    
    @property
    def is_gcp(self):
        """Check if running on Google Cloud"""
        return self.K_SERVICE is not None or self.GOOGLE_CLOUD_PROJECT is not None
    
    @property
    def database_type(self):
        """Get database type (sqlite, postgresql, or firestore)"""
        # Google Cloud Run uses Firestore by default
        if self.is_gcp and not self.DATABASE_URL:
            return 'firestore'
        elif self.DATABASE_URL:
            # Render or other platforms with PostgreSQL
            return 'postgresql'
        return 'sqlite'
    
    @property
    def sqlalchemy_database_uri(self):
        """Get SQLAlchemy-compatible database URI"""
        if self.DATABASE_URL:
            # Fix for Render's postgres:// vs postgresql://
            url = self.DATABASE_URL
            if url.startswith('postgres://'):
                url = url.replace('postgres://', 'postgresql://', 1)
            return url
        return 'sqlite:///woolies_preferences.db'
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    
    # Flask Configuration
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    TESTING = False
    
    # Session Configuration
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour

config = Config()
