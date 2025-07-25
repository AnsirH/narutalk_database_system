from . import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, UniqueConstraint

class DocumentRelation(Base):
    """문서 간의 관계를 관리하는 테이블"""
    __tablename__ = "document_relations"
    
    # 기본 식별 정보
    relation_id = Column(Integer, primary_key=True, autoincrement=True)  # 관계 고유 ID (자동 증가)
    
    # 관계 정보
    source_doc_id = Column(Integer, ForeignKey("documents.doc_id"), nullable=False)  # 원본 문서 ID (외래키, 필수)
    related_doc_id = Column(Integer, ForeignKey("documents.doc_id"), nullable=False)  # 관련 문서 ID (외래키, 필수)
    relation_type = Column(String, nullable=False)  # 관계 유형 (예: 참조, 버전, 보완, 필수)
    
    # 제약 조건
    __table_args__ = (
        UniqueConstraint('source_doc_id', 'related_doc_id', name='uq_doc_relation_source_related'),  # 원본-관련 문서 조합 유니크 제약
    ) 
