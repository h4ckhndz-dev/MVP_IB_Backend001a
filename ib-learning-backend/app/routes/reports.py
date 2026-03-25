# app/routes/reports.py
"""
Report routes
- GET /api/v1/reports/student/{student_id} - Student progress report (T-10)
- GET /api/v1/reports/unit/{unit_id} - Unit progress report
- GET /api/v1/reports/my-progress - Student views own progress report
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user, get_current_teacher, get_current_student
from app.models import (
    User, Student, Teacher, Unit, StudentInquiryProgress,
    StudentAssessment, StudentLearnerProfileProgress, StudentWellBeing
)
from app.schemas.common import SuccessResponse
from uuid import uuid4
from datetime import datetime, date

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

# ============================================================================
# GET /api/v1/reports/student/{student_id} - Student Progress Report (T-10)
# ============================================================================

@router.get("/student/{student_id}", response_model=SuccessResponse)
def get_student_report(
    student_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate comprehensive student progress report (T-10)
    
    Includes:
    - Unit enrollment and completion
    - Assessment scores
    - Learner profile progress
    - Well-being status
    - Agency/voice events
    
    Teachers can view their students' reports
    Students can view their own
    """
    # Get student
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Check access
    if current_user.user_type == 'student':
        if student.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own report"
            )
    
    # Get student user
    student_user = db.query(User).filter(User.user_id == student.user_id).first()
    
    # Units enrolled
    unit_enrollments = db.query(StudentInquiryProgress).filter(
        StudentInquiryProgress.student_id == student_id
    ).all()
    
    units_enrolled = len(unit_enrollments)
    units_completed = len([u for u in unit_enrollments if u.completion_percentage == 100])
    
    # Assessments
    assessments = db.query(StudentAssessment).filter(
        StudentAssessment.student_id == student_id
    ).all()
    
    assessments_completed = len([a for a in assessments if a.submission_status in ['submitted', 'graded']])
    assessments_graded = len([a for a in assessments if a.submission_status == 'graded'])
    
    avg_assessment_score = 0
    if assessments_graded > 0:
        scores = [a.score_earned for a in assessments if a.score_earned is not None]
        avg_assessment_score = sum(scores) / len(scores) if scores else 0
    
    # Learner profile
    profile_progress = db.query(StudentLearnerProfileProgress).filter(
        StudentLearnerProfileProgress.student_id == student_id
    ).all()
    
    profile_data = [
        {
            "attribute_name": p.attribute_id,  # Should join to get name
            "student_proficiency_level": p.student_proficiency_level,
            "teacher_proficiency_level": p.teacher_proficiency_level,
            "assessment_date": str(p.assessment_date)
        }
        for p in profile_progress
    ]
    
    # Well-being
    wellbeing_records = db.query(StudentWellBeing).filter(
        StudentWellBeing.student_id == student_id
    ).order_by(StudentWellBeing.assessment_date.desc()).all()
    
    latest_wellbeing = None
    if wellbeing_records:
        latest = wellbeing_records[0]
        latest_wellbeing = {
            "assessment_date": str(latest.assessment_date),
            "overall_score": latest.overall_wellbeing_score,
            "support_needed": latest.support_needed
        }
    
    # Summary statistics
    report_data = {
        "student_id": str(student_id),
        "student_name": f"{student_user.first_name} {student_user.last_name}",
        "grade_level": student.grade_level,
        "report_generated_date": str(date.today()),
        "units": {
            "total_enrolled": units_enrolled,
            "completed": units_completed,
            "completion_percentage": (units_completed / units_enrolled * 100) if units_enrolled > 0 else 0
        },
        "assessments": {
            "total": len(assessments),
            "completed": assessments_completed,
            "graded": assessments_graded,
            "average_score": round(avg_assessment_score, 2)
        },
        "learner_profile": {
            "total_attributes": len(profile_progress),
            "attributes": profile_data
        },
        "wellbeing": latest_wellbeing,
        "summary": {
            "overall_progress": "On Track" if units_enrolled > 0 and units_completed > 0 else "In Progress",
            "engagement_level": "High" if assessments_completed >= len(assessments) * 0.8 else "Moderate"
        }
    }
    
    return SuccessResponse(
        status="success",
        message="Student report generated",
        data=report_data
    )

# ============================================================================
# GET /api/v1/reports/unit/{unit_id} - Unit Progress Report
# ============================================================================

