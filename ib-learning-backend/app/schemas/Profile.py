# app/schemas/profile.py
"""
Learner Profile and Well-Being schemas (Pydantic models)
Used for S-07, T-07, S-09 workflows
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID

# ============================================================================
# LEARNER PROFILE ATTRIBUTE SCHEMAS
# ============================================================================

class LearnerProfileAttributeResponse(BaseModel):
    """Learner Profile attribute (pre-populated in MVP: 2-3 only)
    
    MVP: Inquirer, Communicator, Thinker
    """
    attribute_id: UUID
    attribute_name: str
    attribute_description: str
    observable_behaviors: Optional[str]
    display_order: int
    
    class Config:
        from_attributes = True

# ============================================================================
# STUDENT LEARNER PROFILE PROGRESS SCHEMAS (S-07, T-07)
# ============================================================================

class StudentProfileSelfAssess(BaseModel):
    """Student self-assesses on learner profile (S-07)
    
    MVP Simplified:
    - 2-3 attributes only (not 10)
    - Self-rate on 1-4 scale
    - Collect 1-2 evidence pieces
    - Write reflection
    """
    attribute_id: UUID
    student_proficiency_level: str = Field(..., regex='^(emerging|developing|proficient|extending)$')
    student_self_reflection: str = Field(..., min_length=10)
    evidence_artifacts: Optional[List[str]] = None  # References to work
    assessment_date: date = Field(default_factory=date.today)

class TeacherProfileRate(BaseModel):
    """Teacher rates student on learner profile (T-07)
    
    Teacher:
    - Reviews student's self-assessment
    - Provides own rating
    - Gives growth feedback
    """
    attribute_id: UUID
    teacher_proficiency_level: str = Field(..., regex='^(emerging|developing|proficient|extending)$')
    teacher_observation: str = Field(..., min_length=10)
    growth_notes: Optional[str] = None

class StudentLearnerProfileProgressResponse(BaseModel):
    """Student learner profile progress response"""
    progress_id: UUID
    student_id: UUID
    attribute_id: UUID
    attribute_name: str  # Include name for display
    assessment_date: date
    student_proficiency_level: Optional[str]
    teacher_proficiency_level: Optional[str]
    student_self_reflection: Optional[str]
    teacher_observation: Optional[str]
    evidence_count: int
    growth_notes: Optional[str]
    
    class Config:
        from_attributes = True

class StudentProfileProgressList(BaseModel):
    """List of student's profile progress on all attributes"""
    student_id: UUID
    attributes: List[StudentLearnerProfileProgressResponse]

# ============================================================================
# WELL-BEING SCHEMAS (S-09: Student Well-Being Check-In)
# ============================================================================

class StudentWellBeingCheckIn(BaseModel):
    """Student well-being check-in (S-09)
    
    MVP Simplified: 5 questions only
    - Physical health (0-10)
    - Emotional health (0-10)
    - Sense of belonging (0-10)
    - What's going well (text)
    - What's challenging (text)
    
    System calculates overall_wellbeing_score automatically
    """
    physical_health_score: int = Field(..., ge=0, le=10)
    emotional_health_score: int = Field(..., ge=0, le=10)
    sense_of_belonging_score: int = Field(..., ge=0, le=10)
    what_is_going_well: str = Field(..., min_length=5)
    what_is_challenging: str = Field(..., min_length=5)

class StudentWellBeingResponse(StudentWellBeingCheckIn):
    """Well-being response with calculated overall score"""
    wellbeing_id: UUID
    student_id: UUID
    assessment_date: date
    overall_wellbeing_score: int  # Auto-calculated: (phys + emot + belong) / 3
    teacher_observations: Optional[str]
    support_needed: bool
    follow_up_required: bool
    created_date: datetime
    
    class Config:
        from_attributes = True

