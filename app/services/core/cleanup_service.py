"""
데이터베이스 정리 서비스
PostgreSQL, S3, OpenSearch 간의 데이터 무결성을 유지하는 서비스
"""

import logging
from typing import List, Set
from sqlalchemy.orm import Session
from app.services.external.s3_service import s3_client, BUCKET_NAME
from app.services.external.opensearch_service import opensearch_client
from app.models.documents import Document

logger = logging.getLogger(__name__)

class CleanupService:
    """데이터베이스 정리 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def cleanup_orphaned_s3_files(self) -> dict:
        """
        PostgreSQL에 없는 S3 파일들을 정리합니다.
        
        Returns:
            dict: 정리 결과 (삭제된 파일 수, 오류 등)
        """
        try:
            # PostgreSQL에서 모든 문서의 file_path 조회
            db_documents = self.db.query(Document.file_path).all()
            db_file_paths = {doc.file_path for doc in db_documents}
            
            # S3에서 모든 파일 조회
            s3_files = set()
            paginator = s3_client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=BUCKET_NAME):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        s3_files.add(obj['Key'])
            
            # PostgreSQL에 없는 S3 파일들 찾기
            orphaned_files = s3_files - db_file_paths
            
            # 고아 파일들 삭제
            deleted_count = 0
            errors = []
            
            for file_path in orphaned_files:
                try:
                    s3_client.delete_object(Bucket=BUCKET_NAME, Key=file_path)
                    deleted_count += 1
                    logger.info(f"S3에서 고아 파일 삭제: {file_path}")
                except Exception as e:
                    error_msg = f"S3 파일 삭제 실패 {file_path}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            return {
                "deleted_count": deleted_count,
                "errors": errors,
                "total_orphaned": len(orphaned_files)
            }
            
        except Exception as e:
            logger.error(f"S3 정리 중 오류 발생: {str(e)}")
            return {"error": str(e)}
    
    def cleanup_orphaned_opensearch_documents(self) -> dict:
        """
        PostgreSQL에 없는 OpenSearch 문서들을 정리합니다.
        
        Returns:
            dict: 정리 결과 (삭제된 문서 수, 오류 등)
        """
        try:
            # PostgreSQL에서 모든 문서의 doc_id 조회
            db_documents = self.db.query(Document.doc_id).all()
            db_doc_ids = {doc.doc_id for doc in db_documents}
            
            # OpenSearch에서 모든 문서 조회
            search_body = {
                "size": 10000,  # 충분히 큰 수
                "query": {"match_all": {}},
                "_source": ["doc_id"]
            }
            
            response = opensearch_client.search(
                index="documents",
                body=search_body
            )
            
            opensearch_doc_ids = set()
            for hit in response['hits']['hits']:
                doc_id = hit['_source'].get('doc_id')
                if doc_id:
                    opensearch_doc_ids.add(doc_id)
            
            # PostgreSQL에 없는 OpenSearch 문서들 찾기
            orphaned_docs = opensearch_doc_ids - db_doc_ids
            
            # 고아 문서들 삭제
            deleted_count = 0
            errors = []
            
            for doc_id in orphaned_docs:
                try:
                    # doc_id로 문서 검색하여 _id 찾기
                    search_response = opensearch_client.search(
                        index="documents",
                        body={
                            "query": {"term": {"doc_id": doc_id}},
                            "size": 1
                        }
                    )
                    
                    if search_response['hits']['hits']:
                        doc_id_in_opensearch = search_response['hits']['hits'][0]['_id']
                        opensearch_client.delete(
                            index="documents",
                            id=doc_id_in_opensearch
                        )
                        deleted_count += 1
                        logger.info(f"OpenSearch에서 고아 문서 삭제: doc_id={doc_id}")
                
                except Exception as e:
                    error_msg = f"OpenSearch 문서 삭제 실패 doc_id={doc_id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            return {
                "deleted_count": deleted_count,
                "errors": errors,
                "total_orphaned": len(orphaned_docs)
            }
            
        except Exception as e:
            logger.error(f"OpenSearch 정리 중 오류 발생: {str(e)}")
            return {"error": str(e)}
    
    def full_cleanup(self) -> dict:
        """
        전체 정리 작업을 수행합니다.
        
        Returns:
            dict: 전체 정리 결과
        """
        logger.info("전체 데이터베이스 정리 시작...")
        
        s3_result = self.cleanup_orphaned_s3_files()
        opensearch_result = self.cleanup_orphaned_opensearch_documents()
        
        total_deleted = (
            s3_result.get("deleted_count", 0) + 
            opensearch_result.get("deleted_count", 0)
        )
        
        all_errors = []
        if "errors" in s3_result:
            all_errors.extend(s3_result["errors"])
        if "errors" in opensearch_result:
            all_errors.extend(opensearch_result["errors"])
        
        result = {
            "s3_cleanup": s3_result,
            "opensearch_cleanup": opensearch_result,
            "total_deleted": total_deleted,
            "total_errors": len(all_errors),
            "errors": all_errors
        }
        
        logger.info(f"전체 정리 완료: {total_deleted}개 삭제, {len(all_errors)}개 오류")
        return result
    
    def get_cleanup_statistics(self) -> dict:
        """
        정리 전 통계 정보를 반환합니다.
        
        Returns:
            dict: 통계 정보
        """
        try:
            # PostgreSQL 문서 수
            db_count = self.db.query(Document).count()
            
            # S3 파일 수
            s3_count = 0
            paginator = s3_client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=BUCKET_NAME):
                if 'Contents' in page:
                    s3_count += len(page['Contents'])
            
            # OpenSearch 문서 수
            opensearch_count = 0
            try:
                response = opensearch_client.count(index="documents")
                opensearch_count = response['count']
            except Exception as e:
                logger.warning(f"OpenSearch 문서 수 조회 실패: {str(e)}")
            
            return {
                "postgresql_documents": db_count,
                "s3_files": s3_count,
                "opensearch_documents": opensearch_count
            }
            
        except Exception as e:
            logger.error(f"통계 조회 중 오류 발생: {str(e)}")
            return {"error": str(e)} 