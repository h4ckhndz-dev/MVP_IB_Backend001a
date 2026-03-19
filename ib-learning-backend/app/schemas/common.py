# app/schemas/common.py
"""
Common schemas used across all endpoints
Error responses, pagination, etc.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any, List
from datetime import datetime

# ============================================================================
# ERROR RESPONSES
# ============================================================================

class ErrorDetail(BaseModel):
    """Error detail"""
    error_code: str
    error_message: str
    details: Optional[str] = None

class ErrorResponse(BaseModel):
    """Standard error response"""
    status: str = "error"
    message: str
    error_code: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[dict] = None

class ValidationError(ErrorResponse):
    """Validation error response"""
    status: str = "validation_error"
    errors: List[dict]  # List of validation errors

# ============================================================================
# SUCCESS RESPONSES
# ============================================================================

class SuccessResponse(BaseModel):
    """Standard success response"""
    status: str = "success"
    message: str
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class CreatedResponse(SuccessResponse):
    """Created response (201)"""
    status: str = "created"

# ============================================================================
# PAGINATION SCHEMAS
# ============================================================================

class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""
    data: List[Any]
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_previous: bool

# ============================================================================
# FILTER SCHEMAS
# ============================================================================

class UnitFilterParams(BaseModel):
    """Unit list filter parameters"""
    grade_level: Optional[int] = None
    unit_status: Optional[str] = None
    theme_id: Optional[str] = None
    sort_by: str = Field(default='created_date', pattern='^(created_date|unit_title|start_date)$')
    sort_order: str = Field(default='desc', pattern='^(asc|desc)$')
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

class AssessmentFilterParams(BaseModel):
    """Assessment list filter parameters"""
    assessment_type: Optional[str] = None
    unit_id: Optional[str] = None
    due_date_from: Optional[str] = None  # YYYY-MM-DD
    due_date_to: Optional[str] = None
    status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

# ============================================================================
# HEALTH CHECK SCHEMAS
# ============================================================================

class HealthCheckResponse(BaseModel):
    """API health check response"""
    status: str
    app_name: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class DatabaseHealthCheck(BaseModel):
    """Database connection health check"""
    status: str  # "connected" or "disconnected"
    database: str
    latency_ms: Optional[float]

# ============================================================================
# BATCH OPERATION SCHEMAS
# ============================================================================

class BatchError(BaseModel):
    """Error for single item in batch"""
    item_id: Any
    error_message: str

class BatchResponse(BaseModel):
    """Batch operation response"""
    successful: int
    failed: int
    total: int
    errors: Optional[List[BatchError]] = None

# ============================================================================
# FILE UPLOAD SCHEMAS
# ============================================================================

class FileUploadResponse(BaseModel):
    """File upload response"""
    file_name: str
    file_url: str
    file_size: int
    content_type: str
    uploaded_at: datetime

class FileUploadError(ErrorResponse):
    """File upload error"""
    status: str = "file_upload_error"
    max_file_size_mb: int
    allowed_types: List[str]
