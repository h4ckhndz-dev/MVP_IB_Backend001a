# app/schemas/user.py
"""
User request/response schemas (Pydantic models)
Used for API request validation and response formatting
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

# ============================================================================
# USER SCHEMAS
# ============================================================================

class UserBase(BaseModel):
    """Base user schema"""
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    primary_language: str = Field(default='en', max_length=50)

class UserRegister(UserBase):
    """User registration request"""
    password: str = Field(..., min_length=8, max_length=255)
    user_type: str = Field(..., pattern='^(student|teacher|admin)$')
    community_id: UUID

class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr
    password: str = Field(..., min_length=1)

class UserResponse(UserBase):
    """User response (no password!)"""
    user_id: UUID
    user_type: str
    account_status: str
    is_active: bool
    created_date: datetime
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int

class TokenRefresh(BaseModel):
    """Token refresh request"""
    refresh_token: str

# ============================================================================
# STUDENT SCHEMAS
# ============================================================================

class StudentBase(BaseModel):
    """Base student data"""
    grade_level: int = Field(..., ge=0, le=6)
    home_language: str = Field(default='en')
    learning_needs_documented: bool = False
    learning_needs_description: Optional[str] = None

class StudentCreate(StudentBase):
    """Create student request"""
    student_number: Optional[str] = None
    enrollment_status: str = Field(default='current')

class StudentResponse(StudentBase):
    """Student response"""
    student_id: UUID
    student_number: Optional[str]
    enrollment_status: str
    
    class Config:
        from_attributes = True

# ============================================================================
# TEACHER SCHEMAS
# ============================================================================

class TeacherBase(BaseModel):
    """Base teacher data"""
    subject_specialization: Optional[str] = None
    qualification: Optional[str] = None
    years_of_experience: int = Field(default=0, ge=0)
    is_coordinator: bool = False

class TeacherCreate(TeacherBase):
    """Create teacher request"""
    employee_number: Optional[str] = None
    employment_status: str = Field(default='full-time')

class TeacherResponse(TeacherBase):
    """Teacher response"""
    teacher_id: UUID
    employee_number: Optional[str]
    employment_status: str
    
    class Config:
        from_attributes = True

# ============================================================================
# AUTH RESPONSE
# ============================================================================

class AuthResponse(BaseModel):
    """Complete auth response with user info"""
    user: UserResponse
    token: TokenResponse
