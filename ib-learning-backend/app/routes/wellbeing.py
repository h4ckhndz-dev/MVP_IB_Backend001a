# app/routes/wellbeing.py
"""
Well-Being routes
- POST /api/v1/wellbeing - Student records well-being check-in (S-09)
- GET /api/v1/wellbeing/my-status - Student views their well-being status
- GET /api/v1/wellbeing/student/{student_id} - Teacher views student's well-being
- GET /api/v1/wellbeing/class - Teacher views class well-being overview
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user, get_current_teacher, get_current_student
from app.models import User, Student, StudentWellBeing
from app.schemas.profile import (
    StudentWellBeingCheckIn,
    StudentWellBeingResponse,
    WellBeingStatus,
)
from app.schemas.common import SuccessResponse, CreatedResponse
from uuid import uuid4
from datetime import datetime, date
from typing import List

router = APIRouter(prefix="/api/v1/wellbeing", tags=["wellbeing"])

# ============================================================================
# POST /api/v1/wellbeing - Student Records Well-Being Check-In (S-09)
# ============================================================================

@router.post("", response_model=CreatedResponse)
def check_in_wellbeing(
    wellbeing_data: StudentWellBeingCheckIn,
    current_user: User = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """
    Student records well-being check-in (S-09)
    
    Student answers 5 questions:
    1. Physical health (0-10)
    2. Emotional health (0-10)
    3. Sense of belonging (0-10)
    4. What's going well (text)
    5. What's challenging (text)
    
    System automatically calculates overall_wellbeing_score = avg(phys, emot, belong)
    
    Returns:
        CreatedResponse with check-in confirmation
    """
    try:
        # Get student
        student = db.query(Student).filter(Student.user_id == current_user.user_id).first()
        if not student:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Student record not found"
            )
        
        # Calculate overall score (average of 3 dimensions)
        overall_score = (
            wellbeing_data.physical_health_score +
            wellbeing_data.emotional_health_score +
            wellbeing_data.sense_of_belonging_score
        ) // 3
        
        # Create check-in
        wellbeing_id = uuid4()
        new_checkin = StudentWellBeing(
            wellbeing_id=wellbeing_id,
            student_id=student.student_id,
            physical_health_score=wellbeing_data.physical_health_score,
            emotional_health_score=wellbeing_data.emotional_health_score,
            sense_of_belonging_score=wellbeing_data.sense_of_belonging_score,
            what_is_going_well=wellbeing_data.what_is_going_well,
            what_is_challenging=wellbeing_data.what_is_challenging,
            overall_wellbeing_score=overall_score,
            assessment_date=date.today(),
            support_needed=overall_score < 5,  # Flag if score is low
            follow_up_required=overall_score < 4,  # Flag for teacher follow-up if very low
            created_date=datetime.utcnow()
        )
        
        db.add(new_checkin)
        db.commit()
        
        return CreatedResponse(
            status="created",
            message="Well-being check-in recorded successfully",
            data={
                "wellbeing_id": str(wellbeing_id),
                "assessment_date": str(new_checkin.assessment_date),
                "overall_wellbeing_score": overall_score,
                "support_needed": new_checkin.support_needed
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error recording check-in: {str(e)}"
        )

# ============================================================================
# GET /api/v1/wellbeing/my-status - Student Views Own Well-Being Status
# ============================================================================

@router.get("/my-status", response_model=SuccessResponse)
def get_my_wellbeing_status(
    current_user: User = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """
    Student views their current well-being status
    
    Shows latest check-in and trend
    """
    student = db.query(Student).filter(Student.user_id == current_user.user_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student record not found"
        )
    
    # Get latest check-in
    latest = db.query(StudentWellBeing).filter(
        StudentWellBeing.student_id == student.student_id
    ).order_by(StudentWellBeing.assessment_date.desc()).first()
    
    if not latest:
        return SuccessResponse(
            status="success",
            message="No well-being data yet",
            data=None
        )
    
    # Determine status
    score = latest.overall_wellbeing_score
    if score >= 8:
        status_label = "Excellent"
    elif score >= 6:
        status_label = "Good"
    elif score >= 4:
        status_label = "Fair"
    else:
        status_label = "Needs Support"
    
    return SuccessResponse(
        status="success",
        message="Well-being status retrieved",
        data={
            "latest_score": latest.overall_wellbeing_score,
            "status": status_label,
            "last_assessment_date": str(latest.assessment_date),
            "physical_health": latest.physical_health_score,
            "emotional_health": latest.emotional_health_score,
            "sense_of_belonging": latest.sense_of_belonging_score,
            "support_needed": latest.support_needed
        }
    )

# ============================================================================
# GET /api/v1/wellbeing/student/{student_id} - Teacher Views Student Well-Being
# ============================================================================

@router.get("/student/{student_id}", response_model=SuccessResponse)
def get_student_wellbeing(
    student_id: str,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Teacher views a student's well-being trend
    
    Shows all check-ins and identifies students needing support
    """
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Get all well-being records
    records = db.query(StudentWellBeing).filter(
        StudentWellBeing.student_id == student_id
    ).order_by(StudentWellBeing.assessment_date.desc()).all()
    
    if not records:
        return SuccessResponse(
            status="success",
            message="No well-being data for this student",
            data=None
        )
    
    # Calculate trend
    if len(records) >= 2:
        latest = records[0].overall_wellbeing_score
        previous = records[1].overall_wellbeing_score
        if latest > previous:
            trend = "improving"
        elif latest < previous:
            trend = "declining"
        else:
            trend = "stable"
    else:
        trend = None
    
    checkins = [
        {
            "assessment_date": str(r.assessment_date),
            "overall_score": r.overall_wellbeing_score,
            "physical": r.physical_health_score,
            "emotional": r.emotional_health_score,
            "belonging": r.sense_of_belonging_score,
            "going_well": r.what_is_going_well,
            "challenging": r.what_is_challenging,
            "support_needed": r.support_needed
        }
        for r in records
    ]
    
    return SuccessResponse(
        status="success",
        message="Student well-being retrieved",
        data={
            "student_id": str(student_id),
            "checkins": checkins,
            "average_score": sum(r.overall_wellbeing_score for r in records) // len(records),
            "trend": trend,
            "needs_follow_up": any(r.follow_up_required for r in records)
        }
    )

