from . import Base
from sqlalchemy import Column, Integer, String, Date, ForeignKey, Numeric

class SalesRecord(Base):
    """매출 기록을 관리하는 테이블"""
    __tablename__ = "sales_records"
    
    # 기본 식별 정보
    record_id = Column(Integer, primary_key=True, autoincrement=True)  # 매출 기록 고유 ID (자동 증가)
    
    # 관계 정보
    employee_id = Column(Integer, ForeignKey("employees.employee_id"), nullable=False)  # 매출 담당 직원 ID (외래키, 필수)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"), nullable=False)  # 매출 발생 고객 ID (외래키, 필수)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)  # 판매된 제품 ID (외래키, 필수)
    
    # 매출 정보
    sale_amount = Column(Numeric(15, 2), nullable=False)  # 매출 금액 (소수점 2자리까지, 필수)
    sale_date = Column(Date, nullable=False)  # 매출 발생 날짜 (필수) 
