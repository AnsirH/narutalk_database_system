from . import Base
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

class Employee(Base):
    """직원 정보를 관리하는 테이블"""
    __tablename__ = "employees"
    
    # 기본 식별 정보
    employee_id = Column(Integer, primary_key=True, autoincrement=True)  # 직원 고유 ID (자동 증가)
    email = Column(String, unique=True, nullable=False)  # 직원 이메일 주소 (고유값, 필수)
    username = Column(String, unique=True, nullable=False)  # 로그인용 사용자명 (고유값, 필수)
    password = Column(String, nullable=False)  # 로그인 비밀번호 (해시화된 값, 필수)
    name = Column(String, nullable=False)  # 직원 실명 (필수)
    
    # 조직 정보
    team = Column(String)  # 소속 팀명 (예: 영업팀, 마케팅팀)
    position = Column(String)  # 직급 (예: 대리, 과장, 차장)
    business_unit = Column(String)  # 사업부 (예: 제약사업부, 의료사업부)
    branch = Column(String)  # 지점/지사명
    
    # 연락처 및 업무 정보
    contact_number = Column(String)  # 연락처 전화번호
    responsibilities = Column(String)  # 담당 업무 영역 설명
    
    # 급여 및 예산 정보
    base_salary = Column(Integer)  # 기본급 (원 단위)
    incentive_pay = Column(Integer)  # 인센티브/성과급 (원 단위)
    avg_monthly_budget = Column(Integer)  # 월 평균 업무 예산 (원 단위)
    
    # 평가 및 상태 정보
    latest_evaluation = Column(String)  # 최근 평가 결과 (예: A, B, C 등급)
    role = Column(String, nullable=False)  # 시스템 내 역할 (예: admin, user, manager, 필수)
    is_active = Column(Boolean, default=True)  # 계정 활성화 상태 (기본값: 활성)
    
    # 시스템 정보
    created_at = Column(DateTime, default=func.now())  # 계정 생성 일시 (자동 설정)
    
    # 관계 설정 (선택적)
    employee_info = relationship("EmployeeInfo", back_populates="employee", uselist=False)
