from app.services.opensearch_client import opensearch_client
import re
import logging
from typing import List, Dict, Any, Optional

DOCUMENT_INDEX_NAME = "document_chunks"
SEARCH_PIPELINE_ID = "hybrid-minmax-pipeline"

# 로깅 설정
logger = logging.getLogger(__name__)

# 고급 키워드 추출 서비스 import
from app.services.keyword_extractor import keyword_extractor
from app.services.keyword_utils import extract_keywords_fallback

# Search Pipeline 초기화 함수
def initialize_search_pipeline():
    """Search Pipeline을 초기화합니다."""
    try:
        # Search Pipeline 생성
        pipeline_created = opensearch_client.create_search_pipeline(SEARCH_PIPELINE_ID)
        if pipeline_created:
            logger.info(f"✅ Search Pipeline '{SEARCH_PIPELINE_ID}' 초기화 완료")
        else:
            logger.warning(f"⚠️ Search Pipeline '{SEARCH_PIPELINE_ID}' 초기화 실패")
        return pipeline_created
    except Exception as e:
        logger.error(f"❌ Search Pipeline 초기화 중 오류: {e}")
        return False

# 자연어 질문에서 키워드 추출 함수 (OpenAI 기반)
def extract_keywords_from_question(question: str, top_k: int = 10) -> List[str]:
    """
    자연어 질문에서 검색 키워드를 추출합니다.
    
    Args:
        question: 질문 텍스트
        top_k: 추출할 키워드 수
    
    Returns:
        키워드 리스트
    """
    try:
        # OpenAI를 사용한 키워드 추출
        keywords = keyword_extractor.extract_keywords(question, top_k)
        
        # 키워드만 추출 (점수 제외)
        return [kw for kw, score in keywords]
        
    except Exception as e:
        logger.error(f"키워드 추출 실패: {e}")
        # 실패 시 기본 방법 사용
        return extract_keywords_fallback(question, top_k)



# 문서 내용 요약 함수
def summarize_documents(documents: List[Dict[str, Any]], question: str) -> str:
    """검색된 문서들을 요약하여 답변을 생성합니다."""
    if not documents:
        return "죄송합니다. 질문과 관련된 문서를 찾을 수 없습니다."
    
    # 문서 내용들을 결합
    combined_content = ""
    for i, doc in enumerate(documents[:3], 1):  # 상위 3개 문서만 사용
        # 수정: source 안의 content에 접근
        source = doc.get("source", {})
        content = source.get("content", "")
        if content:
            combined_content += f"문서 {i}: {content}\n\n"
    
    if not combined_content.strip():
        return "죄송합니다. 문서 내용을 추출할 수 없습니다."
    
    # 간단한 요약 로직 (실제로는 더 정교한 요약 모델 사용 권장)
    sentences = re.split(r'[.!?]', combined_content)
    relevant_sentences = []
    
    # 질문 키워드가 포함된 문장들을 우선 선택
    question_keywords = extract_keywords_from_question(question)
    
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) > 10:  # 너무 짧은 문장 제외
            # 키워드가 포함된 문장 우선 선택
            if any(keyword in sentence for keyword in question_keywords):
                relevant_sentences.append(sentence)
    
    # 키워드가 포함된 문장이 부족하면 전체에서 선택
    if len(relevant_sentences) < 2:
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20 and sentence not in relevant_sentences:
                relevant_sentences.append(sentence)
                if len(relevant_sentences) >= 5:  # 최대 5개 문장
                    break
    
    # 요약 생성
    if relevant_sentences:
        summary = " ".join(relevant_sentences[:3])  # 상위 3개 문장만 사용
        if len(summary) > 500:  # 너무 길면 자르기
            summary = summary[:500] + "..."
        return summary
    else:
        return "관련 문서를 찾았지만, 질문에 대한 구체적인 답변을 추출하기 어렵습니다."

# 신뢰도 점수 계산 함수
def calculate_confidence_score(search_results: List[Dict[str, Any]]) -> float:
    """검색 결과의 신뢰도 점수를 계산합니다."""
    if not search_results:
        return 0.0
    
    # 검색 점수의 평균을 신뢰도로 사용
    scores = [result.get("score", 0.0) for result in search_results]
    avg_score = sum(scores) / len(scores)
    
    # 점수를 0-1 범위로 정규화 (일반적으로 검색 점수는 0-10 범위)
    normalized_score = min(avg_score / 10.0, 1.0)
    
    return round(normalized_score, 2)