class WellBeingStatus(BaseModel):
    """Well-being status summary"""
    student_id: UUID
    latest_score: Optional[int]
    status: str  # "Excellent" (8-10), "Good" (6-7), "Fair" (4-5), "Needs Support" (<4)
    last_assessment_date: Optional[date]
    trend: Optional[str]  # "improving", "stable", "declining"

class StudentWellBeingTrend(BaseModel):
    """Well-being trend over time"""
    student_id: UUID
    assessments: List[StudentWellBeingResponse]
    average_score: float
    trend_direction: str  # "up", "stable", "down"

# ============================================================================
# AGENCY & VOICE SCHEMAS (T-03)
# ============================================================================

class CommunityDecisionCreate(BaseModel):
    """Create decision for student voice collection (T-03)
    
    MVP Simplified: Class voting/decisions
    Teacher creates simple decision with 2-3 options
    Students vote
    """
    decision_topic: str = Field(..., min_length=5)
    decision_description: Optional[str] = None
    decision_options: List[str] = Field(..., min_items=2, max_items=5)
    voice_collection_method: str = Field(default='poll', regex='^(poll|survey|discussion|voting)$')
    unit_id: Optional[UUID] = None

class StudentVote(BaseModel):
    """Student votes on decision"""
    decision_id: UUID
    selected_option: str

class CommunityDecisionResponse(BaseModel):
    """Community decision response"""
    decision_id: UUID
    decision_topic: str
    decision_description: Optional[str]
    decision_options: List[str]
    voice_collection_method: str
    voice_count: int
    final_decision: Optional[str]
    decision_rationale: Optional[str]
    decision_date: date
    
    class Config:
        from_attributes = True

class AgencyEventResponse(BaseModel):
    """Agency event (voice, choice, ownership)"""
    agency_event_id: UUID
    user_id: UUID
    agency_type: str  # voice, choice, ownership
    specific_action: str
    event_date: date
    celebration_recorded: bool
    
    class Config:
        from_attributes = True

# ============================================================================
# MESSAGE SCHEMAS
# ============================================================================

class MessageCreate(BaseModel):
    """Create message"""
    recipient_id: UUID
    subject: Optional[str] = None
    message_text: str = Field(..., min_length=1)
    message_type: str = Field(default='general', regex='^(feedback|notification|general|alert)$')

class MessageResponse(BaseModel):
    """Message response"""
    message_id: UUID
    sender_id: UUID
    recipient_id: UUID
    subject: Optional[str]
    message_text: str
    message_type: str
    is_read: bool
    read_date: Optional[datetime]
    created_date: datetime
    
    class Config:
        from_attributes = True

class MessageList(BaseModel):
    """Message list (lightweight)"""
    message_id: UUID
    sender_name: str
    subject: Optional[str]
    message_text: str  # First 100 chars
    is_read: bool
    created_date: datetime

# ============================================================================
# DASHBOARD SCHEMAS
# ============================================================================

class StudentDashboardStats(BaseModel):
    """Student dashboard statistics"""
    total_units: int
    active_units: int
    completed_assessments: int
    pending_assessments: int
    avg_proficiency_score: float  # 0-4 scale
    wellbeing_status: str

class TeacherDashboardStats(BaseModel):
    """Teacher dashboard statistics"""
    total_students: int
    units_active: int
    assessments_pending_grading: int
    students_needing_support: int

# ============================================================================
# REPORT SCHEMAS (T-10)
# ============================================================================

class StudentProgressReport(BaseModel):
    """Student progress report"""
    student_id: UUID
    student_name: str
    grade_level: int
    units_enrolled: int
    units_completed: int
    avg_assessment_score: float
    learner_profile_progress: List[StudentLearnerProfileProgressResponse]
    latest_wellbeing: Optional[StudentWellBeingResponse]
    recent_messages: int
    agency_events_count: int

class UnitProgressReport(BaseModel):
    """Unit progress report"""
    unit_id: UUID
    unit_title: str
    total_students: int
    students_completed: int
    completion_percentage: float
    avg_assessment_score: float
    assessments_pending_grading: int
