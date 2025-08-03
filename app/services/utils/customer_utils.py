"""
공통 고객명/주소 추출 유틸리티
여러 서비스에서 공통으로 사용하는 고객명과 주소 추출 기능을 제공합니다.
"""

import re
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

def extract_name_and_address(raw_name: str) -> Tuple[str, Optional[str]]:
    """
    고객명에서 이름과 주소를 분리합니다.
    
    Args:
        raw_name: 원본 고객명 (예: '미라클신경과의원(강서구 화곡동)')
        
    Returns:
        (이름, 주소) 튜플
    """
    if not raw_name:
        return "", None
    
    # 괄호 안의 내용 추출 (주소일 가능성)
    match = re.match(r"(.+?)\((.+)\)", raw_name)
    if match:
        name = match.group(1).strip()
        address = match.group(2).strip()
        return name, address
    
    return raw_name.strip(), None

def extract_address_from_name(customer_name: str) -> Optional[str]:
    """
    고객명에서 주소 정보를 추출합니다.
    
    Args:
        customer_name: 고객명
        
    Returns:
        추출된 주소 또는 None
    """
    if not customer_name:
        return None
    
    # 괄호 안의 내용 추출 (주소일 가능성)
    bracket_match = re.search(r'[\(（]([^\)）]+)[\)）]', customer_name)
    if bracket_match:
        bracket_content = bracket_match.group(1).strip()
        # 주소 관련 키워드가 포함되어 있는지 확인
        address_keywords = ['시', '구', '동', '로', '길', '번지', '호', '층', '빌딩', '빌라', '아파트']
        if any(keyword in bracket_content for keyword in address_keywords):
            return bracket_content
    
    # 특정 패턴에서 주소 추출
    # 예: "OO병원 (서울시 강남구)" -> "서울시 강남구"
    address_patterns = [
        r'[\(（]([^\)）]*[시구동로길번지호층빌딩빌라아파트][^\)）]*)[\)）]',
        r'([가-힣]+시\s*[가-힣]+구\s*[가-힣]+동)',
        r'([가-힣]+시\s*[가-힣]+구)',
    ]
    
    for pattern in address_patterns:
        match = re.search(pattern, customer_name)
        if match:
            return match.group(1).strip()
    
    return None

def extract_address_and_clean_name(customer_name: str) -> Tuple[str, Optional[str]]:
    """
    고객명에서 주소를 추출하고 깔끔한 이름을 반환합니다.
    
    Args:
        customer_name: 고객명
        
    Returns:
        (깔끔한 이름, 주소) 튜플
    """
    if not customer_name:
        return "", None
    
    # 괄호 안의 내용 추출 (주소일 가능성)
    bracket_match = re.search(r'[\(（]([^\)）]+)[\)）]', customer_name)
    if bracket_match:
        bracket_content = bracket_match.group(1).strip()
        # 주소 관련 키워드가 포함되어 있는지 확인
        address_keywords = ['시', '구', '동', '로', '길', '번지', '호', '층', '빌딩', '빌라', '아파트']
        if any(keyword in bracket_content for keyword in address_keywords):
            # 주소 추출 및 이름에서 주소 부분 제거
            clean_name = re.sub(r'[\(（][^\)）]+[\)）]', '', customer_name).strip()
            return clean_name, bracket_content
    
    # 특정 패턴에서 주소 추출
    address_patterns = [
        r'[\(（]([^\)）]*[시구동로길번지호층빌딩빌라아파트][^\)）]*)[\)）]',
        r'([가-힣]+시\s*[가-힣]+구\s*[가-힣]+동)',
        r'([가-힣]+시\s*[가-힣]+구)',
    ]
    
    for pattern in address_patterns:
        match = re.search(pattern, customer_name)
        if match:
            address = match.group(1).strip()
            # 주소 부분을 제거한 깔끔한 이름
            clean_name = re.sub(pattern, '', customer_name).strip()
            return clean_name, address
    
    return customer_name, None  # 주소를 찾지 못한 경우 