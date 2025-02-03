from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, SecurityScopes
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import Optional
import random
import string

from app.database import get_db
from app.models.models import User
from app.schemas.schemas import UserCreate, User as UserSchema, Token, UserUpdate, EmailSchema, VerifyOTPSchema, ResetPasswordSchema, Message
from app.config import settings
from app.services import email_service

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token",
    scheme_name="JWT"
)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(security_scopes: SecurityScopes, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

@router.post("/signup", response_model=UserSchema, description="Register a new user")
async def signup(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        name=user.name,
        hashed_password=hashed_password,
        total_tokens=10000,  # Give 10,000 tokens by default
        used_tokens=0
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/token", response_model=Token, description="Login to get access token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserSchema, description="Get current user information")
async def get_user_info(current_user: User = Security(get_current_user, scopes=[])):
    return current_user

@router.put("/me", response_model=UserSchema, description="Update user's name")
async def update_user(
    user_update: UserUpdate,
    current_user: User = Security(get_current_user, scopes=[]),
    db: Session = Depends(get_db)
):
    # Update user's name
    current_user.name = user_update.name
    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/forgot-password", response_model=Message)
async def forgot_password(email: EmailSchema, db: Session = Depends(get_db)):
    """
    Send password reset OTP to user's email
    """
    user = db.query(User).filter(User.email == email.email).first()
    if not user:
        # Return success even if user doesn't exist to prevent email enumeration
        return {"message": "If the email exists, you will receive a password reset OTP"}
    
    # Generate 6-digit OTP
    otp = ''.join(random.choices(string.digits, k=6))
    print(email.email)
    
    # Set OTP and expiry in database
    user.reset_otp = otp
    user.reset_otp_expiry = datetime.utcnow() + timedelta(minutes=10)
    db.commit()
    
    # Send OTP email
    email_sent = email_service.send_reset_password_email(email.email, otp)
    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send reset email"
        )
    
    return {"message": "If the email exists, you will receive a password reset OTP"}

@router.post("/verify-otp", response_model=Message)
async def verify_reset_otp(verify_data: VerifyOTPSchema, db: Session = Depends(get_db)):
    """
    Verify the OTP provided by the user
    """
    user = db.query(User).filter(User.email == verify_data.email).first()
    if not user or not user.reset_otp or user.reset_otp != verify_data.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP"
        )
    
    if not user.reset_otp_expiry or user.reset_otp_expiry < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired"
        )
    
    return {"message": "OTP verified successfully"}

@router.post("/reset-password", response_model=Message)
async def reset_password(reset_data: ResetPasswordSchema, db: Session = Depends(get_db)):
    """
    Reset user's password after OTP verification
    """
    user = db.query(User).filter(User.email == reset_data.email).first()
    if not user or not user.reset_otp or user.reset_otp != reset_data.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP"
        )
    
    if not user.reset_otp_expiry or user.reset_otp_expiry < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired"
        )
    
    if len(reset_data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long"
        )
    
    # Update password
    user.hashed_password = pwd_context.hash(reset_data.new_password)
    # Clear OTP fields
    user.reset_otp = None
    user.reset_otp_expiry = None
    db.commit()
    
    return {"message": "Password reset successfully"} 