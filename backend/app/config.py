"""Configuration management using Pydantic settings."""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Gmail API
    gmail_credentials_file: str = "credentials.json"
    gmail_token_file: str = "token.json"
    
    # Ollama
    ollama_model: str = "llama3"
    ollama_base_url: str = "http://localhost:11434"
    
    # Database
    database_url: str = "sqlite:///./job_tracker.db"
    
    # Application
    sync_interval_minutes: int = 30
    max_emails_per_sync: int = 50
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
