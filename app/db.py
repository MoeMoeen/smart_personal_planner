# app/db.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
from app.models import Base  # ✅ Import the same Base defined in models.py
from typing import Generator
from sqlalchemy.orm import Session

# Load environment variables from .env
load_dotenv()

# Get the database URL from .env
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
	raise ValueError("DATABASE_URL environment variable is not set.")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create a session factory for database access
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Generator function to provide a database session
def get_db() -> Generator[Session, None, None]: 
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
