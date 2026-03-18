# app/models/__init__.py - SQLAlchemy ORM Models for IB Learning Community
"""
Complete SQLAlchemy models for all 21 tables
Maps directly to PostgreSQL schema
"""

from datetime import datetime, date
from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, ForeignKey, Date, JSON, DECIMAL, Enum, CheckConstraint, UniqueConstraint, func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid
import enum

Base = declarative_base()

# ============================================================================
# LAYER 1: CORE INFRASTRUCTURE MODELS
# ============================================================================

class LearningCommunity(Base):
    """The school/organization"""
    __tablename__ = "learning_community"
    
    community_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    community_name = Column(String(255), unique=True, nullable=False)
    country = Column(String(100), nullable=False)
    region_state = Column(String(100))
    city = Column(String(100))
    mission_statement = Column(Text)
    ib_status = Column(String(50), nullable=False, default='candidate')  # candidate, authorized, full
    total_students = Column(Integer, default=0)
    primary_language_of_instruction = Column(String(50), nullable=False, default='en')
    contact_email = Column(String(255), unique=True)
    contact_phone = Column(String(20))
    principal_name = Column(String(255))
    created_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    users = relationship("User", back_populates="community", cascade="all, delete-orphan")
    units = relationship("UnitOfInquiry", back_populates="community")
    concepts = relationship("Concept", back_populates="community")
    themes = relationship("TransdisciplinaryTheme", back_populates="community")
    attributes = relationship("LearnerProfileAttribute", back_populates="community")
    assessments = relationship("Assessment", back_populates="community")
    rubrics = relationship("AssessmentRubric", back_populates="community")
    decisions = relationship("CommunityDecision", back_populates="community")

# ============================================================================

class User(Base):
    """Base user - polymorphic (student, teacher, admin)"""
    __tablename__ = "user"
    
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    community_id = Column(UUID(as_uuid=True), ForeignKey('learning_community.community_id', ondelete='RESTRICT'), nullable=False)
    user_type = Column(String(50), nullable=False)  # student, teacher, admin
    email = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    primary_language = Column(String(50), default='en')
    profile_picture_url = Column(String(500))
    bio = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    account_status = Column(String(50), default='pending')  # pending, active, suspended, inactive
    last_login_date = Column(DateTime)
    created_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('email', 'community_id', name='uq_email_community'),
    )
    
    # Relationships
    community = relationship("LearningCommunity", back_populates="users")
    student = relationship("Student", back_populates="user", uselist=False)
    teacher = relationship("Teacher", back_populates="user", uselist=False)
    sent_messages = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
    received_messages = relationship("Message", foreign_keys="Message.recipient_id", back_populates="recipient")
    agency_events = relationship("AgencyEvent", back_populates="user")

# ============================================================================

class Student(Base):
    """Student-specific info"""
    __tablename__ = "student"
    
    student_id = Column(UUID(as_uuid=True), ForeignKey('user.user_id', ondelete='CASCADE'), primary_key=True)
    student_number = Column(String(50), unique=True)
    grade_level = Column(Integer, nullable=False, default=1)  # 0-6
    entry_date = Column(Date, nullable=False, default=date.today)
    exit_date = Column(Date)
    enrollment_status = Column(String(50), default='current')  # current, graduated, withdrawn, on_leave
    home_language = Column(String(50), default='en')
    learning_needs_documented = Column(Boolean, default=False)
    learning_needs_description = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="student")
    assessments = relationship("StudentAssessment", back_populates="student")
    inquiry_progress = relationship("StudentInquiryProgress", back_populates="student")
    profile_progress = relationship("StudentLearnerProfileProgress", back_populates="student")
    wellbeing = relationship("StudentWellBeing", back_populates="student")

# ============================================================================

class Teacher(Base):
    """Teacher-specific info"""
    __tablename__ = "teacher"
    
    teacher_id = Column(UUID(as_uuid=True), ForeignKey('user.user_id', ondelete='CASCADE'), primary_key=True)
    employee_number = Column(String(50), unique=True)
    subject_specialization = Column(String(100))
    qualification = Column(Text)
    years_of_experience = Column(Integer, default=0)
    employment_status = Column(String(50), default='full-time')  # full-time, part-time, contract
    start_date = Column(Date, nullable=False, default=date.today)
    end_date = Column(Date)
    is_coordinator = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="teacher")
    units = relationship("UnitOfInquiry", back_populates="teacher")
    assessments = relationship("Assessment", back_populates="teacher")

