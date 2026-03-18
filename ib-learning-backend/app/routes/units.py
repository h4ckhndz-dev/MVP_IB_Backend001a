# app/routes/units.py
"""
Unit of Inquiry routes
- POST /api/v1/units - Create unit (T-01)
- GET /api/v1/units - List units
- GET /api/v1/units/{unit_id} - Get unit details
- PATCH /api/v1/units/{unit_id} - Update unit
- POST /api/v1/units/{unit_id}/join - Student joins unit (S-02)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user, get_current_teacher, get_current_student
from app.models import (
    User, Teacher, Unit, LearningGoal, LinOfInquiry, UnitConcept,
    StudentInquiryProgress
)
from app.schemas.unit import (
    UnitOfInquiryCreate,
    UnitOfInquiryUpdate,
    UnitOfInquiryResponse,
    UnitListResponse,
    StudentInquiryProgressCreate,
    StudentInquiryProgressResponse,
)
from app.schemas.common import SuccessResponse, CreatedResponse, PaginatedResponse
from uuid import uuid4
from datetime import datetime
from typing import List

router = APIRouter(prefix="/api/v1/units", tags=["units"])

# ============================================================================
# POST /api/v1/units - Create Unit (T-01)
# ============================================================================

@router.post("", response_model=CreatedResponse)
def create_unit(
    unit_data: UnitOfInquiryCreate,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Create new Unit of Inquiry (T-01)
    
    Only teachers can create units.
    Includes:
    - Unit basic info
    - Learning goals
    - Concepts
    - Inquiry questions
    
    Returns:
        CreatedResponse with new unit details
    """
    try:
        # Get teacher record
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.user_id).first()
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teacher record not found"
            )
        
        # Create unit
        unit_id = uuid4()
        new_unit = Unit(
            unit_id=unit_id,
            teacher_id=teacher.teacher_id,
            learning_community_id=current_user.learning_community_id,
            unit_title=unit_data.unit_title,
            central_idea=unit_data.central_idea,
            unit_description=unit_data.unit_description,
            theme_id=unit_data.theme_id,
            grade_level=unit_data.grade_level,
            duration_weeks=unit_data.duration_weeks,
            start_date=unit_data.start_date,
            end_date=unit_data.end_date,
            unit_status='planning',
            created_date=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_unit)
        db.flush()
        
        # Add learning goals
        for goal_data in unit_data.learning_goals:
            goal = LearningGoal(
                goal_id=uuid4(),
                unit_id=unit_id,
                goal_description=goal_data.goal_description,
                goal_type=goal_data.goal_type,
                sequence_order=goal_data.sequence_order
            )
            db.add(goal)
        
        # Add concepts
        for concept_data in unit_data.concepts:
            unit_concept = UnitConcept(
                unit_concept_id=uuid4(),
                unit_id=unit_id,
                concept_id=concept_data.concept_id,
                emphasis_level=concept_data.emphasis_level
            )
            db.add(unit_concept)
        
        # Add inquiry questions
        for inquiry_data in unit_data.inquiry_questions:
            inquiry = LinOfInquiry(
                inquiry_id=uuid4(),
                unit_id=unit_id,
                inquiry_question=inquiry_data.inquiry_question,
                inquiry_focus=inquiry_data.inquiry_focus,
                sequence_order=inquiry_data.sequence_order
            )
            db.add(inquiry)
        
        db.commit()
        
        return CreatedResponse(
            status="created",
            message="Unit created successfully",
            data={
                "unit_id": str(unit_id),
                "unit_title": new_unit.unit_title,
                "central_idea": new_unit.central_idea,
                "unit_status": new_unit.unit_status
            }
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating unit: {str(e)}"
        )

# ============================================================================
# GET /api/v1/units - List Units
# ============================================================================

