import logging
from typing import Dict, Any, List, Optional
from app.services.opensearch_client import opensearch_client
from app.services.query_analyzer import query_analyzer
from app.services.text2sql_search import text2sql_search_service
import time

logger = logging.getLogger(__name__)

class HybridSearchService:
    """하이브리드 검색 서비스 (벡터 검색 + OpenSearch)"""
    
    def __init__(self):
        """하이브리드 검색 서비스 초기화"""
        pass
    
    def search(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """
        하이브리드 검색 수행
        
        Args:
            query: 검색 질의
            limit: 결과 개수 제한
            
        Returns:
            Dict: 검색 결과
        """
        start_time = time.time()
        
        try:
            # 1. 질의 분석
            analysis_result = query_analyzer.analyze_query(query)
            
            if not analysis_result['success']:
                logger.error(f"질의 분석 실패: {analysis_result.get('error')}")
                return self._create_error_response("질의 분석 중 오류가 발생했습니다.")
            
            analysis = analysis_result['analysis']
            search_type = analysis['search_type']
            
            logger.info(f"검색 유형: {search_type}, 신뢰도: {analysis['confidence']}")
            
            # 2. 검색 유형에 따른 검색 수행
            if search_type == 'table':
                results = self._search_table_data(query, analysis, limit)
            elif search_type == 'text':
                results = self._search_text_documents(query, analysis, limit)
            else:  # hybrid
                results = self._search_hybrid(query, analysis, limit)
            
            # 3. 결과 정렬 (정확도 우선)
            results = self._sort_by_accuracy(results)
            
            # 4. 응답 생성
            search_time = time.time() - start_time
            
            return {
                'success': True,
                'query': query,
                'search_type': search_type,
                'analysis': analysis,
                'results': results,
                'total_count': len(results),
                'search_time': round(search_time, 3),
                'message': f'검색 완료: {len(results)}개 결과 ({search_time:.3f}초)'
            }
            
        except Exception as e:
            logger.error(f"하이브리드 검색 중 오류: {e}")
            return self._create_error_response(f"검색 중 오류가 발생했습니다: {str(e)}")
    
    def _search_table_data(self, query: str, analysis: Dict, limit: int) -> List[Dict]:
        """테이블 데이터 검색 (Text2SQL 기반)"""
        try:
            logger.info(f"Text2SQL 기반 테이블 데이터 검색: '{query}'")
            
            # Text2SQL 분류기를 사용한 검색
            search_result = text2sql_search_service.search_table_data(query, limit)
            
            if not search_result['success']:
                logger.error(f"Text2SQL 검색 실패: {search_result['message']}")
                return []
            
            logger.info(f"Text2SQL 검색 완료: {len(search_result['results'])}개 결과")
            return search_result['results']
            
        except Exception as e:
            logger.error(f"테이블 데이터 검색 중 오류: {e}")
            return []
    
    def _search_text_documents(self, query: str, analysis: Dict, limit: int) -> List[Dict]:
        """텍스트 문서 검색"""
        try:
            # OpenSearch 검색 수행
            from app.services.opensearch_service import DOCUMENT_INDEX_NAME
            text_results = opensearch_client.search_document(DOCUMENT_INDEX_NAME, {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["content", "doc_title"],
                        "type": "best_fields"
                    }
                },
                "size": limit
            })
            
            logger.info(f"OpenSearch 검색 결과: {len(text_results)}개")
            if text_results:
                logger.info(f"첫 번째 OpenSearch 결과 구조: {text_results[0]}")
            
            # 결과 포맷 변환
            formatted_results = []
            for result in text_results:
                # OpenSearch 결과 구조 안전 처리
                # _source 또는 source 필드에서 데이터 추출
                source = result.get('_source') or result.get('source', {})
                
                formatted_result = {
                    'type': 'text',
                    'id': result.get('_id'),
                    'doc_id': source.get('document_id') or source.get('doc_id'),
                    'doc_title': source.get('title') or source.get('doc_title') or source.get('file_name'),
                    'content': source.get('content'),
                    'created_at': source.get('created_at'),
                    'similarity_score': result.get('_score') or result.get('score', 0.0),
                    'source': 'opensearch'
                }
                
                # null 값 처리
                if formatted_result['content'] is None:
                    # content가 없으면 다른 필드에서 텍스트 찾기
                    formatted_result['content'] = source.get('text') or source.get('body') or source.get('document_content') or "내용 없음"
                
                if formatted_result['doc_title'] is None:
                    # doc_title이 없으면 다른 필드에서 제목 찾기
                    formatted_result['doc_title'] = source.get('name') or "제목 없음"
                
                formatted_results.append(formatted_result)
            
            logger.info(f"텍스트 검색 완료: {len(formatted_results)}개 결과")
            if formatted_results:
                logger.info(f"첫 번째 포맷된 결과: {formatted_results[0]}")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"텍스트 문서 검색 중 오류: {e}")
            return []
    
    def _search_hybrid(self, query: str, analysis: Dict, limit: int) -> List[Dict]:
        """하이브리드 검색 (테이블 + 텍스트)"""
        try:
            # 테이블 데이터 검색
            table_results = self._search_table_data(query, analysis, limit // 2)
            
            # 텍스트 문서 검색
            text_results = self._search_text_documents(query, analysis, limit // 2)
            
            # 결과 병합
            combined_results = table_results + text_results
            
            logger.info(f"하이브리드 검색 완료: 테이블 {len(table_results)}개, 텍스트 {len(text_results)}개")
            return combined_results
            
        except Exception as e:
            logger.error(f"하이브리드 검색 중 오류: {e}")
            return []
    
    def _sort_by_accuracy(self, results: List[Dict]) -> List[Dict]:
        """정확도 기준으로 결과 정렬"""
        try:
            # similarity_score 기준으로 내림차순 정렬
            sorted_results = sorted(
                results,
                key=lambda x: x.get('similarity_score', 0.0),
                reverse=True
            )
            
            return sorted_results
            
        except Exception as e:
            logger.error(f"결과 정렬 중 오류: {e}")
            return results
    
    def _create_error_response(self, message: str) -> Dict[str, Any]:
        """에러 응답 생성"""
        return {
            'success': False,
            'message': message,
            'results': [],
            'total_count': 0,
            'search_time': 0.0
        }

# 전역 인스턴스
hybrid_search_service = HybridSearchService() 