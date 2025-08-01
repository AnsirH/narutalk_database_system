"""
OpenAI 기반 키워드 추출 서비스 (LangChain 기반)

사용자 질문에서 검색 키워드를 추출하는 LangChain OpenAI 기반 서비스입니다.
"""

import logging
import json
import re
from typing import List, Tuple, Union, Dict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings
from app.services.keyword_utils import extract_keywords_fallback, extract_keywords_with_scores

logger = logging.getLogger(__name__)

class OpenAIKeywordExtractor:
    """LangChain OpenAI 기반 키워드 추출 클래스"""
    
    def __init__(self):
        """초기화"""
        # LangChain OpenAI 클라이언트 초기화
        try:
            # 중앙화된 설정에서 OpenAI API 키 가져오기
            api_key = settings.get_openai_config().get("api_key")
            if api_key:
                self.llm = ChatOpenAI(
                    model="gpt-3.5-turbo", 
                    temperature=0,
                    api_key=api_key
                )
                logger.info("LangChain OpenAI 클라이언트 초기화 성공")
            else:
                logger.warning("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
                self.llm = None
        except Exception as e:
            logger.warning(f"LangChain OpenAI 클라이언트 초기화 실패: {e}")
            self.llm = None

        # 향상된 키워드 추출 프롬프트 템플릿
        self.keyword_prompt = {
            "prompts": {
                "keyword_extraction": """
                당신은 반드시 키워드를 추출하는 챗봇입니다.
                사용자의 질문에서 키워드를 반드시 추출하세요.

                "{user_question}"

                아래 조건을 만족해서 출력하세요.

                1. 키워드는 리스트 형태로 반드시 출력

                2. 문자열은 큰따옴표로 감싸서 출력하세요.

                3. 리스트외에는 아무것도 출력하지 마세요.

                4. 키워드는 최대 5개까지 추출하세요.

                5. 복합어는 분해해서 의미 있는 단어 단위로 나눠줘

                예를 들어 '임직원 교육기간'이라면 '임직원', '교육', '기간'처럼 나눠주세요.
                """
            }
        }

    def extract_keywords(self, text: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        LangChain OpenAI를 사용한 향상된 키워드 추출
        
        Args:
            text: 입력 텍스트 (질문)
            top_k: 추출할 키워드 수 (기본값: 5)
        
        Returns:
            (키워드, 점수) 튜플 리스트
        """
        if not self.llm:
            logger.warning("LangChain OpenAI 클라이언트가 초기화되지 않았습니다.")
            return []
        
        try:
            # LangChain 프롬프트 템플릿 사용
            keyword_template = self.keyword_prompt.get("prompts", {}).get("keyword_extraction", "")
            template = ChatPromptTemplate.from_template(keyword_template)
            messages = template.format_messages(user_question=text)
            
            # LangChain OpenAI 호출
            response = self.llm.invoke(messages)
            response_content = response.content.strip()
            
            # 응답에서 키워드 추출 (리스트 형태 파싱)
            keywords = self._parse_keyword_response(response_content)
            
            # 키워드 수 제한
            keywords = keywords[:top_k]
            
            # 점수 계산 (균등 분배)
            score_per_keyword = 1.0 / len(keywords) if keywords else 0
            keyword_scores = [(kw, score_per_keyword) for kw in keywords]
            
            logger.info(f"LangChain OpenAI 키워드 추출 완료: {keywords}")
            return keyword_scores
            
        except Exception as e:
            logger.error(f"LangChain OpenAI 키워드 추출 실패: {e}")
            # 실패 시 공통 fallback 방법 사용
            return extract_keywords_with_scores(text, top_k)

    def _parse_keyword_response(self, response_content: str) -> List[str]:
        """
        LangChain 응답에서 키워드 리스트를 파싱합니다.
        
        Args:
            response_content: LangChain 응답 내용
            
        Returns:
            키워드 리스트
        """
        try:
            # 큰따옴표로 감싸진 키워드들을 추출
            keywords = re.findall(r'"([^"]+)"', response_content)
            
            if keywords:
                return keywords
            
            # 큰따옴표가 없는 경우 쉼표로 구분된 형태로 파싱
            if ',' in response_content:
                keywords = [kw.strip() for kw in response_content.split(',') if kw.strip()]
                return keywords
            
            # 단일 키워드인 경우
            if response_content.strip():
                return [response_content.strip()]
            
            return []
            
        except Exception as e:
            logger.warning(f"키워드 응답 파싱 실패: {e}")
            return []



    def extract_keywords_simple(self, text: str, top_k: int = 5) -> List[str]:
        """
        키워드만 추출하는 간단한 메서드 (점수 제외)
        
        Args:
            text: 입력 텍스트
            top_k: 추출할 키워드 수
            
        Returns:
            키워드 리스트
        """
        keyword_scores = self.extract_keywords(text, top_k)
        return [kw for kw, score in keyword_scores]

    def extract_keywords_with_metadata(self, text: str, top_k: int = 5) -> Dict[str, Union[List[str], List[Tuple[str, float]], str]]:
        """
        메타데이터와 함께 키워드를 추출하는 메서드
        
        Args:
            text: 입력 텍스트
            top_k: 추출할 키워드 수
            
        Returns:
            키워드와 메타데이터를 포함한 딕셔너리
        """
        try:
            keyword_scores = self.extract_keywords(text, top_k)
            keywords_only = [kw for kw, score in keyword_scores]
            
            return {
                "success": True,
                "original_text": text,
                "keywords": keywords_only,
                "keyword_scores": keyword_scores,
                "total_keywords": len(keywords_only),
                "extraction_method": "langchain_openai",
                "metadata": {
                    "model": "gpt-3.5-turbo",
                    "temperature": 0,
                    "max_keywords": top_k
                }
            }
            
        except Exception as e:
            logger.error(f"키워드 메타데이터 추출 실패: {e}")
            return {
                "success": False,
                "original_text": text,
                "keywords": [],
                "keyword_scores": [],
                "total_keywords": 0,
                "extraction_method": "fallback",
                "error": str(e)
            }


# 전역 인스턴스 생성
keyword_extractor = OpenAIKeywordExtractor() 