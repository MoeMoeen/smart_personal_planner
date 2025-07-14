"""Configuration settings for the Smart Personal Planner application."""

import os
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseModel):
    """Application configuration settings."""
    
    # Database configuration
    database_url: str = Field(
        default="sqlite:///./smart_planner.db",
        description="Database connection URL"
    )
    
    # API configuration
    api_title: str = Field(
        default="Smart Personal Planner API",
        description="API title"
    )
    
    api_version: str = Field(
        default="1.0.0",
        description="API version"
    )
    
    # OpenAI configuration
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key for AI features"
    )
    
    openai_model: str = Field(
        default="gpt-4",
        description="OpenAI model to use"
    )
    
    # Application settings
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    
    def __init__(self, **kwargs):
        # Load values from environment variables
        env_values = {
            'database_url': os.getenv('DATABASE_URL', 'sqlite:///./smart_planner.db'),
            'api_title': os.getenv('API_TITLE', 'Smart Personal Planner API'),
            'api_version': os.getenv('API_VERSION', '1.0.0'),
            'openai_api_key': os.getenv('OPENAI_API_KEY'),
            'openai_model': os.getenv('OPENAI_MODEL', 'gpt-4'),
            'debug': os.getenv('DEBUG', 'false').lower() == 'true'
        }
        
        # Merge with provided kwargs
        env_values.update(kwargs)
        super().__init__(**env_values)


# Create a global settings instance
settings = Settings()