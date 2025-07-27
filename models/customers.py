from . import Base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, func

class Customer(Base):
    """고객(의료기관) 정보를 관리하는 테이블"""
    __tablename__ = "customers"
    
    # 기본 식별 정보
    customer_id = Column(Integer, primary_key=True, autoincrement=True)  # 고객 고유 ID (자동 증가)
    customer_name = Column(String, nullable=False)  # 고객명/기관명 (필수)
    
    # 고객 분류 정보
    customer_type = Column(String)  # 고객 유형 (예: 대형병원, 중소병원, 의원, 약국)
    
    # 위치 정보
    address = Column(String)  # 고객 주소
    
    # 담당자 정보
    doctor_name = Column(String)  # 담당 의사명
    
    # 규모 정보
    total_patients = Column(Integer)  # 총 환자 수
    
    # 등급 및 평가 정보
    customer_grade = Column(String)  # 고객 등급 (예: A, B, C, VIP)
    
    # 기타 정보
    notes = Column(String)  # 고객 관련 특이사항 및 메모
    
    # Soft Delete 관련 필드
    is_deleted = Column(Boolean, default=False)  # 논리적 삭제 상태 (기본값: 삭제되지 않음)
    deleted_at = Column(DateTime)  # 논리적 삭제 일시
    
    # 시스템 정보
    created_at = Column(DateTime, default=func.now())  # 고객 등록 일시 (자동 설정) 
