"""
공통 키워드 추출 유틸리티
여러 서비스에서 공통으로 사용하는 키워드 추출 기능을 제공합니다.
"""

import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

# 한국어 불용어 목록
KOREAN_STOP_WORDS = {
    '이', '가', '을', '를', '의', '에', '에서', '로', '으로', '와', '과', '도', '는', '은', '이', '가',
    '어떻게', '무엇', '언제', '어디', '왜', '어떤', '몇', '얼마', '어떠한', '무슨', '어느', '어떤',
    '있나요', '있습니까', '입니까', '인가요', '인지', '인지요', '인가', '인지', '인지요',
    '알려주세요', '알려주시기', '알려주시면', '알려주시겠습니까', '알려주시겠어요',
    '해주세요', '해주시기', '해주시면', '해주시겠습니까', '해주시겠어요',
    '좋겠습니까', '좋겠어요', '좋을까요', '좋을지', '좋을지요',
    '있을까요', '있을지', '있을지요', '될까요', '될지', '될지요'
}

def extract_keywords_fallback(text: str, top_k: int = 10) -> List[str]:
    """
    기본 키워드 추출 방법 (fallback)
    
    Args:
        text: 입력 텍스트
        top_k: 추출할 키워드 수
        
    Returns:
        키워드 리스트
    """
    try:
        # 특수문자 제거 및 소문자 변환
        cleaned_text = re.sub(r'[^\w\s가-힣]', ' ', text.lower())
        
        # 단어 분리
        words = cleaned_text.split()
        
        # 불용어 제거 및 2글자 이상 단어만 유지
        keywords = [word for word in words if word not in KOREAN_STOP_WORDS and len(word) >= 2]
        
        # 중복 제거
        keywords = list(set(keywords))
        
        # 최대 top_k개 키워드로 제한
        return keywords[:top_k]
        
    except Exception as e:
        logger.error(f"Fallback 키워드 추출 실패: {e}")
        return []

def extract_keywords_with_scores(text: str, top_k: int = 10) -> List[Tuple[str, float]]:
    """
    키워드와 점수를 함께 추출하는 기본 방법
    
    Args:
        text: 입력 텍스트
        top_k: 추출할 키워드 수
        
    Returns:
        (키워드, 점수) 튜플 리스트
    """
    keywords = extract_keywords_fallback(text, top_k)
    
    # 점수 계산 (균등 분배)
    score_per_keyword = 1.0 / len(keywords) if keywords else 0
    keyword_scores = [(kw, score_per_keyword) for kw in keywords]
    
    return keyword_scores 