@router.get("/unit/{unit_id}", response_model=SuccessResponse)
def get_unit_report(
    unit_id: str,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Generate unit progress report
    
    Shows:
    - Student enrollment
    - Assessment completion
    - Overall progress
    """
    # Get unit
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
            detail="You can only view your own units"
        )
    
    # Get enrolled students
    enrollments = db.query(StudentInquiryProgress).filter(
        StudentInquiryProgress.unit_id == unit_id
    ).all()
    
    total_students = len(enrollments)
    completed_students = len([e for e in enrollments if e.completion_percentage == 100])
    
    # Get assessments
    from app.models import Assessment
    assessments = db.query(Assessment).filter(Assessment.unit_id == unit_id).all()
    
    total_assessments = len(assessments)
    assessments_with_submissions = 0
    assessments_graded = 0
    
    for assessment in assessments:
        submissions = db.query(StudentAssessment).filter(
            StudentAssessment.assessment_id == assessment.assessment_id,
            StudentAssessment.submission_status.in_(['submitted', 'graded'])
        ).all()
        
        if submissions:
            assessments_with_submissions += 1
            graded = len([s for s in submissions if s.submission_status == 'graded'])
            assessments_graded += len([s for s in submissions if s.submission_status == 'graded'])
    
    report_data = {
        "unit_id": str(unit_id),
        "unit_title": unit.unit_title,
        "central_idea": unit.central_idea,
        "teacher_id": str(unit.teacher_id),
        "unit_status": unit.unit_status,
        "start_date": str(unit.start_date),
        "end_date": str(unit.end_date) if unit.end_date else None,
        "report_generated_date": str(date.today()),
        "students": {
            "total_enrolled": total_students,
            "completed": completed_students,
            "completion_percentage": (completed_students / total_students * 100) if total_students > 0 else 0
        },
        "assessments": {
            "total": total_assessments,
            "with_submissions": assessments_with_submissions,
            "graded": assessments_graded,
            "grading_percentage": (assessments_graded / (total_assessments * total_students) * 100) if total_assessments > 0 and total_students > 0 else 0
        }
    }
    
    return SuccessResponse(
        status="success",
        message="Unit report generated",
        data=report_data
    )

# ============================================================================
# GET /api/v1/reports/my-progress - Student Views Own Progress Report
# ============================================================================

@router.get("/my-progress", response_model=SuccessResponse)
def get_my_progress(
    current_user: User = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """
    Student views their own progress report
    """
    student = db.query(Student).filter(Student.user_id == current_user.user_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student record not found"
        )
    
    # Reuse student report logic
    # Get student info
    student_user = current_user
    
    # Units enrolled
    unit_enrollments = db.query(StudentInquiryProgress).filter(
        StudentInquiryProgress.student_id == student.student_id
    ).all()
    
    units_enrolled = len(unit_enrollments)
    units_completed = len([u for u in unit_enrollments if u.completion_percentage == 100])
    
    # Assessments
    assessments = db.query(StudentAssessment).filter(
        StudentAssessment.student_id == student.student_id
    ).all()
    
    assessments_pending = len([a for a in assessments if a.submission_status == 'not_submitted'])
    assessments_submitted = len([a for a in assessments if a.submission_status in ['submitted']])
    assessments_graded = len([a for a in assessments if a.submission_status == 'graded'])
    
    avg_grade = 0
    if assessments_graded > 0:
        scores = [a.score_earned for a in assessments if a.score_earned is not None]
        avg_grade = sum(scores) / len(scores) if scores else 0
    
    # Well-being status
    latest_wellbeing = db.query(StudentWellBeing).filter(
        StudentWellBeing.student_id == student.student_id
    ).order_by(StudentWellBeing.assessment_date.desc()).first()
    
    wellbeing_status = None
    if latest_wellbeing:
        score = latest_wellbeing.overall_wellbeing_score
        if score >= 8:
            status_label = "Excellent"
        elif score >= 6:
            status_label = "Good"
        elif score >= 4:
            status_label = "Fair"
        else:
            status_label = "Needs Support"
        
        wellbeing_status = {
            "latest_score": score,
            "status": status_label,
            "assessment_date": str(latest_wellbeing.assessment_date)
        }
    
    report_data = {
        "student_name": f"{student_user.first_name} {student_user.last_name}",
        "grade_level": student.grade_level,
        "report_generated_date": str(date.today()),
        "units": {
            "enrolled": units_enrolled,
            "completed": units_completed
        },
        "assessments": {
            "pending": assessments_pending,
            "submitted": assessments_submitted,
            "graded": assessments_graded,
            "average_grade": round(avg_grade, 2)
        },
        "wellbeing": wellbeing_status,
        "next_steps": [
            f"Complete {assessments_pending} pending assessments" if assessments_pending > 0 else None,
            "Check feedback on graded work" if assessments_graded > 0 else None
        ]
    }
    
    # Filter out None values
    next_steps = [s for s in report_data["next_steps"] if s]
    report_data["next_steps"] = next_steps
    
    return SuccessResponse(
        status="success",
        message="Your progress report",
        data=report_data
    )
