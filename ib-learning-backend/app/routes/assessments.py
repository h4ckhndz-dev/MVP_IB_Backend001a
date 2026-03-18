# app/routes/assessments.py
"""
Assessment routes
- POST /api/v1/assessments - Create assessment (T-05)
- GET /api/v1/assessments - List assessments
- GET /api/v1/assessments/{assessment_id} - Get assessment details
- PATCH /api/v1/assessments/{assessment_id} - Update assessment
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user, get_current_teacher
from app.models import User, Teacher, Assessment, Unit
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentUpdate,
    AssessmentResponse,
    AssessmentListResponse,
)
from app.schemas.common import SuccessResponse, CreatedResponse
from uuid import uuid4
from datetime import datetime

router = APIRouter(prefix="/api/v1/assessments", tags=["assessments"])

# ============================================================================
# POST /api/v1/assessments - Create Assessment (T-05)
# ============================================================================

@router.post("", response_model=CreatedResponse)
def create_assessment(
    assessment_data: AssessmentCreate,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Create new assessment (T-05)
    
    Only teachers can create assessments.
    
    MVP Simplified:
    - Formative or Summative
    - Tied to Unit and Learning Goal
    - Uses pre-built rubric (not custom)
    - Optional file submission
    
    Returns:
        CreatedResponse with assessment details
    """
    try:
        # Get teacher
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.user_id).first()
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teacher record not found"
            )
        
        # Verify unit exists and belongs to teacher
        unit = db.query(Unit).filter(Unit.unit_id == assessment_data.unit_id).first()
        if not unit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unit not found"
            )
        
        if unit.teacher_id != teacher.teacher_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only create assessments for your own units"
            )
        
        # Create assessment
        assessment_id = uuid4()
        new_assessment = Assessment(
            assessment_id=assessment_id,
            unit_id=assessment_data.unit_id,
            teacher_id=teacher.teacher_id,
            goal_id=assessment_data.goal_id,
            rubric_id=assessment_data.rubric_id,
            assessment_title=assessment_data.assessment_title,
            assessment_description=assessment_data.assessment_description,
            assessment_type=assessment_data.assessment_type,
            due_date=assessment_data.due_date,
            submission_required=assessment_data.submission_required,
            max_score=assessment_data.max_score,
            created_date=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_assessment)
        db.commit()
        
        return CreatedResponse(
            status="created",
            message="Assessment created successfully",
            data={
                "assessment_id": str(assessment_id),
                "assessment_title": new_assessment.assessment_title,
                "due_date": new_assessment.due_date,
                "assessment_type": new_assessment.assessment_type
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating assessment: {str(e)}"
        )

# ============================================================================
# GET /api/v1/assessments - List Assessments
# ============================================================================

@router.get("", response_model=SuccessResponse)
def list_assessments(
    unit_id: str = None,
    assessment_type: str = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List assessments
    
    Query parameters:
        unit_id: Filter by unit
        assessment_type: Filter by type (formative/summative)
        skip: Pagination offset
        limit: Pagination limit
    """
    query = db.query(Assessment)
    
    # If teacher, show own assessments
    # If student, show assessments from enrolled units
    if current_user.user_type == 'teacher':
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.user_id).first()
        query = query.filter(Assessment.teacher_id == teacher.teacher_id)
    
    if unit_id:
        query = query.filter(Assessment.unit_id == unit_id)
    
    if assessment_type:
        query = query.filter(Assessment.assessment_type == assessment_type)
    
    total = query.count()
    assessments = query.order_by(Assessment.due_date).offset(skip).limit(limit).all()
    
    assessment_list = [
        AssessmentListResponse(
            assessment_id=a.assessment_id,
            assessment_title=a.assessment_title,
            assessment_type=a.assessment_type,
            due_date=a.due_date,
            submission_required=a.submission_required
        )
        for a in assessments
    ]
    
    return SuccessResponse(
        status="success",
        message="Assessments retrieved",
        data={
            "assessments": assessment_list,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    )

# ============================================================================
# GET /api/v1/assessments/{assessment_id} - Get Assessment Details
# ============================================================================

@router.get("/{assessment_id}", response_model=SuccessResponse)
def get_assessment(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get assessment details
    """
    assessment = db.query(Assessment).filter(Assessment.assessment_id == assessment_id).first()
    
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )
    
    return SuccessResponse(
        status="success",
        message="Assessment retrieved",
        data={
            "assessment_id": str(assessment.assessment_id),
            "assessment_title": assessment.assessment_title,
            "assessment_description": assessment.assessment_description,
            "assessment_type": assessment.assessment_type,
            "due_date": assessment.due_date,
            "submission_required": assessment.submission_required,
            "max_score": assessment.max_score,
            "unit_id": str(assessment.unit_id),
            "goal_id": str(assessment.goal_id),
            "rubric_id": str(assessment.rubric_id) if assessment.rubric_id else None
        }
    )

# ============================================================================
# PATCH /api/v1/assessments/{assessment_id} - Update Assessment
# ============================================================================

@router.patch("/{assessment_id}", response_model=SuccessResponse)
def update_assessment(
    assessment_id: str,
    assessment_data: AssessmentUpdate,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Update assessment (teacher only)
    """
    assessment = db.query(Assessment).filter(Assessment.assessment_id == assessment_id).first()
    
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )
    
    # Check ownership
    teacher = db.query(Teacher).filter(Teacher.user_id == current_user.user_id).first()
    if assessment.teacher_id != teacher.teacher_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own assessments"
        )
    
    # Update fields
    if assessment_data.assessment_title:
        assessment.assessment_title = assessment_data.assessment_title
    if assessment_data.assessment_description:
        assessment.assessment_description = assessment_data.assessment_description
    if assessment_data.due_date:
        assessment.due_date = assessment_data.due_date
    if assessment_data.max_score is not None:
        assessment.max_score = assessment_data.max_score
    
    assessment.updated_at = datetime.utcnow()
    db.commit()
    
    return SuccessResponse(
        status="success",
        message="Assessment updated successfully",
        data={"assessment_id": str(assessment.assessment_id)}
    )

# ============================================================================
# GET /api/v1/assessments/{assessment_id}/status - Assessment Status for Student
# ============================================================================

@router.get("/{assessment_id}/status", response_model=SuccessResponse)
def get_assessment_status(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get student's submission status for an assessment
    """
    from app.models import StudentAssessment, Student
    
    assessment = db.query(Assessment).filter(Assessment.assessment_id == assessment_id).first()
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )
    
    # Get student
    student = db.query(Student).filter(Student.user_id == current_user.user_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student record not found"
        )
    
    # Get submission status
    submission = db.query(StudentAssessment).filter(
        StudentAssessment.assessment_id == assessment_id,
        StudentAssessment.student_id == student.student_id
    ).first()
    
    status_data = {
        "assessment_id": str(assessment.assessment_id),
        "assessment_title": assessment.assessment_title,
        "due_date": assessment.due_date,
        "submission_status": submission.submission_status if submission else "not_submitted",
        "submission_date": submission.submission_date if submission else None,
        "teacher_rating": submission.teacher_rating if submission else None,
        "score_earned": submission.score_earned if submission else None
    }
    
    return SuccessResponse(
        status="success",
        message="Assessment status retrieved",
        data=status_data
    )
