# Hybrid Search Router API 명세서

## 개요
하이브리드 검색 기능을 제공하는 API입니다. 테이블 데이터와 텍스트 문서를 통합하여 검색하며, 다양한 검색 방식을 지원합니다.

## 기본 정보
- **Base URL**: `/search`
- **Content-Type**: `application/json`
- **인증**: JWT 토큰 기반

## API 엔드포인트

### 1. 하이브리드 검색 (POST)
**POST** `/search/hybrid`

#### 헤더
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

#### 요청 본문
```json
{
  "query": "매출 현황",
  "limit": 20
}
```

#### 파라미터 설명
- **query**: 검색 쿼리 (문자열)
- **limit**: 결과 개수 제한 (기본값: 20)

#### 응답
```json
{
  "success": true,
  "message": "검색이 완료되었습니다.",
  "query": "매출 현황",
  "search_type": "hybrid",
  "analysis": {
    "query_type": "sales_inquiry",
    "confidence": 0.85
  },
  "table_results": [
    {
      "id": 1,
      "doc_id": 1,
      "table_type": "sales_data",
      "content": {
        "month": "2024-01",
        "sales": 1500000,
        "growth": "15%"
      },
      "created_at": "2024-01-01T12:00:00Z",
      "similarity_score": 0.95,
      "source": "text2sql_search"
    }
  ],
  "text_results": [
    {
      "id": "chunk_1",
      "doc_id": 2,
      "doc_title": "매출 보고서",
      "content": "2024년 1월 매출은 150만원으로...",
      "created_at": "2024-01-01T12:00:00Z",
      "similarity_score": 0.88,
      "source": "opensearch"
    }
  ],
  "total_count": 2,
  "search_time": 0.15
}
```

#### 사용 예시
```bash
curl -X POST "http://localhost:8010/search/hybrid" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "매출 현황",
    "limit": 20
  }'
```

---

### 2. 하이브리드 검색 (GET)
**GET** `/search/hybrid`

#### 헤더
```
Authorization: Bearer <access_token>
```

#### 쿼리 파라미터
- **query**: 검색 쿼리 (필수)
- **limit**: 결과 개수 제한 (선택, 기본값: 20)

#### 응답
```json
{
  "success": true,
  "message": "검색이 완료되었습니다.",
  "query": "매출 현황",
  "search_type": "hybrid",
  "analysis": {
    "query_type": "sales_inquiry",
    "confidence": 0.85
  },
  "table_results": [
    {
      "id": 1,
      "doc_id": 1,
      "table_type": "sales_data",
      "content": {
        "month": "2024-01",
        "sales": 1500000,
        "growth": "15%"
      },
      "created_at": "2024-01-01T12:00:00Z",
      "similarity_score": 0.95,
      "source": "text2sql_search"
    }
  ],
  "text_results": [
    {
      "id": "chunk_1",
      "doc_id": 2,
      "doc_title": "매출 보고서",
      "content": "2024년 1월 매출은 150만원으로...",
      "created_at": "2024-01-01T12:00:00Z",
      "similarity_score": 0.88,
      "source": "opensearch"
    }
  ],
  "total_count": 2,
  "search_time": 0.15
}
```

#### 사용 예시
```bash
curl -X GET "http://localhost:8010/search/hybrid?query=매출%20현황&limit=20" \
  -H "Authorization: Bearer <access_token>"
```

---

### 3. 하이브리드 검색 통계
**GET** `/search/hybrid/stats`

#### 헤더
```
Authorization: Bearer <access_token>
```

#### 응답
```json
{
  "total_searches": 150,
  "average_search_time": 0.12,
  "success_rate": 0.98,
  "popular_queries": [
    "매출 현황",
    "직원 정보",
    "고객 데이터"
  ],
  "search_types": {
    "table_only": 30,
    "text_only": 45,
    "hybrid": 75
  }
}
```

#### 사용 예시
```bash
curl -X GET "http://localhost:8010/search/hybrid/stats" \
  -H "Authorization: Bearer <access_token>"
```

---

## 검색 결과 타입

### 테이블 검색 결과 (TableSearchResult)
```json
{
  "id": 1,
  "doc_id": 1,
  "table_type": "sales_data",
  "content": {
    "month": "2024-01",
    "sales": 1500000,
    "growth": "15%"
  },
  "created_at": "2024-01-01T12:00:00Z",
  "similarity_score": 0.95,
  "source": "text2sql_search"
}
```

### 텍스트 검색 결과 (TextSearchResult)
```json
{
  "id": "chunk_1",
  "doc_id": 2,
  "doc_title": "매출 보고서",
  "content": "2024년 1월 매출은 150만원으로...",
  "created_at": "2024-01-01T12:00:00Z",
  "similarity_score": 0.88,
  "source": "opensearch"
}
```

---

## 검색 분석 기능

### 쿼리 분석
- **query_type**: 쿼리 유형 분류 (sales_inquiry, employee_info, etc.)
- **confidence**: 분석 신뢰도 (0.0-1.0)

### 검색 성능
- **search_time**: 검색 소요 시간 (초)
- **total_count**: 총 검색 결과 수
- **success_rate**: 검색 성공률

---

## 에러 응답

### 400 Bad Request
```json
{
  "detail": "검색 쿼리가 비어있습니다."
}
```

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 500 Internal Server Error
```json
{
  "detail": "검색 중 오류가 발생했습니다."
}
```

---

## 검색 최적화

### 쿼리 작성 팁
- **구체적인 키워드**: "매출 현황" > "매출"
- **관련 용어 포함**: "2024년 매출" > "매출"
- **정확한 표현**: "직원 수" > "사람"

### 성능 최적화
- **limit 파라미터**: 필요한 만큼만 설정
- **쿼리 길이**: 너무 긴 쿼리는 피하기
- **특수문자**: 검색에 필요한 특수문자만 사용

---

## 검색 통계 활용

### 인기 검색어 분석
```bash
# 인기 검색어 확인
curl -X GET "http://localhost:8010/search/hybrid/stats" \
  -H "Authorization: Bearer <access_token>"
```

### 성능 모니터링
- 평균 검색 시간 모니터링
- 성공률 추적
- 검색 유형별 통계

---

## 주의사항

1. **검색 범위**: 테이블과 텍스트 문서 모두 검색
2. **결과 정렬**: 유사도 점수 기준 내림차순
3. **캐싱**: 자주 사용되는 쿼리는 캐시됨
4. **실시간**: 최신 데이터 반영
5. **보안**: 인증된 사용자만 접근 가능 