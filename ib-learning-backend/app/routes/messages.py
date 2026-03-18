# app/routes/messages.py
"""
Messaging routes
- POST /api/v1/messages - Send message
- GET /api/v1/messages/inbox - Get inbox
- GET /api/v1/messages/{message_id} - Get message
- PATCH /api/v1/messages/{message_id}/read - Mark as read
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user
from app.models import User, Message
from app.schemas.profile import MessageCreate, MessageResponse
from app.schemas.common import SuccessResponse, CreatedResponse
from uuid import uuid4
from datetime import datetime

router = APIRouter(prefix="/api/v1/messages", tags=["messages"])

# ============================================================================
# POST /api/v1/messages - Send Message
# ============================================================================

@router.post("", response_model=CreatedResponse)
def send_message(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send message to another user
    """
    try:
        # Check recipient exists
        recipient = db.query(User).filter(User.user_id == message_data.recipient_id).first()
        if not recipient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recipient not found"
            )
        
        message_id = uuid4()
        new_message = Message(
            message_id=message_id,
            sender_id=current_user.user_id,
            recipient_id=message_data.recipient_id,
            subject=message_data.subject,
            message_text=message_data.message_text,
            message_type=message_data.message_type,
            is_read=False,
            created_date=datetime.utcnow()
        )
        
        db.add(new_message)
        db.commit()
        
        return CreatedResponse(
            status="created",
            message="Message sent successfully",
            data={
                "message_id": str(message_id),
                "recipient_id": str(message_data.recipient_id)
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending message: {str(e)}"
        )

# ============================================================================
# GET /api/v1/messages/inbox - Get Inbox
# ============================================================================

@router.get("/inbox", response_model=SuccessResponse)
def get_inbox(
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's inbox (received messages)
    """
    query = db.query(Message).filter(Message.recipient_id == current_user.user_id)
    
    if unread_only:
        query = query.filter(Message.is_read == False)
    
    total = query.count()
    messages = query.order_by(Message.created_date.desc()).offset(skip).limit(limit).all()
    
    # Get sender info
    messages_list = []
    for msg in messages:
        sender = db.query(User).filter(User.user_id == msg.sender_id).first()
        messages_list.append({
            "message_id": str(msg.message_id),
            "sender_id": str(msg.sender_id),
            "sender_name": f"{sender.first_name} {sender.last_name}" if sender else "Unknown",
            "subject": msg.subject,
            "message_text": msg.message_text[:100] + "..." if len(msg.message_text) > 100 else msg.message_text,
            "is_read": msg.is_read,
            "created_date": msg.created_date
        })
    
    return SuccessResponse(
        status="success",
        message="Inbox retrieved",
        data={
            "messages": messages_list,
            "total": total,
            "unread_count": len([m for m in messages if not m.is_read]),
            "skip": skip,
            "limit": limit
        }
    )

# ============================================================================
# GET /api/v1/messages/{message_id} - Get Message
# ============================================================================

@router.get("/{message_id}", response_model=SuccessResponse)
def get_message(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get full message details
    """
    message = db.query(Message).filter(Message.message_id == message_id).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Check access (recipient or sender)
    if message.recipient_id != current_user.user_id and message.sender_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Mark as read if recipient
    if message.recipient_id == current_user.user_id and not message.is_read:
        message.is_read = True
        message.read_date = datetime.utcnow()
        db.commit()
    
    # Get sender/recipient names
    sender = db.query(User).filter(User.user_id == message.sender_id).first()
    recipient = db.query(User).filter(User.user_id == message.recipient_id).first()
    
    return SuccessResponse(
        status="success",
        message="Message retrieved",
        data={
            "message_id": str(message.message_id),
            "sender_id": str(message.sender_id),
            "sender_name": f"{sender.first_name} {sender.last_name}" if sender else "Unknown",
            "recipient_id": str(message.recipient_id),
            "recipient_name": f"{recipient.first_name} {recipient.last_name}" if recipient else "Unknown",
            "subject": message.subject,
            "message_text": message.message_text,
            "message_type": message.message_type,
            "is_read": message.is_read,
            "read_date": message.read_date,
            "created_date": message.created_date
        }
    )

# ============================================================================
# PATCH /api/v1/messages/{message_id}/read - Mark as Read
# ============================================================================

@router.patch("/{message_id}/read", response_model=SuccessResponse)
def mark_as_read(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark message as read
    """
    message = db.query(Message).filter(Message.message_id == message_id).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Check access (recipient only)
    if message.recipient_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only recipient can mark as read"
        )
    
    message.is_read = True
    message.read_date = datetime.utcnow()
    db.commit()
    
    return SuccessResponse(
        status="success",
        message="Message marked as read",
        data={"message_id": str(message_id)}
    )

# ============================================================================
# GET /api/v1/messages/sent - Get Sent Messages
# ============================================================================

@router.get("/sent", response_model=SuccessResponse)
def get_sent_messages(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's sent messages
    """
    query = db.query(Message).filter(Message.sender_id == current_user.user_id)
    
    total = query.count()
    messages = query.order_by(Message.created_date.desc()).offset(skip).limit(limit).all()
    
    # Get recipient info
    messages_list = []
    for msg in messages:
        recipient = db.query(User).filter(User.user_id == msg.recipient_id).first()
        messages_list.append({
            "message_id": str(msg.message_id),
            "recipient_id": str(msg.recipient_id),
            "recipient_name": f"{recipient.first_name} {recipient.last_name}" if recipient else "Unknown",
            "subject": msg.subject,
            "message_text": msg.message_text[:100] + "..." if len(msg.message_text) > 100 else msg.message_text,
            "created_date": msg.created_date
        })
    
    return SuccessResponse(
        status="success",
        message="Sent messages retrieved",
        data={
            "messages": messages_list,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    )