# 자연어 질문-답변 함수
def question_answering(question: str, top_k: int = 5, include_sources: bool = True) -> Dict[str, Any]:
    """
    질문에 대한 답변을 생성합니다.
    
    Args:
        question: 사용자 질문
        top_k: 검색할 문서 수
        include_sources: 소스 정보 포함 여부
        
    Returns:
        답변과 소스 정보를 포함한 딕셔너리
    """
    try:
        # 1. 키워드 추출
        keywords = extract_keywords_from_question(question, top_k=10)
        
        # 2. OpenSearch에서 검색
        search_results = opensearch_client.search_with_pipeline(
            query_text=question,
            keywords=keywords,
            pipeline_id=SEARCH_PIPELINE_ID,
            index_name=DOCUMENT_INDEX_NAME,
            top_k=top_k,
            use_rerank=True,
            rerank_top_k=3
        )
        
        # 3. 검색 결과가 없으면 기본 검색 시도
        if not search_results:
            logger.warning("파이프라인 검색 결과가 없어 기본 검색을 시도합니다.")
            search_results = opensearch_client.search_document(
                index_name=DOCUMENT_INDEX_NAME,
                query={
                    "query": {
                        "multi_match": {
                            "query": question,
                            "fields": ["content", "doc_title"],
                            "type": "best_fields",
                            "fuzziness": "AUTO"
                        }
                    },
                    "size": top_k
                }
            )
        
        # 4. 답변 생성
        if search_results:
            answer = summarize_documents(search_results, question)
        else:
            answer = "죄송합니다. 질문과 관련된 문서를 찾을 수 없습니다."
        
        # 5. 소스 정보 생성
        sources = []
        if include_sources and search_results:
            for i, result in enumerate(search_results[:3], 1):
                source = result.get("source", {})
                source_info = {
                    "rank": i,
                    "doc_id": source.get("doc_id"),
                    "doc_title": source.get("doc_title"),
                    "file_name": source.get("file_name"),
                    "content_preview": source.get("content", "")[:200] + "..." if len(source.get("content", "")) > 200 else source.get("content", ""),
                    "score": result.get("score", 0.0)
                }
                sources.append(source_info)
        
        # 6. 신뢰도 점수 계산
        confidence_score = calculate_confidence_score(search_results)
        
        # 7. 요약 생성 (선택적)
        summary = None
        if len(search_results) > 1:
            summary = f"총 {len(search_results)}개의 관련 문서를 찾았습니다. 주요 내용은 다음과 같습니다: {answer[:300]}..."
        
        logger.info(f"QA 처리 완료: {len(search_results)}개 문서에서 정보를 찾았습니다.")
        
        return {
            "success": True,
            "question": question,
            "answer": answer,
            "summary": summary,
            "sources": sources,
            "search_results": search_results,
            "total_sources": len(search_results),
            "confidence_score": confidence_score
        }
        
    except Exception as e:
        logger.error(f"QA 처리 오류: {e}")
        return {
            "success": False,
            "question": question,
            "answer": f"질문 처리 중 오류가 발생했습니다: {str(e)}",
            "summary": None,
            "sources": [],
            "search_results": [],
            "total_sources": 0,
            "confidence_score": 0.0
        }

# 문서 청킹 인덱싱 함수 (추가 기능 포함)
def index_document_chunks(doc_id, doc_title, file_name, text, document_type="report"):
    """문서 청킹을 OpenSearch에 인덱싱합니다."""
    try:
        # OpenSearch에 문서 청킹 저장
        success = opensearch_client.index_document_chunks(
            index_name=DOCUMENT_INDEX_NAME,
            doc_id=doc_id,
            doc_title=doc_title,
            file_name=file_name,
            text=text,
            document_type=document_type
        )
        
        if success:
            logger.info(f"문서 {doc_id}의 청킹을 OpenSearch에 저장했습니다. (문서 타입: {document_type})")
        else:
            logger.error(f"문서 {doc_id}의 청킹 인덱싱에 실패했습니다.")
        
        return success
        
    except Exception as e:
        logger.error(f"문서 청킹 인덱싱 실패: {e}")
        return False

def delete_document_chunks_from_opensearch(index_name, document_id):
    """OpenSearch에서 특정 문서의 청킹을 삭제합니다."""
    try:
        # OpenSearch에서 문서 청킹 삭제
        success = opensearch_client.delete_document_chunks(
            index_name=index_name,
            document_id=document_id
        )
        
        if success:
            logger.info(f"문서 {document_id}의 청킹을 OpenSearch에서 삭제했습니다.")
        else:
            logger.error(f"문서 {document_id}의 청킹 삭제에 실패했습니다.")
        
        return success
        
    except Exception as e:
        logger.error(f"문서 청킹 삭제 실패: {e}")
        return False 