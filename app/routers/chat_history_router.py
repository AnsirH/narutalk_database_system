"""
채팅 히스토리 관리 API
PostgreSQL을 통한 채팅 메시지 저장 및 조회
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime
import uuid
import json
import logging

from app.models.chat_history import ChatHistory
from app.models.chat_sessions import ChatSession
from app.services.db import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat-history", tags=["Chat History"])

# 요청 모델
class SaveMessageRequest(BaseModel):
    session_id: str
    role: str  # "user" or "assistant"
    message_text: str
    employee_id: int
    metadata: Optional[Dict] = None

class GetHistoryRequest(BaseModel):
    session_id: str
    limit: Optional[int] = 50
    offset: Optional[int] = 0

class GetSessionInfoRequest(BaseModel):
    session_id: str

# 응답 모델
class MessageResponse(BaseModel):
    message_id: str
    session_id: str
    timestamp: str
    role: str
    content: str
    metadata: Dict

class SessionInfoResponse(BaseModel):
    session_id: str
    created_at: str
    last_activity: str
    message_count: int

@router.post("/save-message")
async def save_message(
    request: SaveMessageRequest,
    db: Session = Depends(get_db)
):
    """메시지 저장"""
    try:
        message_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        # 세션이 없으면 생성
        session = db.query(ChatSession).filter(
            ChatSession.session_id == request.session_id
        ).first()
        
        if not session:
            session = ChatSession(
                session_id=request.session_id,
                created_at=timestamp,
                last_activity=timestamp,
                metadata=json.dumps({})
            )
            db.add(session)
        
        # 메시지 저장
        message = ChatHistory(
            session_id=request.session_id,
            message_id=message_id,
            timestamp=timestamp,
            role=request.role,
            message_text=request.message_text,
            employee_id=request.employee_id,
            metadata=json.dumps(request.metadata or {}, ensure_ascii=False)
        )
        
        db.add(message)
        
        # 세션 last_activity 업데이트
        session.last_activity = timestamp
        
        db.commit()
        
        logger.info(f"Message saved: {message_id}")
        
        return {
            "success": True,
            "message_id": message_id,
            "timestamp": timestamp
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/get-history")
async def get_conversation_history(
    request: GetHistoryRequest,
    db: Session = Depends(get_db)
):
    """대화 기록 조회"""
    try:
        query = db.query(ChatHistory).filter(
            ChatHistory.session_id == request.session_id
        ).order_by(ChatHistory.timestamp.asc())
        
        if request.limit:
            query = query.limit(request.limit)
        if request.offset:
            query = query.offset(request.offset)
        
        messages = query.all()
        
        result = []
        for msg in messages:
            result.append({
                "message_id": msg.message_id,
                "timestamp": msg.timestamp,
                "role": msg.role,
                "content": msg.message_text,
                "metadata": json.loads(msg.metadata or "{}")
            })
        
        return {
            "success": True,
            "messages": result,
            "count": len(result)
        }
        
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/get-session-info")
async def get_session_info(
    request: GetSessionInfoRequest,
    db: Session = Depends(get_db)
):
    """세션 정보 조회"""
    try:
        session = db.query(ChatSession).filter(
            ChatSession.session_id == request.session_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # 메시지 수 조회
        message_count = db.query(ChatHistory).filter(
            ChatHistory.session_id == request.session_id
        ).count()
        
        return {
            "success": True,
            "session": {
                "session_id": session.session_id,
                "created_at": session.created_at,
                "last_activity": session.last_activity,
                "message_count": message_count
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy", "service": "chat-history-api"} 