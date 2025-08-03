"""
Text2SQL 기반 검색 서비스
자연어 쿼리를 SQL로 변환하여 데이터베이스에서 검색하는 기능을 제공합니다.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from sqlalchemy import text
from app.services.external.openai_service import openai_service
from app.services.utils.db import SessionLocal

logger = logging.getLogger(__name__)

class Text2SQLSearchService:
    """Text2SQL 기반 검색 서비스"""
    
    def __init__(self):
        """Text2SQL 검색 서비스 초기화"""
        pass
    
    def search_table_data(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """
        자연어 쿼리를 SQL로 변환하여 테이블 데이터 검색
        
        Args:
            query: 자연어 검색 쿼리
            limit: 결과 개수 제한
            
        Returns:
            Dict: 검색 결과
        """
        try:
            logger.info(f"Text2SQL 검색 시작: '{query}'")
            
            # 1. 자연어 쿼리를 SQL로 변환
            sql_result = self._convert_query_to_sql(query, limit)
            
            if not sql_result['success']:
                logger.error(f"SQL 변환 실패: {sql_result['message']}")
                return {
                    'success': False,
                    'message': f"SQL 변환 실패: {sql_result['message']}",
                    'results': []
                }
            
            # 2. SQL 실행
            execution_result = self._execute_search_sql(sql_result['sql'], limit)
            
            if not execution_result['success']:
                logger.error(f"SQL 실행 실패: {execution_result['message']}")
                return {
                    'success': False,
                    'message': f"SQL 실행 실패: {execution_result['message']}",
                    'results': []
                }
            
            # 3. 결과 포맷 변환
            formatted_results = []
            for record in execution_result['results']:
                formatted_results.append({
                    'type': 'table',
                    'id': record.get('sales_record_id') or record.get('id'),  # sales_record_id 우선, 없으면 id
                    'doc_id': record.get('doc_id'),
                    'table_type': sql_result['target_table'],
                    'content': record,
                    'created_at': record.get('created_at'),
                    'similarity_score': sql_result['confidence'],
                    'source': 'text2sql_search'
                })
            
            logger.info(f"Text2SQL 검색 완료: {len(formatted_results)}개 결과")
            
            return {
                'success': True,
                'message': f"Text2SQL 검색 완료: {len(formatted_results)}개 결과",
                'results': formatted_results,
                'sql': sql_result['sql'],
                'confidence': sql_result['confidence']
            }
            
        except Exception as e:
            logger.error(f"Text2SQL 검색 중 오류: {e}")
            return {
                'success': False,
                'message': f"Text2SQL 검색 중 오류: {str(e)}",
                'results': []
            }
    
    def _convert_query_to_sql(self, query: str, limit: int) -> Dict[str, Any]:
        """자연어 쿼리를 SQL로 변환"""
        try:
            # 데이터베이스 스키마 정보
            schema_info = self._get_database_schema_info()
            
            # LLM 프롬프트 생성
            prompt = self._create_sql_generation_prompt(query, schema_info, limit)
            
            # LLM 호출
            response = openai_service.create_chat_completion(
                messages=[
                    {"role": "system", "content": "당신은 자연어를 SQL로 변환하는 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                model="gpt-3.5-turbo",
                max_tokens=500,
                temperature=0.1
            )
            
            if not response:
                return {
                    'success': False,
                    'message': 'LLM 응답을 받지 못했습니다.'
                }
            
            # 응답 파싱
            try:
                # JSON 응답 파싱 시도
                response_data = json.loads(response.strip())
                
                return {
                    'success': True,
                    'sql': response_data.get('sql', ''),
                    'target_table': response_data.get('target_table', ''),
                    'confidence': response_data.get('confidence', 0.0),
                    'reasoning': response_data.get('reasoning', '')
                }
                
            except json.JSONDecodeError:
                # 일반 텍스트 응답 처리
                return {
                    'success': True,
                    'sql': response.strip(),
                    'target_table': 'sales_records',  # 기본값
                    'confidence': 0.7,
                    'reasoning': 'LLM 응답을 직접 SQL로 사용'
                }
                
        except Exception as e:
            logger.error(f"SQL 변환 중 오류: {e}")
            return {
                'success': False,
                'message': f"SQL 변환 중 오류: {str(e)}"
            }
    
    def _get_database_schema_info(self) -> str:
        """데이터베이스 스키마 정보 반환"""
        return """
        데이터베이스 스키마:
        
        1. sales_records (매출 기록)
           - sales_record_id (PK)
           - employee_id (FK)
           - customer_id (FK) 
           - product_id (FK)
           - sale_amount (매출액)
           - sale_date (매출일)
           - created_at (생성일)
           
        2. employee_info (직원 정보)
           - employee_info_id (PK)
           - name (이름)
           - employee_number (사번)
           - team (팀)
           - position (직급)
           
        3. customers (고객 정보)
           - customer_id (PK)
           - customer_name (고객명)
           - address (주소)
           - doctor_name (담당의사)
           
        4. products (제품 정보)
           - product_id (PK)
           - product_name (제품명)
           - description (설명)
           - category (카테고리)
        """
    
    def _create_sql_generation_prompt(self, query: str, schema_info: str, limit: int) -> str:
        """SQL 생성 프롬프트 생성"""
        return f"""
        다음 자연어 쿼리를 SQL로 변환해주세요.
        
        쿼리: "{query}"
        결과 개수 제한: {limit}
        
        {schema_info}
        
        요구사항:
        1. JOIN을 사용하여 관련 정보를 함께 조회
        2. ORDER BY를 사용하여 최신 데이터 우선
        3. LIMIT을 사용하여 결과 개수 제한
        4. 고객명, 직원명, 제품명이 쿼리에 포함된 경우 반드시 WHERE 조건에 추가
        5. 날짜 범위가 있는 경우 sale_date 조건 추가
        6. JSON 형식으로 응답:
        {{
            "sql": "실제 SQL 쿼리",
            "target_table": "주요 테이블명",
            "confidence": 0.0-1.0,
            "reasoning": "변환 이유"
        }}
        
        예시 쿼리:
        - "최수아 매출" → SELECT ... FROM sales_records AS sr JOIN employee_info AS ei ON sr.employee_id = ei.employee_info_id WHERE ei.name LIKE '%최수아%'
        - "폭세틴 판매" → SELECT ... FROM sales_records AS sr JOIN products AS p ON sr.product_id = p.product_id WHERE p.product_name LIKE '%폭세틴%'
        - "우리가족의원 2024년 2월부터 5월까지 매출" → SELECT ... FROM sales_records AS sr JOIN customers AS c ON sr.customer_id = c.customer_id WHERE c.customer_name LIKE '%우리가족의원%' AND sr.sale_date >= '2024-02-01' AND sr.sale_date <= '2024-05-31'
        
        중요: 
        - 고객명, 직원명, 제품명이 쿼리에 언급되면 반드시 WHERE 조건에 포함해야 함
        - LIKE 연산자를 사용하여 부분 일치 검색 수행
        - 날짜 범위와 고객명 조건을 모두 포함해야 함
        """
    
    def _execute_search_sql(self, sql: str, limit: int) -> Dict[str, Any]:
        """검색 SQL 실행"""
        try:
            session = SessionLocal()
            results = []
            
            try:
                logger.info(f"실행할 SQL: {sql}")
                
                # SQL 실행
                result = session.execute(text(sql))
                
                # 결과를 딕셔너리로 변환
                for row in result:
                    row_dict = {}
                    for key, value in row._mapping.items():
                        if hasattr(value, 'isoformat'):
                            row_dict[key] = value.isoformat()
                        else:
                            row_dict[key] = value
                    results.append(row_dict)
                
                logger.info(f"SQL 실행 결과: {len(results)}개 행 조회됨")
                if results:
                    logger.info(f"첫 번째 결과 샘플: {results[0]}")
                
                return {
                    'success': True,
                    'results': results,
                    'count': len(results)
                }
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"SQL 실행 중 오류: {e}")
            return {
                'success': False,
                'message': f"SQL 실행 중 오류: {str(e)}"
            }

# 싱글턴 인스턴스
text2sql_search_service = Text2SQLSearchService() 