# app/routes/voice.py
"""
Voice and Agency routes
- POST /api/v1/voice/decisions - Teacher creates decision for student voice (T-03)
- POST /api/v1/voice/decisions/{decision_id}/vote - Student votes on decision
- GET /api/v1/voice/decisions - View community decisions
- GET /api/v1/voice/decisions/{decision_id} - Get decision with results
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user, get_current_teacher, get_current_student
from app.models import (
    User, Teacher, Student, CommunityDecision, StudentVote, AgencyEvent
)
from app.schemas.profile import (
    CommunityDecisionCreate,
    StudentVote as StudentVoteSchema,
    CommunityDecisionResponse,
)
from app.schemas.common import SuccessResponse, CreatedResponse
from uuid import uuid4
from datetime import datetime, date
import json

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])

# ============================================================================
# POST /api/v1/voice/decisions - Teacher Creates Decision (T-03)
# ============================================================================

@router.post("/decisions", response_model=CreatedResponse)
def create_decision(
    decision_data: CommunityDecisionCreate,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Teacher creates decision for student voice collection (T-03)
    
    MVP Simplified:
    - Simple class decision/poll
    - 2-5 options
    - Optional unit context
    - Students vote
    
    Returns:
        CreatedResponse with decision details
    """
    try:
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.user_id).first()
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teacher record not found"
            )
        
        decision_id = uuid4()
        new_decision = CommunityDecision(
            decision_id=decision_id,
            teacher_id=teacher.teacher_id,
            unit_id=decision_data.unit_id,
            decision_topic=decision_data.decision_topic,
            decision_description=decision_data.decision_description,
            decision_options=decision_data.decision_options,  # Stored as JSON list
            voice_collection_method=decision_data.voice_collection_method,
            voice_count=0,
            decision_date=date.today(),
            created_date=datetime.utcnow()
        )
        
        db.add(new_decision)
        db.commit()
        
        return CreatedResponse(
            status="created",
            message="Decision created successfully",
            data={
                "decision_id": str(decision_id),
                "decision_topic": new_decision.decision_topic,
                "decision_options": new_decision.decision_options
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating decision: {str(e)}"
        )

# ============================================================================
# POST /api/v1/voice/decisions/{decision_id}/vote - Student Votes (S-Voice)
# ============================================================================

@router.post("/decisions/{decision_id}/vote", response_model=SuccessResponse)
def student_vote(
    decision_id: str,
    vote_data: StudentVoteSchema,
    current_user: User = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """
    Student votes on decision
    
    Records student voice and agency
    """
    try:
        student = db.query(Student).filter(Student.user_id == current_user.user_id).first()
        if not student:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Student record not found"
            )
        
        # Get decision
        decision = db.query(CommunityDecision).filter(
            CommunityDecision.decision_id == decision_id
        ).first()
        
        if not decision:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Decision not found"
            )
        
        # Check if already voted
        existing_vote = db.query(StudentVote).filter(
            StudentVote.decision_id == decision_id,
            StudentVote.student_id == student.student_id
        ).first()
        
        if existing_vote:
            # Update vote
            existing_vote.selected_option = vote_data.selected_option
            existing_vote.vote_date = datetime.utcnow()
            db.commit()
            vote_id = existing_vote.student_vote_id
        else:
            # Create new vote
            vote_id = uuid4()
            new_vote = StudentVote(
                student_vote_id=vote_id,
                decision_id=decision_id,
                student_id=student.student_id,
                selected_option=vote_data.selected_option,
                vote_date=datetime.utcnow()
            )
            db.add(new_vote)
            
            # Update decision voice count
            decision.voice_count = (decision.voice_count or 0) + 1
            
            # Record agency event (student used voice)
            agency_event = AgencyEvent(
                agency_event_id=uuid4(),
                user_id=current_user.user_id,
                agency_type='voice',
                specific_action='voted_on_decision',
                event_date=date.today()
            )
            db.add(agency_event)
            
            db.commit()
        
        return SuccessResponse(
            status="success",
            message="Vote recorded successfully",
            data={
                "vote_id": str(vote_id),
                "decision_id": str(decision_id),
                "selected_option": vote_data.selected_option
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error recording vote: {str(e)}"
        )

# ============================================================================
# GET /api/v1/voice/decisions - List Community Decisions
# ============================================================================

@router.get("/decisions", response_model=SuccessResponse)
def list_decisions(
    unit_id: str = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List community decisions
    
    Students see decisions they can vote on
    Teachers see their created decisions
    """
    query = db.query(CommunityDecision)
    
    if unit_id:
        query = query.filter(CommunityDecision.unit_id == unit_id)
    
    total = query.count()
    decisions = query.order_by(CommunityDecision.decision_date.desc()).offset(skip).limit(limit).all()
    
    decision_list = [
        {
            "decision_id": str(d.decision_id),
            "decision_topic": d.decision_topic,
            "decision_options": d.decision_options,
            "voice_collection_method": d.voice_collection_method,
            "voice_count": d.voice_count,
            "decision_date": str(d.decision_date)
        }
        for d in decisions
    ]
    
    return SuccessResponse(
        status="success",
        message="Decisions retrieved",
        data={
            "decisions": decision_list,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    )

# ============================================================================
# GET /api/v1/voice/decisions/{decision_id} - Get Decision With Results
# ============================================================================

@router.get("/decisions/{decision_id}", response_model=SuccessResponse)
def get_decision_results(
    decision_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get decision with voting results and student's vote (if any)
    """
    decision = db.query(CommunityDecision).filter(
        CommunityDecision.decision_id == decision_id
    ).first()
    
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Decision not found"
        )
    
    # Get all votes
    all_votes = db.query(StudentVote).filter(
        StudentVote.decision_id == decision_id
    ).all()
    
    # Count votes by option
    vote_counts = {}
    for option in decision.decision_options:
        vote_counts[option] = len([v for v in all_votes if v.selected_option == option])
    
    # Get current user's vote (if student)
    my_vote = None
    if current_user.user_type == 'student':
        student = db.query(Student).filter(Student.user_id == current_user.user_id).first()
        my_vote_record = db.query(StudentVote).filter(
            StudentVote.decision_id == decision_id,
            StudentVote.student_id == student.student_id
        ).first()
        if my_vote_record:
            my_vote = my_vote_record.selected_option
    
    return SuccessResponse(
        status="success",
        message="Decision results retrieved",
        data={
            "decision_id": str(decision.decision_id),
            "decision_topic": decision.decision_topic,
            "decision_description": decision.decision_description,
            "decision_options": decision.decision_options,
            "vote_counts": vote_counts,
            "total_votes": decision.voice_count,
            "final_decision": decision.final_decision,
            "decision_rationale": decision.decision_rationale,
            "my_vote": my_vote
        }
    )

# ============================================================================
# GET /api/v1/voice/agency-events - View Agency Events
# ============================================================================

@router.get("/agency-events", response_model=SuccessResponse)
def get_agency_events(
    student_id: str = None,
    agency_type: str = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    View agency events (voice, choice, ownership celebrations)
    
    Teachers can view all student events
    Students can view their own
    """
    query = db.query(AgencyEvent)
    
    if current_user.user_type == 'student':
        query = query.filter(AgencyEvent.user_id == current_user.user_id)
    elif student_id:
        query = query.filter(AgencyEvent.user_id == student_id)
    
    if agency_type:
        query = query.filter(AgencyEvent.agency_type == agency_type)
    
    total = query.count()
    events = query.order_by(AgencyEvent.event_date.desc()).offset(skip).limit(limit).all()
    
    events_list = [
        {
            "agency_event_id": str(e.agency_event_id),
            "user_id": str(e.user_id),
            "agency_type": e.agency_type,
            "specific_action": e.specific_action,
            "event_date": str(e.event_date),
            "celebration_recorded": e.celebration_recorded
        }
        for e in events
    ]
    
    return SuccessResponse(
        status="success",
        message="Agency events retrieved",
        data={
            "events": events_list,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    )

# ============================================================================
# POST /api/v1/voice/decisions/{decision_id}/finalize - Finalize Decision (Teacher Only)
# ============================================================================

@router.post("/decisions/{decision_id}/finalize", response_model=SuccessResponse)
def finalize_decision(
    decision_id: str,
    final_decision: str,
    decision_rationale: str = None,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Teacher finalizes decision based on student voice
    
    Teacher reviews votes and makes final decision with rationale
    """
    decision = db.query(CommunityDecision).filter(
        CommunityDecision.decision_id == decision_id
    ).first()
    
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Decision not found"
        )
    
    # Check ownership
    teacher = db.query(Teacher).filter(Teacher.user_id == current_user.user_id).first()
    if decision.teacher_id != teacher.teacher_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only finalize your own decisions"
        )
    
    decision.final_decision = final_decision
    decision.decision_rationale = decision_rationale
    db.commit()
    
    return SuccessResponse(
        status="success",
        message="Decision finalized",
        data={
            "decision_id": str(decision_id),
            "final_decision": final_decision
        }
    )