# ============================================================================
# LAYER 2: LEARNING & INQUIRY MODELS
# ============================================================================

class TransdisciplinaryTheme(Base):
    """IB 6 Transdisciplinary Themes"""
    __tablename__ = "transdisciplinary_theme"
    
    theme_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    community_id = Column(UUID(as_uuid=True), ForeignKey('learning_community.community_id', ondelete='CASCADE'), nullable=False)
    theme_name = Column(String(255), nullable=False)
    theme_description = Column(Text)
    display_order = Column(Integer, default=0)
    created_date = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('community_id', 'theme_name', name='uq_community_theme'),
    )
    
    # Relationships
    community = relationship("LearningCommunity", back_populates="themes")
    units = relationship("UnitOfInquiry", back_populates="theme")

# ============================================================================

class UnitOfInquiry(Base):
    """Main learning unit"""
    __tablename__ = "unit_of_inquiry"
    
    unit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    community_id = Column(UUID(as_uuid=True), ForeignKey('learning_community.community_id', ondelete='CASCADE'), nullable=False)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey('teacher.teacher_id', ondelete='RESTRICT'), nullable=False)
    theme_id = Column(UUID(as_uuid=True), ForeignKey('transdisciplinary_theme.theme_id', ondelete='RESTRICT'), nullable=False)
    grade_level = Column(Integer, nullable=False)  # 0-6
    unit_title = Column(String(255), nullable=False)
    central_idea = Column(Text, nullable=False)
    unit_description = Column(Text)
    duration_weeks = Column(Integer)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    unit_status = Column(String(50), default='planning')  # planning, active, completed, archived
    created_date = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    community = relationship("LearningCommunity", back_populates="units")
    teacher = relationship("Teacher", back_populates="units")
    theme = relationship("TransdisciplinaryTheme", back_populates="units")
    inquiries = relationship("LineOfInquiry", back_populates="unit", cascade="all, delete-orphan")
    goals = relationship("LearningGoal", back_populates="unit", cascade="all, delete-orphan")
    assessments = relationship("Assessment", back_populates="unit")
    concepts = relationship("UnitConcept", back_populates="unit", cascade="all, delete-orphan")
    student_progress = relationship("StudentInquiryProgress", back_populates="unit")
    decisions = relationship("CommunityDecision", back_populates="unit")
    agency_events = relationship("AgencyEvent", back_populates="unit")

# ============================================================================

class LineOfInquiry(Base):
    """Research questions in unit"""
    __tablename__ = "line_of_inquiry"
    
    inquiry_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unit_id = Column(UUID(as_uuid=True), ForeignKey('unit_of_inquiry.unit_id', ondelete='CASCADE'), nullable=False)
    inquiry_question = Column(Text, nullable=False)
    inquiry_focus = Column(String(100))
    sequence_order = Column(Integer, default=0)
    created_date = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('unit_id', 'sequence_order', name='uq_unit_inquiry_sequence'),
    )
    
    # Relationships
    unit = relationship("UnitOfInquiry", back_populates="inquiries")

# ============================================================================

class Concept(Base):
    """IB Key Concepts"""
    __tablename__ = "concept"
    
    concept_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    community_id = Column(UUID(as_uuid=True), ForeignKey('learning_community.community_id', ondelete='CASCADE'), nullable=False)
    concept_name = Column(String(50), unique=True, nullable=False)
    concept_definition = Column(Text, nullable=False)
    synonym = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    community = relationship("LearningCommunity", back_populates="concepts")
    unit_concepts = relationship("UnitConcept", back_populates="concept")

# ============================================================================

