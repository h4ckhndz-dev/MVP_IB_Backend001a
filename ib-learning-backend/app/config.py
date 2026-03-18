## app/config.py (Configuration)

"""
Configuration and environment variables
"""

from typing import List
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    # App
    APP_NAME: str = "IB Learning Community"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "False") == "True"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    DATABASE_ECHO: bool = os.getenv("DATABASE_ECHO", "False") == "True"
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:5173",  # Vite dev server
    ]
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # File Storage
    STORAGE_BUCKET: str = "student-submissions"
    MAX_FILE_SIZE_MB: int = 100
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
