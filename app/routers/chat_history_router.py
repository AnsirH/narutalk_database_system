"""
채팅 히스토리 관리 API
PostgreSQL을 통한 채팅 메시지 저장 및 조회
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import logging

from app.models.chat_history import ChatHistory
from app.models.chat_sessions import ChatSession
from app.services.utils.db import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat-history", tags=["Chat History"])

# 요청 모델
class SaveMessageRequest(BaseModel):
    session_id: str
    role: str  # "user" or "assistant"
    message_text: str
    employee_id: int

class GetHistoryRequest(BaseModel):
    session_id: str
    limit: Optional[int] = 50
    offset: Optional[int] = 0

class GetSessionInfoRequest(BaseModel):
    session_id: str

class UpdateSessionTitleRequest(BaseModel):
    session_id: str
    title: str

class ArchiveSessionRequest(BaseModel):
    session_id: str
    employee_id: int

class RestoreSessionRequest(BaseModel):
    session_id: str
    employee_id: int

# 응답 모델
class MessageResponse(BaseModel):
    message_id: str
    session_id: str
    timestamp: str
    role: str
    content: str

class SessionInfoResponse(BaseModel):
    session_id: str
    session_title: Optional[str]
    created_at: str
    last_activity: str
    message_count: int
    is_archived: bool
    archived_at: Optional[str]

@router.post("/save-message")
async def save_message(
    request: SaveMessageRequest,
    db: Session = Depends(get_db)
):
    """메시지 저장"""
    try:
        message_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # 세션이 없으면 생성
        session = db.query(ChatSession).filter(
            ChatSession.session_id == request.session_id
        ).first()
        
        if not session:
            session = ChatSession(
                session_id=request.session_id,
                employee_id=request.employee_id,
                created_at=timestamp,
                last_activity=timestamp,
                is_archived=False
            )
            db.add(session)
        
        # 메시지 저장
        message = ChatHistory(
            session_id=request.session_id,
            message_id=message_id,
            timestamp=timestamp,
            role=request.role,
            message_text=request.message_text,
            employee_id=request.employee_id
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
                "content": msg.message_text
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
                "session_title": session.session_title,
                "created_at": session.created_at,
                "last_activity": session.last_activity,
                "message_count": message_count,
                "is_archived": session.is_archived,
                "archived_at": session.archived_at
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{employee_id}")
async def get_user_sessions(
    employee_id: int,
    include_archived: bool = False,
    limit: Optional[int] = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """사용자의 세션 목록 조회"""
    try:
        query = db.query(ChatSession).filter(
            ChatSession.employee_id == employee_id
        )
        
        if not include_archived:
            query = query.filter(ChatSession.is_archived == False)
        
        query = query.order_by(ChatSession.last_activity.desc())
        
        # limit과 offset 적용
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        
        sessions = query.all()
        
        result = []
        for session in sessions:
            # 각 세션의 메시지 수 조회
            message_count = db.query(ChatHistory).filter(
                ChatHistory.session_id == session.session_id
            ).count()
            
            result.append({
                "session_id": session.session_id,
                "session_title": session.session_title,
                "created_at": session.created_at,
                "last_activity": session.last_activity,
                "message_count": message_count,
                "is_archived": session.is_archived,
                "archived_at": session.archived_at
            })
        
        # 전체 개수도 함께 반환
        total_count = db.query(ChatSession).filter(
            ChatSession.employee_id == employee_id
        )
        if not include_archived:
            total_count = total_count.filter(ChatSession.is_archived == False)
        total_count = total_count.count()
        
        return {
            "success": True,
            "sessions": result,
            "count": len(result),
            "total_count": total_count
        }
        
    except Exception as e:
        logger.error(f"Failed to get user sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/session/{session_id}/title")
async def update_session_title(
    session_id: str,
    request: UpdateSessionTitleRequest,
    db: Session = Depends(get_db)
):
    """세션 제목 수정"""
    try:
        session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session.session_title = request.title
        session.last_activity = datetime.now(timezone.utc)
        
        db.commit()
        
        logger.info(f"Session title updated: {session_id}")
        
        return {
            "success": True,
            "message": "Session title updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update session title: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/session/{session_id}/archive")
async def archive_session(
    session_id: str,
    request: ArchiveSessionRequest,
    db: Session = Depends(get_db)
):
    """세션 아카이브"""
    try:
        session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id,
            ChatSession.employee_id == request.employee_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.is_archived:
            raise HTTPException(status_code=400, detail="Session is already archived")
        
        session.is_archived = True
        session.archived_at = datetime.now(timezone.utc)
        
        db.commit()
        
        logger.info(f"Session archived: {session_id}")
        
        return {
            "success": True,
            "message": "Session archived successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to archive session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/session/{session_id}/restore")
async def restore_session(
    session_id: str,
    request: RestoreSessionRequest,
    db: Session = Depends(get_db)
):
    """아카이브된 세션 복원"""
    try:
        session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id,
            ChatSession.employee_id == request.employee_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if not session.is_archived:
            raise HTTPException(status_code=400, detail="Session is not archived")
        
        session.is_archived = False
        session.archived_at = None
        session.last_activity = datetime.now(timezone.utc)
        
        db.commit()
        
        logger.info(f"Session restored: {session_id}")
        
        return {
            "success": True,
            "message": "Session restored successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to restore session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    employee_id: int,
    db: Session = Depends(get_db)
):
    """세션 삭제 (메시지도 함께 삭제)"""
    try:
        session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id,
            ChatSession.employee_id == employee_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # 관련 메시지들 삭제
        db.query(ChatHistory).filter(
            ChatHistory.session_id == session_id
        ).delete()
        
        # 세션 삭제
        db.delete(session)
        db.commit()
        
        logger.info(f"Session deleted: {session_id}")
        
        return {
            "success": True,
            "message": "Session deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy", "service": "chat-history-api"} 