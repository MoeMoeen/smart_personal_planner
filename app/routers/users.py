# app/routers/users.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt  # Correct import for JWT functionality
import os

from app import schemas
from app.crud import crud
from app.db.db import get_db
from app.models import User

# Security setup
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "INSECURE-DEV-KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

router = APIRouter(
    prefix="/users",
    tags=["users", "authentication"]
)

# === UTILITY FUNCTIONS ===

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and return user_id"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[int] = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_id
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials", 
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[int] = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        user_id = int(user_id)  # Convert to int if it's a string
    except (JWTError, ValueError):
        raise credentials_exception
    
    user = crud.get_user_by_id(db, user_id=user_id)
    if user is None:
        raise credentials_exception
    return user

# === AUTHENTICATION ENDPOINTS ===

@router.post("/register", response_model=schemas.UserRead)
def register_user(
    user_data: schemas.UserCreate,
    db: Session = Depends(get_db)
) -> schemas.UserRead:
    """
    Register a new user with email and password.
    """
    # Check if user already exists
    if user_data.email:
        existing_user = crud.get_user_by_email(db, user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Validate password is provided for email/password registration
    if not user_data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required for registration"
        )
    
    # Hash the password
    hashed_password = get_password_hash(user_data.password)
    
    # Create user
    db_user = crud.create_user(db, user_data, hashed_password)
    return db_user

@router.post("/login", response_model=schemas.TokenResponse)
def login_user(
    login_data: schemas.UserLogin,
    db: Session = Depends(get_db)
) -> schemas.TokenResponse:
    """
    Authenticate user and return access token.
    """
    # Get user by email
    user = crud.get_user_by_email(db, login_data.email)
    user_has_password = user and user.hashed_password is not None
    if not user or not user_has_password or not verify_password(login_data.password, str(user.hashed_password)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return schemas.TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id  # type: ignore
    )

# === USER MANAGEMENT ENDPOINTS ===

@router.get("/me", response_model=schemas.UserRead)
def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> schemas.UserRead:
    """
    Get current user's information.
    """
    return current_user

@router.put("/me", response_model=schemas.UserRead)
def update_current_user(
    user_updates: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> schemas.UserRead:
    """
    Update current user's information.
    """
    updated_user = crud.update_user(db, current_user.id, user_updates)  # type: ignore
    return updated_user

@router.delete("/me", response_model=schemas.UserRead)
def delete_current_user(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> schemas.UserRead:
    """
    Delete current user's account.
    """
    deleted_user = crud.delete_user(db, current_user.id)  # type: ignore
    return deleted_user

# === ADMIN ENDPOINTS (Optional - for user management) ===

@router.get("/{user_id}", response_model=schemas.UserRead)
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> schemas.UserRead:
    """
    Get user by ID. Users can only view their own profile unless admin.
    """
    # Simple authorization: users can only view their own profile
    if int(current_user.id) != user_id:  # type: ignore
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user"
        )
    
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

# === TELEGRAM INTEGRATION ENDPOINTS ===

@router.post("/telegram/link", response_model=schemas.UserRead)
def link_telegram_account(
    telegram_data: schemas.TelegramLinkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> schemas.UserRead:
    """
    Link a Telegram account to the current user.
    """
    # Check if Telegram user ID is already linked to another account
    existing_telegram_user = crud.get_user_by_telegram_id(db, telegram_data.telegram_user_id)
    if existing_telegram_user and int(existing_telegram_user.id) != int(current_user.id):  # type: ignore
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram account already linked to another user"
        )
    
    # Update current user with Telegram information
    telegram_update = schemas.UserUpdate(
        telegram_user_id=telegram_data.telegram_user_id,
        username=telegram_data.username,
        first_name=telegram_data.first_name,
        last_name=telegram_data.last_name,
        email=None  # Keep existing email
    )
    
    updated_user = crud.update_user(db, current_user.id, telegram_update)  # type: ignore
    return updated_user

@router.post("/telegram/create", response_model=schemas.UserRead)
def create_telegram_user(
    telegram_data: schemas.TelegramUserCreate,
    db: Session = Depends(get_db)
) -> schemas.UserRead:
    """
    Create a new user from Telegram data (used by Telegram bot).
    This endpoint doesn't require authentication since it's called by the bot.
    """
    # Check if Telegram user already exists
    existing_user = crud.get_user_by_telegram_id(db, telegram_data.telegram_user_id)
    if existing_user:
        return existing_user
    
    # Create new user with Telegram data
    user_create = schemas.UserCreate(
        email=None,  # No email for Telegram users
        username=telegram_data.username or f"user_{telegram_data.telegram_user_id}",
        first_name=telegram_data.first_name,
        last_name=telegram_data.last_name,
        password=None,  # No password for Telegram users
        telegram_user_id=telegram_data.telegram_user_id
    )
    
    db_user = crud.create_telegram_user(db, user_create)
    return db_user

# === PASSWORD MANAGEMENT ===

@router.post("/change-password")
def change_password(
    password_data: schemas.PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Change user's password.
    """
    # Verify current password
    user_has_password = current_user.hashed_password is not None
    if not user_has_password or not verify_password(password_data.current_password, str(current_user.hashed_password)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    # Hash new password
    new_hashed_password = get_password_hash(password_data.new_password)
    
    # Update password
    crud.update_user_password(db, current_user.id, new_hashed_password)  # type: ignore
    
    return {"message": "Password changed successfully"}

# === UTILITY ENDPOINT FOR TESTING ===

@router.post("/test-user", response_model=schemas.UserRead)
def create_test_user(
    db: Session = Depends(get_db)
) -> schemas.UserRead:
    """
    Create a test user for development/testing purposes.
    ⚠️ Remove this endpoint in production!
    """
    # Check if test user already exists
    existing_user = crud.get_user_by_email(db, "test@example.com")
    if existing_user:
        return existing_user
    
    # Create test user
    test_user_data = schemas.UserCreate(
        email="test@example.com",
        username="test_user",
        first_name="Test",
        last_name="User",
        password="test123",
        telegram_user_id=None
    )
    
    # Ensure password is not None
    if not test_user_data.password:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Test user password is required"
        )
    
    hashed_password = get_password_hash(test_user_data.password)
    db_user = crud.create_user(db, test_user_data, hashed_password)
    
    return db_user