@router.get("", response_model=SuccessResponse)
def list_units(
    grade_level: int = None,
    unit_status: str = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List units in user's learning community
    
    Query parameters:
        grade_level: Filter by grade level
        unit_status: Filter by status (planning, active, completed, archived)
        skip: Number of records to skip
        limit: Number of records to return
    """
    query = db.query(Unit).filter(
        Unit.learning_community_id == current_user.learning_community_id
    )
    
    if grade_level is not None:
        query = query.filter(Unit.grade_level == grade_level)
    
    if unit_status:
        query = query.filter(Unit.unit_status == unit_status)
    
    total = query.count()
    units = query.offset(skip).limit(limit).all()
    
    unit_list = [
        UnitListResponse(
            unit_id=unit.unit_id,
            unit_title=unit.unit_title,
            central_idea=unit.central_idea,
            grade_level=unit.grade_level,
            unit_status=unit.unit_status,
            start_date=unit.start_date,
            end_date=unit.end_date
        )
        for unit in units
    ]
    
    return SuccessResponse(
        status="success",
        message="Units retrieved",
        data={
            "units": unit_list,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    )

# ============================================================================
# GET /api/v1/units/{unit_id} - Get Unit Details
# ============================================================================

@router.get("/{unit_id}", response_model=SuccessResponse)
def get_unit(
    unit_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed unit information
    """
    unit = db.query(Unit).filter(Unit.unit_id == unit_id).first()
    
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found"
        )
    
    # Check access (same community)
    if unit.learning_community_id != current_user.learning_community_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return SuccessResponse(
        status="success",
        message="Unit details retrieved",
        data={
            "unit_id": str(unit.unit_id),
            "unit_title": unit.unit_title,
            "central_idea": unit.central_idea,
            "unit_description": unit.unit_description,
            "grade_level": unit.grade_level,
            "unit_status": unit.unit_status,
            "start_date": unit.start_date,
            "end_date": unit.end_date,
            "duration_weeks": unit.duration_weeks
        }
    )

# ============================================================================
# PATCH /api/v1/units/{unit_id} - Update Unit
# ============================================================================

@router.patch("/{unit_id}", response_model=SuccessResponse)
def update_unit(
    unit_id: str,
    unit_data: UnitOfInquiryUpdate,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Update unit (teacher only)
    """
    unit = db.query(Unit).filter(Unit.unit_id == unit_id).first()
    
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found"
        )
    
    # Check ownership
    teacher = db.query(Teacher).filter(Teacher.user_id == current_user.user_id).first()
    if unit.teacher_id != teacher.teacher_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own units"
        )
    
    # Update fields
    if unit_data.unit_title:
        unit.unit_title = unit_data.unit_title
    if unit_data.unit_description:
        unit.unit_description = unit_data.unit_description
    if unit_data.start_date:
        unit.start_date = unit_data.start_date
    if unit_data.end_date:
        unit.end_date = unit_data.end_date
    if unit_data.unit_status:
        unit.unit_status = unit_data.unit_status
    
    unit.updated_at = datetime.utcnow()
    db.commit()
    
    return SuccessResponse(
        status="success",
        message="Unit updated successfully",
        data={"unit_id": str(unit.unit_id)}
    )

# ============================================================================
# POST /api/v1/units/{unit_id}/join - Student Joins Unit (S-02)
# ============================================================================

@router.post("/{unit_id}/join", response_model=CreatedResponse)
def join_unit(
    unit_id: str,
    current_user: User = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """
    Student joins unit (S-02)
    """
    # Get unit
    unit = db.query(Unit).filter(Unit.unit_id == unit_id).first()
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found"
        )
    
    # Get student
    from app.models import Student
    student = db.query(Student).filter(Student.user_id == current_user.user_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student record not found"
        )
    
    # Check if already joined
    existing = db.query(StudentInquiryProgress).filter(
        StudentInquiryProgress.student_id == student.student_id,
        StudentInquiryProgress.unit_id == unit_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already enrolled in this unit"
        )
    
    # Create enrollment
    progress = StudentInquiryProgress(
        inquiry_progress_id=uuid4(),
        student_id=student.student_id,
        unit_id=unit_id,
        join_date=datetime.utcnow().date(),
        participation_level='enrolled',
        completion_percentage=0
    )
    
    db.add(progress)
    db.commit()
    
    return CreatedResponse(
        status="created",
        message="Successfully enrolled in unit",
        data={
            "unit_id": str(unit_id),
            "unit_title": unit.unit_title
        }
    )
