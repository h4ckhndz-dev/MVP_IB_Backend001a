# app/schemas/assessment.py
"""
Assessment and submission schemas (Pydantic models)
Used for T-05, S-05, T-06 workflows
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID

# ============================================================================
# ASSESSMENT RUBRIC SCHEMAS
# ============================================================================

class AssessmentRubricResponse(BaseModel):
    """Assessment rubric (pre-built template)"""
    rubric_id: UUID
    rubric_name: str
    rubric_description: Optional[str]
    criteria: dict  # JSON array of criteria
    proficiency_levels: dict  # {emerging, developing, proficient, extending}
    is_template: bool
    
    class Config:
        from_attributes = True

# ============================================================================
# ASSESSMENT SCHEMAS (T-05: Teacher Creates Assessment)
# ============================================================================

class AssessmentBase(BaseModel):
    """Base assessment"""
    assessment_title: str = Field(..., min_length=5, max_length=255)
    assessment_description: Optional[str] = None
    assessment_type: str = Field(default='formative', pattern='^(formative|summative)$')
    due_date: date
    submission_required: bool = Field(default=True)
    max_score: Optional[int] = Field(None, ge=0)

class AssessmentCreate(AssessmentBase):
    """Create assessment (T-05)
    
    MVP Simplified:
    - Title, Description
    - Type (formative/summative)
    - Due date
    - Learning goal (dropdown)
    - Rubric template (pre-built, not custom)
    """
    unit_id: UUID
    goal_id: UUID
    rubric_id: UUID

class AssessmentUpdate(BaseModel):
    """Update assessment"""
    assessment_title: Optional[str] = None
    assessment_description: Optional[str] = None
    due_date: Optional[date] = None
    max_score: Optional[int] = None

class AssessmentResponse(AssessmentBase):
    """Assessment response"""
    assessment_id: UUID
    unit_id: UUID
    goal_id: UUID
    teacher_id: UUID
    rubric_id: Optional[UUID]
    created_date: datetime
    updated_at: datetime
    
    # Nested
    rubric: Optional[AssessmentRubricResponse] = None
    
    class Config:
        from_attributes = True

class AssessmentListResponse(BaseModel):
    """Assessment list response"""
    assessment_id: UUID
    assessment_title: str
    assessment_type: str
    due_date: date
    submission_required: bool
    
    class Config:
        from_attributes = True

# ============================================================================
# STUDENT ASSESSMENT SCHEMAS (S-05: Student Submits, T-06: Teacher Feedback)
# ============================================================================

class StudentAssessmentSubmit(BaseModel):
    """Student submits work (S-05)
    
    MVP: Can submit either:
    - File upload (stored in Supabase Storage)
    - Or text response
    """
    assessment_id: UUID
    submission_text: Optional[str] = None
    submission_file_urls: Optional[List[str]] = None  # URLs from file upload
    student_self_rating: Optional[str] = Field(None, regex='^(emerging|developing|proficient|extending)$')

class StudentAssessmentResponse(BaseModel):
    """Student submission response"""
    student_assessment_id: UUID
    assessment_id: UUID
    student_id: UUID
    submission_status: str
    submission_date: Optional[datetime]
    submission_text: Optional[str]
    submission_file_urls: Optional[List[str]]
    student_self_rating: Optional[str]
    teacher_rating: Optional[str]
    teacher_feedback: Optional[str]
    score_earned: Optional[float]
    feedback_date: Optional[datetime]
    
    class Config:
        from_attributes = True

class TeacherFeedback(BaseModel):
    """Teacher provides feedback (T-06)
    
    After student submits, teacher:
    - Reads submission
    - Rates proficiency (emerging/dev/prof/ext)
    - Provides feedback text
    - System auto-sends message to student
    """
    student_assessment_id: UUID
    teacher_rating: str = Field(..., regex='^(emerging|developing|proficient|extending)$')
    teacher_feedback: str = Field(..., min_length=10)
    score_earned: Optional[float] = Field(None, ge=0)

# ============================================================================
# ASSESSMENT STATUS SCHEMAS
# ============================================================================

class AssessmentStatusResponse(BaseModel):
    """Assessment status per student"""
    assessment_id: UUID
    assessment_title: str
    due_date: date
    submission_status: str  # not_submitted, submitted, returned, graded
    submission_date: Optional[datetime]
    teacher_rating: Optional[str]
    score_earned: Optional[float]
    
    class Config:
        from_attributes = True

class UnitAssessmentStats(BaseModel):
    """Unit assessment statistics (for dashboard)"""
    unit_id: UUID
    total_assessments: int
    assessments_with_submissions: int
    assessments_graded: int
    grading_percentage: float
    
    class Config:
        from_attributes = True