class UnitConcept(Base):
    """Junction table - Links concepts to units"""
    __tablename__ = "unit_concept"
    
    unit_concept_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unit_id = Column(UUID(as_uuid=True), ForeignKey('unit_of_inquiry.unit_id', ondelete='CASCADE'), nullable=False)
    concept_id = Column(UUID(as_uuid=True), ForeignKey('concept.concept_id', ondelete='RESTRICT'), nullable=False)
    emphasis_level = Column(String(50), default='supporting')  # central, major, supporting
    created_date = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('unit_id', 'concept_id', name='uq_unit_concept'),
    )
    
    # Relationships
    unit = relationship("UnitOfInquiry", back_populates="concepts")
    concept = relationship("Concept", back_populates="unit_concepts")

# ============================================================================
# LAYER 3: ASSESSMENT MODELS
# ============================================================================

class LearningGoal(Base):
    """What students will learn"""
    __tablename__ = "learning_goal"
    
    goal_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unit_id = Column(UUID(as_uuid=True), ForeignKey('unit_of_inquiry.unit_id', ondelete='CASCADE'), nullable=False)
    goal_description = Column(Text, nullable=False)
    goal_type = Column(String(50), default='knowledge')  # knowledge, skill, understanding, attitude
    sequence_order = Column(Integer, default=0)
    created_date = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('unit_id', 'sequence_order', name='uq_unit_goal_sequence'),
    )
    
    # Relationships
    unit = relationship("UnitOfInquiry", back_populates="goals")
    assessments = relationship("Assessment", back_populates="goal")

# ============================================================================

class AssessmentRubric(Base):
    """Pre-built assessment templates"""
    __tablename__ = "assessment_rubric"
    
    rubric_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    community_id = Column(UUID(as_uuid=True), ForeignKey('learning_community.community_id', ondelete='CASCADE'), nullable=False)
    rubric_name = Column(String(255), nullable=False)
    rubric_description = Column(Text)
    criteria = Column(JSON, nullable=False)  # Array of criteria
    proficiency_levels = Column(JSON, nullable=False)  # {emerging, developing, proficient, extending}
    is_template = Column(Boolean, default=True)
    created_date = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    community = relationship("LearningCommunity", back_populates="rubrics")
    assessments = relationship("Assessment", back_populates="rubric")

# ============================================================================

class Assessment(Base):
    """Assessment events/assignments"""
    __tablename__ = "assessment"
    
    assessment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    community_id = Column(UUID(as_uuid=True), ForeignKey('learning_community.community_id', ondelete='CASCADE'), nullable=False)
    unit_id = Column(UUID(as_uuid=True), ForeignKey('unit_of_inquiry.unit_id', ondelete='RESTRICT'), nullable=False)
    goal_id = Column(UUID(as_uuid=True), ForeignKey('learning_goal.goal_id', ondelete='RESTRICT'), nullable=False)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey('teacher.teacher_id', ondelete='RESTRICT'), nullable=False)
    rubric_id = Column(UUID(as_uuid=True), ForeignKey('assessment_rubric.rubric_id', ondelete='SET NULL'), nullable=True)
    assessment_title = Column(String(255), nullable=False)
    assessment_description = Column(Text)
    assessment_type = Column(String(50), default='formative')  # formative, summative
    due_date = Column(Date, nullable=False)
    submission_required = Column(Boolean, default=True)
    max_score = Column(Integer)
    created_date = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    community = relationship("LearningCommunity", back_populates="assessments")
    unit = relationship("UnitOfInquiry", back_populates="assessments")
    goal = relationship("LearningGoal", back_populates="assessments")
    teacher = relationship("Teacher", back_populates="assessments")
    rubric = relationship("AssessmentRubric", back_populates="assessments")
    submissions = relationship("StudentAssessment", back_populates="assessment", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="assessment")

# ============================================================================

class StudentAssessment(Base):
    """Student submissions and results"""
    __tablename__ = "student_assessment"
    
    student_assessment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey('assessment.assessment_id', ondelete='CASCADE'), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey('student.student_id', ondelete='CASCADE'), nullable=False)
    submission_status = Column(String(50), default='not_submitted')  # not_submitted, submitted, returned, graded
    submission_date = Column(DateTime)
    submission_text = Column(Text)
    submission_file_urls = Column(JSON)  # Array of file URLs
    student_self_rating = Column(String(50))  # emerging, developing, proficient, extending
    teacher_rating = Column(String(50))
    teacher_feedback = Column(Text)
    score_earned = Column(DECIMAL(5, 2))
    feedback_date = Column(DateTime)
    created_date = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('assessment_id', 'student_id', name='uq_assessment_student'),
    )
    
    # Relationships
    assessment = relationship("Assessment", back_populates="submissions")
    student = relationship("Student", back_populates="assessments")

