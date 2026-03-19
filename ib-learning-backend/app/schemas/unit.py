# app/schemas/unit.py
"""
Unit of Inquiry schemas (Pydantic models)
Used for T-01 workflow: Teacher creates unit
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID

# ============================================================================
# CONCEPT SCHEMAS
# ============================================================================

class ConceptResponse(BaseModel):
    """Concept response (pre-populated)"""
    concept_id: UUID
    concept_name: str
    concept_definition: str
    
    class Config:
        from_attributes = True

# ============================================================================
# THEME SCHEMAS
# ============================================================================

class ThemeResponse(BaseModel):
    """Transdisciplinary theme response"""
    theme_id: UUID
    theme_name: str
    theme_description: Optional[str]
    display_order: int
    
    class Config:
        from_attributes = True

# ============================================================================
# LEARNING GOAL SCHEMAS
# ============================================================================

class LearningGoalBase(BaseModel):
    """Base learning goal"""
    goal_description: str = Field(..., min_length=10)
    goal_type: str = Field(default='knowledge', pattern='^(knowledge|skill|understanding|attitude)$')

class LearningGoalCreate(LearningGoalBase):
    """Create learning goal"""
    sequence_order: int = Field(default=0, ge=0)

class LearningGoalResponse(LearningGoalBase):
    """Learning goal response"""
    goal_id: UUID
    sequence_order: int
    
    class Config:
        from_attributes = True

# ============================================================================
# LINE OF INQUIRY SCHEMAS
# ============================================================================

class LineOfInquiryBase(BaseModel):
    """Base inquiry question"""
    inquiry_question: str = Field(..., min_length=10)
    inquiry_focus: Optional[str] = None

class LineOfInquiryCreate(LineOfInquiryBase):
    """Create inquiry question"""
    sequence_order: int = Field(default=0, ge=0)

class LineOfInquiryResponse(LineOfInquiryBase):
    """Inquiry question response"""
    inquiry_id: UUID
    sequence_order: int
    
    class Config:
        from_attributes = True

# ============================================================================
# UNIT CONCEPT SCHEMAS
# ============================================================================

class UnitConceptCreate(BaseModel):
    """Link concept to unit"""
    concept_id: UUID
    emphasis_level: str = Field(default='supporting', pattern='^(central|major|supporting)$')

class UnitConceptResponse(BaseModel):
    """Unit concept response"""
    unit_concept_id: UUID
    concept: ConceptResponse
    emphasis_level: str
    
    class Config:
        from_attributes = True

# ============================================================================
# UNIT OF INQUIRY SCHEMAS (T-01: Teacher Creates Unit)
# ============================================================================

class UnitOfInquiryBase(BaseModel):
    """Base unit"""
    unit_title: str = Field(..., min_length=5, max_length=255)
    central_idea: str = Field(..., min_length=10)
    unit_description: Optional[str] = None
    grade_level: int = Field(..., ge=0, le=6)
    duration_weeks: int = Field(default=4, ge=1)
    start_date: date
    end_date: Optional[date] = None

class UnitOfInquiryCreate(UnitOfInquiryBase):
    """Create unit request (T-01)
    
    MVP Simplified:
    - Title, Central Idea, Description
    - Grade level
    - Start/End dates
    - Theme, Goals, Concepts, Inquiries
    """
    theme_id: UUID
    learning_goals: List[LearningGoalCreate] = Field(..., min_items=1, max_items=10)
    concepts: List[UnitConceptCreate] = Field(..., min_items=1, max_items=3)
    inquiry_questions: List[LineOfInquiryCreate] = Field(..., min_items=1, max_items=5)

class UnitOfInquiryUpdate(BaseModel):
    """Update unit (partial)"""
    unit_title: Optional[str] = None
    unit_description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    unit_status: Optional[str] = Field(None, pattern='^(planning|active|completed|archived)$')

class UnitOfInquiryResponse(UnitOfInquiryBase):
    """Unit response"""
    unit_id: UUID
    teacher_id: UUID
    theme_id: UUID
    unit_status: str
    created_date: datetime
    updated_at: datetime
    
    # Nested data
    goals: List[LearningGoalResponse] = []
    concepts: List[UnitConceptResponse] = []
    inquiries: List[LineOfInquiryResponse] = []
    
    class Config:
        from_attributes = True

class UnitListResponse(BaseModel):
    """Unit list response (lighter)"""
    unit_id: UUID
    unit_title: str
    central_idea: str
    grade_level: int
    unit_status: str
    start_date: date
    end_date: Optional[date]
    
    class Config:
        from_attributes = True

# ============================================================================
# STUDENT INQUIRY PROGRESS SCHEMAS (S-02: Student Joins Unit)
# ============================================================================

class StudentInquiryProgressCreate(BaseModel):
    """Student joins unit"""
    unit_id: UUID

class StudentInquiryProgressResponse(BaseModel):
    """Student inquiry progress response"""
    inquiry_progress_id: UUID
    student_id: UUID
    unit_id: UUID
    join_date: date
    participation_level: str
    completion_percentage: int
    notes: Optional[str]
    
    class Config:
        from_attributes = True

class StudentInquiryProgressUpdate(BaseModel):
    """Update student progress"""
    participation_level: Optional[str] = None
    completion_percentage: Optional[int] = Field(None, ge=0, le=100)
    notes: Optional[str] = None
