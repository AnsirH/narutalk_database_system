from . import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, BigInteger, Text
from sqlalchemy.orm import relationship

class ChatHistory(Base):
    """채팅 대화 기록을 관리하는 테이블"""
    __tablename__ = "chat_history"
    
    # 기본 식별 정보
    message_id = Column(BigInteger, primary_key=True, autoincrement=True)  # 메시지 고유 ID (자동 증가, 큰 정수)
    
    # 세션 정보
    session_id = Column(String(255), ForeignKey("chat_sessions.session_id"), nullable=False)  # 채팅 세션 ID (외래키, 필수)
    
    # 사용자 정보 (역사적 기록이므로 NULL 불가)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"), nullable=False)  # 채팅한 직원 ID (외래키, 필수)
    
    # 메시지 역할 및 내용
    role = Column(String(20), nullable=False)  # 메시지 역할 ('user' 또는 'assistant')
    message_text = Column(Text, nullable=False)  # 메시지 내용 (긴 텍스트)
        
    # TTL (Time To Live) 관련 필드
    expires_at = Column(DateTime)  # 자동 삭제 예정 일시 (예: 1년 후)
    
    # 시스템 정보
    created_at = Column(DateTime, nullable=False, default=func.now())  # 메시지 생성 일시 (필수, 자동 설정)
    
    # 관계 설정
    employee = relationship("Employee", backref="chat_messages")
    session = relationship("ChatSession", back_populates="messages")
    
    def __repr__(self):
        return f"<ChatHistory(message_id={self.message_id}, session_id='{self.session_id}', role='{self.role}')>" 