# ============================================================================
# LAYER 4: STUDENT LEARNING PROFILE MODELS
# ============================================================================

class LearnerProfileAttribute(Base):
    """IB Learner Profile attributes"""
    __tablename__ = "learner_profile_attribute"
    
    attribute_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    community_id = Column(UUID(as_uuid=True), ForeignKey('learning_community.community_id', ondelete='CASCADE'), nullable=False)
    attribute_name = Column(String(50), nullable=False)  # Inquirer, Communicator, Thinker, etc.
    attribute_description = Column(Text)
    observable_behaviors = Column(Text)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_date = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('community_id', 'attribute_name', name='uq_community_attribute'),
    )
    
    # Relationships
    community = relationship("LearningCommunity", back_populates="attributes")
    progress = relationship("StudentLearnerProfileProgress", back_populates="attribute")

# ============================================================================

class StudentLearnerProfileProgress(Base):
    """Track student development on attributes"""
    __tablename__ = "student_learner_profile_progress"
    
    progress_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey('student.student_id', ondelete='CASCADE'), nullable=False)
    attribute_id = Column(UUID(as_uuid=True), ForeignKey('learner_profile_attribute.attribute_id', ondelete='RESTRICT'), nullable=False)
    assessment_date = Column(Date, nullable=False, default=date.today)
    student_proficiency_level = Column(String(50))  # emerging, developing, proficient, extending
    teacher_proficiency_level = Column(String(50))
    student_self_reflection = Column(Text)
    teacher_observation = Column(Text)
    evidence_artifacts = Column(JSON)  # Array of artifact references
    evidence_count = Column(Integer, default=0)
    growth_notes = Column(Text)
    created_date = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('student_id', 'attribute_id', 'assessment_date', name='uq_student_attribute_date'),
    )
    
    # Relationships
    student = relationship("Student", back_populates="profile_progress")
    attribute = relationship("LearnerProfileAttribute", back_populates="progress")

# ============================================================================

class StudentInquiryProgress(Base):
    """Track student progress in units"""
    __tablename__ = "student_inquiry_progress"
    
    inquiry_progress_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey('student.student_id', ondelete='CASCADE'), nullable=False)
    unit_id = Column(UUID(as_uuid=True), ForeignKey('unit_of_inquiry.unit_id', ondelete='CASCADE'), nullable=False)
    join_date = Column(Date, nullable=False, default=date.today)
    participation_level = Column(String(50), default='active')  # active, observer, completed, withdrawn
    completion_percentage = Column(Integer, default=0)  # 0-100
    last_activity_date = Column(DateTime)
    notes = Column(Text)
    created_date = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('student_id', 'unit_id', name='uq_student_unit'),
    )
    
    # Relationships
    student = relationship("Student", back_populates="inquiry_progress")
    unit = relationship("UnitOfInquiry", back_populates="student_progress")

# ============================================================================
# LAYER 5: WELL-BEING MODEL
# ============================================================================

class StudentWellBeing(Base):
    """Holistic student well-being"""
    __tablename__ = "student_well_being"
    
    wellbeing_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey('student.student_id', ondelete='CASCADE'), nullable=False)
    assessment_date = Column(Date, nullable=False, default=date.today)
    physical_health_score = Column(Integer)  # 0-10
    emotional_health_score = Column(Integer)  # 0-10
    sense_of_belonging_score = Column(Integer)  # 0-10
    # Overall calculated as average in views
    what_is_going_well = Column(Text)
    what_is_challenging = Column(Text)
    teacher_observations = Column(Text)
    support_needed = Column(Boolean, default=False)
    follow_up_required = Column(Boolean, default=False)
    created_date = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('student_id', 'assessment_date', name='uq_student_wellbeing_date'),
    )
    
    # Relationships
    student = relationship("Student", back_populates="wellbeing")

# ============================================================================
# LAYER 6: COMMUNICATION MODEL
# ============================================================================

