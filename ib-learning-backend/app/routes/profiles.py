# app/routes/profiles.py
"""
Learner Profile routes
- POST /api/v1/profiles/self-assess - Student self-assesses (S-07)
- POST /api/v1/profiles/{attribute_id}/rate - Teacher rates student (T-07)
- GET /api/v1/profiles/student/{student_id} - Get student's profile progress
- GET /api/v1/profiles/attributes - List learner profile attributes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user, get_current_teacher, get_current_student
from app.models import (
    User, Student, Teacher, StudentLearnerProfileProgress,
    LearnerProfileAttribute
)
from app.schemas.profile import (
    StudentProfileSelfAssess,
    TeacherProfileRate,
    StudentLearnerProfileProgressResponse,
)
from app.schemas.common import SuccessResponse, CreatedResponse
from uuid import uuid4
from datetime import datetime, date

router = APIRouter(prefix="/api/v1/profiles", tags=["profiles"])

# ============================================================================
# GET /api/v1/profiles/attributes - List Learner Profile Attributes
# ============================================================================

@router.get("/attributes", response_model=SuccessResponse)
def get_attributes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all learner profile attributes
    
    MVP includes: Inquirer, Communicator, Thinker (3 only)
    """
    attributes = db.query(LearnerProfileAttribute).order_by(
        LearnerProfileAttribute.display_order
    ).all()
    
    attrs_list = [
        {
            "attribute_id": str(a.attribute_id),
            "attribute_name": a.attribute_name,
            "attribute_description": a.attribute_description,
            "observable_behaviors": a.observable_behaviors
        }
        for a in attributes
    ]
    
    return SuccessResponse(
        status="success",
        message="Attributes retrieved",
        data=attrs_list
    )

# ============================================================================
# POST /api/v1/profiles/self-assess - Student Self-Assesses (S-07)
# ============================================================================

