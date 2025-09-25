import os

class Config:
    PORT = 8010
    FLASK_ENV = os.environ.get("FLASK_ENV", "development")
    DEBUG = os.environ.get("DEBUG", "True").lower() == "true"
    SECRET_KEY = os.environ.get("SECRET_KEY", "super-secret-content-key")

    # SQLite Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///content.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # CORS settings
    CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "*").split(",")

class DevelopmentConfig(Config):
    DEBUG = True
    FLASK_ENV = "development"
    SQLALCHEMY_DATABASE_URI = "sqlite:///content.db"

class ProductionConfig(Config):
    DEBUG = False
    FLASK_ENV = "production"
    SQLALCHEMY_DATABASE_URI = "sqlite:///data/content.db" # For persistent volume in Cloud Run

def get_config():
    if os.environ.get("FLASK_ENV") == "production":
        return ProductionConfig
    return DevelopmentConfig

