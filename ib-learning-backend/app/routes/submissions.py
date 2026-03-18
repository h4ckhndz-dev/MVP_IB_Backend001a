# app/routes/submissions.py
"""
Submission and feedback routes
- POST /api/v1/submissions - Student submits work (S-05)
- POST /api/v1/submissions/{submission_id}/feedback - Teacher provides feedback (T-06)
- GET /api/v1/submissions/{submission_id} - View feedback (S-06)
- GET /api/v1/assessments/{assessment_id}/submissions - Teacher views all submissions
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user, get_current_teacher, get_current_student
from app.models import (
    User, Student, Teacher, StudentAssessment, Assessment, Message
)
from app.schemas.assessment import (
    StudentAssessmentSubmit,
    StudentAssessmentResponse,
    TeacherFeedback,
)
from app.schemas.common import SuccessResponse, CreatedResponse
from uuid import uuid4
from datetime import datetime

router = APIRouter(prefix="/api/v1/submissions", tags=["submissions"])

# ============================================================================
# POST /api/v1/submissions - Student Submits Work (S-05)
# ============================================================================

@router.post("", response_model=CreatedResponse)
def submit_assessment(
    submission_data: StudentAssessmentSubmit,
    current_user: User = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """
    Student submits work for assessment (S-05)
    
    Student can submit:
    - Text response
    - File URLs (already uploaded to Supabase Storage)
    - Self-rating (emerging/developing/proficient/extending)
    
    Returns:
        CreatedResponse with submission confirmation
    """
    try:
        # Get student
        student = db.query(Student).filter(Student.user_id == current_user.user_id).first()
        if not student:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Student record not found"
            )
        
        # Check assessment exists
        assessment = db.query(Assessment).filter(
            Assessment.assessment_id == submission_data.assessment_id
        ).first()
        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment not found"
            )
        
        # Check for existing submission
        existing = db.query(StudentAssessment).filter(
            StudentAssessment.assessment_id == submission_data.assessment_id,
            StudentAssessment.student_id == student.student_id
        ).first()
        
        if existing:
            # Update existing submission
            existing.submission_text = submission_data.submission_text
            existing.submission_file_urls = submission_data.submission_file_urls
            existing.student_self_rating = submission_data.student_self_rating
            existing.submission_status = 'submitted'
            existing.submission_date = datetime.utcnow()
            db.commit()
            submission_id = existing.student_assessment_id
        else:
            # Create new submission
            submission_id = uuid4()
            new_submission = StudentAssessment(
                student_assessment_id=submission_id,
                assessment_id=submission_data.assessment_id,
                student_id=student.student_id,
                submission_status='submitted',
                submission_text=submission_data.submission_text,
                submission_file_urls=submission_data.submission_file_urls,
                student_self_rating=submission_data.student_self_rating,
                submission_date=datetime.utcnow()
            )
            db.add(new_submission)
            db.commit()
        
        return CreatedResponse(
            status="created",
            message="Work submitted successfully",
            data={
                "submission_id": str(submission_id),
                "assessment_id": str(submission_data.assessment_id),
                "submission_status": "submitted"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting work: {str(e)}"
        )

# ============================================================================
# POST /api/v1/submissions/{submission_id}/feedback - Teacher Provides Feedback (T-06)
# ============================================================================

@router.post("/{submission_id}/feedback", response_model=SuccessResponse)
def provide_feedback(
    submission_id: str,
    feedback_data: TeacherFeedback,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Teacher provides feedback on student submission (T-06)
    
    Teacher:
    - Reviews submission
    - Rates proficiency (emerging/developing/proficient/extending)
    - Provides feedback text
    - System auto-sends notification message to student
    
    Returns:
        SuccessResponse with feedback confirmation
    """
    try:
        # Get submission
        submission = db.query(StudentAssessment).filter(
            StudentAssessment.student_assessment_id == submission_id
        ).first()
        
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found"
            )
        
        # Get assessment and teacher check
        assessment = db.query(Assessment).filter(
            Assessment.assessment_id == submission.assessment_id
        ).first()
        
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.user_id).first()
        if assessment.teacher_id != teacher.teacher_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only grade your own assessments"
            )
        
        # Update submission with feedback
        submission.teacher_rating = feedback_data.teacher_rating
        submission.teacher_feedback = feedback_data.teacher_feedback
        submission.score_earned = feedback_data.score_earned
        submission.submission_status = 'graded'
        submission.feedback_date = datetime.utcnow()
        db.commit()
        
        # Auto-create notification message to student
        # (Get student user record)
        student = db.query(Student).filter(
            Student.student_id == submission.student_id
        ).first()
        student_user = db.query(User).filter(
            User.user_id == student.user_id
        ).first()
        
        notification = Message(
            message_id=uuid4(),
            sender_id=current_user.user_id,
            recipient_id=student_user.user_id,
            subject=f"Feedback on {assessment.assessment_title}",
            message_text=feedback_data.teacher_feedback,
            message_type='feedback',
            is_read=False,
            created_date=datetime.utcnow()
        )
        db.add(notification)
        db.commit()
        
        return SuccessResponse(
            status="success",
            message="Feedback provided successfully",
            data={
                "submission_id": str(submission_id),
                "submission_status": "graded",
                "rating": feedback_data.teacher_rating
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error providing feedback: {str(e)}"
        )

# ============================================================================
# GET /api/v1/submissions/{submission_id} - View Feedback (S-06)
# ============================================================================

@router.get("/{submission_id}", response_model=SuccessResponse)
def get_submission(
    submission_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get submission details with feedback (S-06)
    
    Student can view their own submission and feedback
    Teacher can view all submissions in their assessments
    """
    submission = db.query(StudentAssessment).filter(
        StudentAssessment.student_assessment_id == submission_id
    ).first()
    
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
    
    # Check access
    if current_user.user_type == 'student':
        student = db.query(Student).filter(Student.user_id == current_user.user_id).first()
        if submission.student_id != student.student_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own submissions"
            )
    elif current_user.user_type == 'teacher':
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.user_id).first()
        assessment = db.query(Assessment).filter(
            Assessment.assessment_id == submission.assessment_id
        ).first()
        if assessment.teacher_id != teacher.teacher_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    return SuccessResponse(
        status="success",
        message="Submission retrieved",
        data={
            "submission_id": str(submission.student_assessment_id),
            "assessment_id": str(submission.assessment_id),
            "submission_status": submission.submission_status,
            "submission_date": submission.submission_date,
            "submission_text": submission.submission_text,
            "submission_file_urls": submission.submission_file_urls,
            "student_self_rating": submission.student_self_rating,
            "teacher_rating": submission.teacher_rating,
            "teacher_feedback": submission.teacher_feedback,
            "score_earned": submission.score_earned,
            "feedback_date": submission.feedback_date
        }
    )

# ============================================================================
# GET /api/v1/assessments/{assessment_id}/submissions - Teacher Views All Submissions
# ============================================================================

@router.get("/assessment/{assessment_id}/submissions", response_model=SuccessResponse)
def get_assessment_submissions(
    assessment_id: str,
    submission_status: str = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Teacher views all student submissions for an assessment
    
    Query parameters:
        submission_status: Filter by status (not_submitted, submitted, graded, returned)
        skip: Pagination offset
        limit: Pagination limit
    """
    # Check assessment belongs to teacher
    assessment = db.query(Assessment).filter(Assessment.assessment_id == assessment_id).first()
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )
    
    teacher = db.query(Teacher).filter(Teacher.user_id == current_user.user_id).first()
    if assessment.teacher_id != teacher.teacher_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get submissions
    query = db.query(StudentAssessment).filter(
        StudentAssessment.assessment_id == assessment_id
    )
    
    if submission_status:
        query = query.filter(StudentAssessment.submission_status == submission_status)
    
    total = query.count()
    submissions = query.offset(skip).limit(limit).all()
    
    submissions_list = [
        {
            "submission_id": str(s.student_assessment_id),
            "student_id": str(s.student_id),
            "submission_status": s.submission_status,
            "submission_date": s.submission_date,
            "teacher_rating": s.teacher_rating,
            "score_earned": s.score_earned
        }
        for s in submissions
    ]
    
    return SuccessResponse(
        status="success",
        message="Submissions retrieved",
        data={
            "assessment_id": str(assessment_id),
            "assessment_title": assessment.assessment_title,
            "submissions": submissions_list,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    )
