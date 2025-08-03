from . import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, Boolean
from sqlalchemy.orm import relationship

class ChatSession(Base):
    """채팅 세션 정보를 관리하는 테이블"""
    __tablename__ = "chat_sessions"
    
    # 기본 식별 정보
    session_id = Column(String(255), primary_key=True)  # 세션 고유 ID (기본키)
    
    # 사용자 정보
    employee_id = Column(Integer, ForeignKey("employees.employee_id"), nullable=False)  # 세션 소유자 직원 ID (외래키, 필수)
    
    # 세션 정보 (선택적)
    session_title = Column(String(500))  # 세션 제목 (선택적)
    
    # 시간 정보
    created_at = Column(DateTime, nullable=False, default=func.now())  # 세션 생성 일시 (필수, 자동 설정)
    last_activity = Column(DateTime, nullable=False, default=func.now())  # 마지막 활동 일시 (필수, 자동 설정)
    
    # 아카이브 관련 필드
    is_archived = Column(Boolean, default=False)  # 아카이브 상태 (기본값: 활성)
    archived_at = Column(DateTime)  # 아카이브 일시
    
    # 관계 설정
    employee = relationship("Employee", backref="chat_sessions")
    messages = relationship("ChatHistory", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ChatSession(session_id='{self.session_id}', employee_id={self.employee_id})>" 