# ============================================================================
# GET /api/v1/wellbeing/class - Teacher Views Class Well-Being Overview
# ============================================================================

@router.get("/class", response_model=SuccessResponse)
def get_class_wellbeing(
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Teacher views class well-being overview
    
    Shows:
    - Class average scores
    - Students needing support
    - Trends
    """
    from app.models import Teacher, StudentInquiryProgress, Unit
    
    # Get teacher's students via units
    teacher = db.query(Teacher).filter(Teacher.user_id == current_user.user_id).first()
    
    # Get all units taught by teacher
    teacher_units = db.query(Unit).filter(Unit.teacher_id == teacher.teacher_id).all()
    unit_ids = [u.unit_id for u in teacher_units]
    
    if not unit_ids:
        return SuccessResponse(
            status="success",
            message="No units found",
            data=None
        )
    
    # Get all students in those units
    enrolled = db.query(StudentInquiryProgress).filter(
        StudentInquiryProgress.unit_id.in_(unit_ids)
    ).all()
    
    student_ids = list(set(e.student_id for e in enrolled))
    
    if not student_ids:
        return SuccessResponse(
            status="success",
            message="No students enrolled",
            data=None
        )
    
    # Get latest well-being for each student
    student_status = []
    scores = []
    
    for sid in student_ids:
        latest = db.query(StudentWellBeing).filter(
            StudentWellBeing.student_id == sid
        ).order_by(StudentWellBeing.assessment_date.desc()).first()
        
        if latest:
            scores.append(latest.overall_wellbeing_score)
            student_status.append({
                "student_id": str(sid),
                "latest_score": latest.overall_wellbeing_score,
                "assessment_date": str(latest.assessment_date),
                "support_needed": latest.support_needed,
                "needs_follow_up": latest.follow_up_required
            })
    
    return SuccessResponse(
        status="success",
        message="Class well-being overview",
        data={
            "total_students": len(student_ids),
            "students_with_data": len(scores),
            "class_average_score": sum(scores) // len(scores) if scores else 0,
            "students_needing_support": len([s for s in student_status if s["support_needed"]]),
            "students_needing_follow_up": len([s for s in student_status if s["needs_follow_up"]]),
            "student_status": student_status
        }
    )
