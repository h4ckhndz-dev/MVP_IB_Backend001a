# app/routes/auth.py
"""
Authentication routes
- POST /api/v1/auth/register - Register new user
- POST /api/v1/auth/login - Login user
- POST /api/v1/auth/refresh - Refresh access token
- POST /api/v1/auth/logout - Logout user
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.auth import (
    authenticate_user,
    hash_password,
    create_tokens,
    get_current_user,
    refresh_access_token,
)
from app.models import User, Student, Teacher
from app.schemas.user import (
    UserRegister,
    UserLogin,
    TokenResponse,
    TokenRefresh,
    AuthResponse,
    UserResponse,
)
from app.schemas.common import SuccessResponse, ErrorResponse, CreatedResponse
from uuid import uuid4
from datetime import datetime

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# ============================================================================
# POST /api/v1/auth/register
# ============================================================================

@router.post("/register", response_model=CreatedResponse)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new user (student, teacher, or admin)
    
    Args:
        user_data: Registration data with email, password, user_type, community_id
    
    Returns:
        CreatedResponse with new user info and tokens
    """
    try:
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create base user
        user_id = uuid4()
        new_user = User(
            user_id=user_id,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            email=user_data.email,
            password_hash=hash_password(user_data.password),
            user_type=user_data.user_type,
            learning_community_id=user_data.community_id,
            primary_language=user_data.primary_language,
            account_status='active',
            is_active=True,
            created_date=datetime.utcnow()
        )
        
        db.add(new_user)
        db.flush()  # Get the user_id before committing
        
        # Create student or teacher record based on user_type
        if user_data.user_type == 'student':
            student = Student(
                student_id=uuid4(),
                user_id=user_id,
                grade_level=0,  # Default, can be updated later
                enrollment_status='current'
            )
            db.add(student)
        
        elif user_data.user_type == 'teacher':
            teacher = Teacher(
                teacher_id=uuid4(),
                user_id=user_id,
                employment_status='full-time'
            )
            db.add(teacher)
        
        db.commit()
        
        # Create tokens
        tokens = create_tokens(str(user_id))
        
        # Build response
        user_response = UserResponse(
            user_id=new_user.user_id,
            first_name=new_user.first_name,
            last_name=new_user.last_name,
            email=new_user.email,
            primary_language=new_user.primary_language,
            user_type=new_user.user_type,
            account_status=new_user.account_status,
            is_active=new_user.is_active,
            created_date=new_user.created_date
        )
        
        return CreatedResponse(
            status="created",
            message="User registered successfully",
            data={
                "user": user_response,
                "token": TokenResponse(**tokens)
            }
        )
    
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please check your data."
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration error: {str(e)}"
        )

# ============================================================================
# POST /api/v1/auth/login
# ============================================================================

@router.post("/login", response_model=SuccessResponse)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login user with email and password
    
    Args:
        credentials: Email and password
    
    Returns:
        SuccessResponse with user info and tokens
    """
    # Authenticate user
    user = authenticate_user(db, credentials.email, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create tokens
    tokens = create_tokens(str(user.user_id))
    
    # Build response
    user_response = UserResponse(
        user_id=user.user_id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        primary_language=user.primary_language,
        user_type=user.user_type,
        account_status=user.account_status,
        is_active=user.is_active,
        created_date=user.created_date
    )
    
    return SuccessResponse(
        status="success",
        message="Login successful",
        data={
            "user": user_response,
            "token": TokenResponse(**tokens)
        }
    )

# ============================================================================
# POST /api/v1/auth/refresh
# ============================================================================

@router.post("/refresh", response_model=SuccessResponse)
def refresh_token(
    token_data: TokenRefresh,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    
    Args:
        token_data: Refresh token
    
    Returns:
        SuccessResponse with new access token
    """
    new_access_token = refresh_access_token(token_data.refresh_token)
    
    if not new_access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    return SuccessResponse(
        status="success",
        message="Token refreshed",
        data={
            "access_token": new_access_token,
            "token_type": "bearer"
        }
    )

# ============================================================================
# POST /api/v1/auth/logout
# ============================================================================

@router.post("/logout", response_model=SuccessResponse)
def logout(current_user: User = Depends(get_current_user)):
    """
    Logout user (client-side removes token)
    
    Note: JWT tokens don't have server-side logout.
    Client simply removes token from storage.
    This endpoint can be used for logging, cleanup, etc.
    """
    return SuccessResponse(
        status="success",
        message="Logged out successfully"
    )

# ============================================================================
# GET /api/v1/auth/me
# ============================================================================

@router.get("/me", response_model=SuccessResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user info
    
    Returns:
        Current user details
    """
    user_response = UserResponse(
        user_id=current_user.user_id,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        email=current_user.email,
        primary_language=current_user.primary_language,
        user_type=current_user.user_type,
        account_status=current_user.account_status,
        is_active=current_user.is_active,
        created_date=current_user.created_date
    )
    
    return SuccessResponse(
        status="success",
        message="User info retrieved",
        data=user_response
    )