@router.post("/self-assess", response_model=CreatedResponse)
def student_self_assess(
    self_assessment: StudentProfileSelfAssess,
    current_user: User = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """
    Student self-assesses on learner profile attribute (S-07)
    
    Student provides:
    - Self-rating (emerging/developing/proficient/extending)
    - Reflection on learning
    - Evidence artifacts (optional)
    
    Returns:
        CreatedResponse with assessment confirmation
    """
    try:
        # Get student
        student = db.query(Student).filter(Student.user_id == current_user.user_id).first()
        if not student:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Student record not found"
            )
        
        # Check attribute exists
        attribute = db.query(LearnerProfileAttribute).filter(
            LearnerProfileAttribute.attribute_id == self_assessment.attribute_id
        ).first()
        if not attribute:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attribute not found"
            )
        
        # Check for existing assessment on same date
        existing = db.query(StudentLearnerProfileProgress).filter(
            StudentLearnerProfileProgress.student_id == student.student_id,
            StudentLearnerProfileProgress.attribute_id == self_assessment.attribute_id,
            StudentLearnerProfileProgress.assessment_date == self_assessment.assessment_date
        ).first()
        
        if existing:
            # Update existing
            existing.student_proficiency_level = self_assessment.student_proficiency_level
            existing.student_self_reflection = self_assessment.student_self_reflection
            existing.evidence_artifacts = self_assessment.evidence_artifacts
            db.commit()
            progress_id = existing.progress_id
        else:
            # Create new
            progress_id = uuid4()
            new_progress = StudentLearnerProfileProgress(
                progress_id=progress_id,
                student_id=student.student_id,
                attribute_id=self_assessment.attribute_id,
                assessment_date=self_assessment.assessment_date,
                student_proficiency_level=self_assessment.student_proficiency_level,
                student_self_reflection=self_assessment.student_self_reflection,
                evidence_artifacts=self_assessment.evidence_artifacts
            )
            db.add(new_progress)
            db.commit()
        
        return CreatedResponse(
            status="created",
            message="Self-assessment recorded successfully",
            data={
                "progress_id": str(progress_id),
                "attribute_id": str(self_assessment.attribute_id),
                "proficiency_level": self_assessment.student_proficiency_level
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error recording self-assessment: {str(e)}"
        )

# ============================================================================
# POST /api/v1/profiles/{attribute_id}/rate - Teacher Rates Student (T-07)
# ============================================================================

@router.post("/{attribute_id}/rate", response_model=SuccessResponse)
def teacher_rate_student(
    attribute_id: str,
    student_id: str,
    rating_data: TeacherProfileRate,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Teacher rates student on learner profile attribute (T-07)
    
    Teacher provides:
    - Proficiency level (emerging/developing/proficient/extending)
    - Observation notes
    - Growth feedback
    
    Returns:
        SuccessResponse with rating confirmation
    """
    try:
        # Get student
        student = db.query(Student).filter(Student.student_id == student_id).first()
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        
        # Check attribute exists
        attribute = db.query(LearnerProfileAttribute).filter(
            LearnerProfileAttribute.attribute_id == attribute_id
        ).first()
        if not attribute:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attribute not found"
            )
        
        # Get or create progress record
        progress = db.query(StudentLearnerProfileProgress).filter(
            StudentLearnerProfileProgress.student_id == student_id,
            StudentLearnerProfileProgress.attribute_id == attribute_id
        ).first()
        
        if progress:
            # Update teacher rating
            progress.teacher_proficiency_level = rating_data.teacher_proficiency_level
            progress.teacher_observation = rating_data.teacher_observation
            progress.growth_notes = rating_data.growth_notes
        else:
            # Create new progress with teacher rating
            progress = StudentLearnerProfileProgress(
                progress_id=uuid4(),
                student_id=student_id,
                attribute_id=attribute_id,
                assessment_date=date.today(),
                teacher_proficiency_level=rating_data.teacher_proficiency_level,
                teacher_observation=rating_data.teacher_observation,
                growth_notes=rating_data.growth_notes
            )
            db.add(progress)
        
        db.commit()
        
        # Auto-create notification message to student
        student_user = db.query(User).filter(User.user_id == student.user_id).first()
        from app.models import Message
        notification = Message(
            message_id=uuid4(),
            sender_id=current_user.user_id,
            recipient_id=student_user.user_id,
            subject=f"Feedback on {attribute.attribute_name}",
            message_text=rating_data.teacher_observation,
            message_type='feedback',
            is_read=False,
            created_date=datetime.utcnow()
        )
        db.add(notification)
        db.commit()
        
        return SuccessResponse(
            status="success",
            message="Rating provided successfully",
            data={
                "student_id": str(student_id),
                "attribute_id": str(attribute_id),
                "rating": rating_data.teacher_proficiency_level
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error providing rating: {str(e)}"
        )

# ============================================================================
# GET /api/v1/profiles/student/{student_id} - Get Student's Profile Progress
# ============================================================================

@router.get("/student/{student_id}", response_model=SuccessResponse)
def get_student_profile(
    student_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get student's learner profile progress on all attributes
    
    Returns all self-assessments and teacher ratings
    """
    # Check access
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    if current_user.user_type == 'student':
        if student.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own profile"
            )
    
    # Get all profile progress
    progress_records = db.query(StudentLearnerProfileProgress).filter(
        StudentLearnerProfileProgress.student_id == student_id
    ).all()
    
    profile_data = [
        {
            "progress_id": str(p.progress_id),
            "attribute_id": str(p.attribute_id),
            "assessment_date": p.assessment_date,
            "student_proficiency_level": p.student_proficiency_level,
            "teacher_proficiency_level": p.teacher_proficiency_level,
            "student_self_reflection": p.student_self_reflection,
            "teacher_observation": p.teacher_observation,
            "growth_notes": p.growth_notes
        }
        for p in progress_records
    ]
    
    return SuccessResponse(
        status="success",
        message="Student profile retrieved",
        data={
            "student_id": str(student_id),
            "attributes": profile_data
        }
    )

# ============================================================================
# GET /api/v1/profiles/my-profile - Student Gets Own Profile
# ============================================================================

@router.get("/my-profile", response_model=SuccessResponse)
def get_my_profile(
    current_user: User = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """
    Student gets their own learner profile progress
    """
    student = db.query(Student).filter(Student.user_id == current_user.user_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student record not found"
        )
    
    # Get all profile progress
    progress_records = db.query(StudentLearnerProfileProgress).filter(
        StudentLearnerProfileProgress.student_id == student.student_id
    ).all()
    
    profile_data = [
        {
            "progress_id": str(p.progress_id),
            "attribute_id": str(p.attribute_id),
            "assessment_date": p.assessment_date,
            "student_proficiency_level": p.student_proficiency_level,
            "teacher_proficiency_level": p.teacher_proficiency_level,
            "student_self_reflection": p.student_self_reflection,
            "teacher_observation": p.teacher_observation,
            "growth_notes": p.growth_notes
        }
        for p in progress_records
    ]
    
    return SuccessResponse(
        status="success",
        message="Your profile retrieved",
        data=profile_data
    )