class Message(Base):
    """Messages between users"""
    __tablename__ = "message"
    
    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_id = Column(UUID(as_uuid=True), ForeignKey('user.user_id', ondelete='CASCADE'), nullable=False)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey('user.user_id', ondelete='CASCADE'), nullable=False)
    subject = Column(String(255))
    message_text = Column(Text, nullable=False)
    message_type = Column(String(50), default='feedback')  # feedback, notification, general, alert
    related_assessment_id = Column(UUID(as_uuid=True), ForeignKey('assessment.assessment_id', ondelete='SET NULL'), nullable=True)
    is_read = Column(Boolean, default=False)
    read_date = Column(DateTime)
    created_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="received_messages")
    assessment = relationship("Assessment", back_populates="messages")

# ============================================================================
# LAYER 7: RELATIONSHIPS & AGENCY MODELS
# ============================================================================

class CommunityDecision(Base):
    """Track decisions with student voice"""
    __tablename__ = "community_decision"
    
    decision_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    community_id = Column(UUID(as_uuid=True), ForeignKey('learning_community.community_id', ondelete='CASCADE'), nullable=False)
    unit_id = Column(UUID(as_uuid=True), ForeignKey('unit_of_inquiry.unit_id', ondelete='SET NULL'), nullable=True)
    decision_topic = Column(Text, nullable=False)
    decision_description = Column(Text)
    decision_options = Column(JSON, nullable=False)  # Array of options
    voice_collection_method = Column(String(50), default='poll')  # poll, survey, discussion, voting
    voice_collected_from = Column(JSON)  # Array of student IDs
    voice_count = Column(Integer, default=0)
    dissent_recorded = Column(Boolean, default=False)
    dissent_notes = Column(Text)
    final_decision = Column(String(255))
    decision_rationale = Column(Text)
    decision_date = Column(Date, default=date.today)
    implemented_date = Column(Date)
    created_date = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    community = relationship("LearningCommunity", back_populates="decisions")
    unit = relationship("UnitOfInquiry", back_populates="decisions")
    agency_events = relationship("AgencyEvent", back_populates="decision")

# ============================================================================

class AgencyEvent(Base):
    """Track voice, choice, ownership"""
    __tablename__ = "agency_event"
    
    agency_event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.user_id', ondelete='CASCADE'), nullable=False)
    unit_id = Column(UUID(as_uuid=True), ForeignKey('unit_of_inquiry.unit_id', ondelete='SET NULL'), nullable=True)
    agency_type = Column(String(50), default='voice')  # voice, choice, ownership
    specific_action = Column(Text, nullable=False)
    related_decision_id = Column(UUID(as_uuid=True), ForeignKey('community_decision.decision_id', ondelete='SET NULL'), nullable=True)
    event_date = Column(Date, default=date.today)
    celebration_recorded = Column(Boolean, default=False)
    evidence_notes = Column(Text)
    created_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="agency_events")
    unit = relationship("UnitOfInquiry", back_populates="agency_events")
    decision = relationship("CommunityDecision", back_populates="agency_events")

# ============================================================================
# LAYER 8: SYSTEM MODEL
# ============================================================================

class SystemLog(Base):
    """Audit trail"""
    __tablename__ = "system_log"
    
    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.user_id', ondelete='SET NULL'), nullable=True)
    action_type = Column(String(50), nullable=False)  # create, update, delete, login, logout
    entity_type = Column(String(100))  # table name
    entity_id = Column(UUID(as_uuid=True))
    old_values = Column(JSON)
    new_values = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    action_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

# ============================================================================
# EXPORT ALL MODELS
# ============================================================================

__all__ = [
    'LearningCommunity',
    'User',
    'Student',
    'Teacher',
    'TransdisciplinaryTheme',
    'UnitOfInquiry',
    'LineOfInquiry',
    'Concept',
    'UnitConcept',
    'LearningGoal',
    'AssessmentRubric',
    'Assessment',
    'StudentAssessment',
    'LearnerProfileAttribute',
    'StudentLearnerProfileProgress',
    'StudentInquiryProgress',
    'StudentWellBeing',
    'Message',
    'CommunityDecision',
    'AgencyEvent',
    'SystemLog',
]
