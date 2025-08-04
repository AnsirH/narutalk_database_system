# QA Router API 명세서

## 개요
자연어 질문-답변 (QA) 기능을 제공하는 API입니다. 사용자의 자연어 질문을 받아 관련 문서를 검색하고 요약하여 답변을 생성합니다.

## 기본 정보
- **Base URL**: `/qa`
- **Content-Type**: `application/json`
- **인증**: JWT 토큰 기반

## API 엔드포인트

### 1. QA 시스템 상태 확인
**GET** `/qa/health`

#### 응답
```json
{
  "status": "healthy",
  "opensearch_connected": true,
  "embedding_model_available": true,
  "message": "QA 시스템이 정상 작동 중입니다."
}
```

#### 상태 코드
- **healthy**: 모든 시스템 정상
- **partial**: 일부 시스템에 문제
- **unhealthy**: 시스템에 문제

#### 사용 예시
```bash
curl -X GET "http://localhost:8010/qa/health"
```

---

### 2. 자연어 질문-답변
**POST** `/qa/question`

#### 헤더
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

#### 요청 본문
```json
{
  "question": "회사의 매출 현황은 어떻게 되나요?",
  "top_k": 5,
  "include_summary": true,
  "include_sources": true
}
```

#### 파라미터 설명
- **question**: 자연어 질문 (1-1000자)
- **top_k**: 검색할 문서 수 (1-20, 기본값: 5)
- **include_summary**: 요약 포함 여부 (기본값: true)
- **include_sources**: 원본 문서 정보 포함 여부 (기본값: true)

#### 응답
```json
{
  "success": true,
  "question": "회사의 매출 현황은 어떻게 되나요?",
  "answer": "회사의 매출은 지난해 대비 15% 증가했습니다. 주요 성장 요인은 신제품 출시와 해외 시장 확장입니다.",
  "summary": "매출 15% 증가, 신제품과 해외 확장이 주요 요인",
  "sources": [
    {
      "doc_id": 1,
      "doc_title": "2024년 매출 보고서",
      "content": "2024년 매출은 15% 증가...",
      "similarity_score": 0.95
    }
  ],
  "search_results": [
    {
      "id": "chunk_1",
      "content": "2024년 매출은 지난해 대비 15% 증가...",
      "similarity_score": 0.95
    }
  ],
  "total_sources": 1,
  "confidence_score": 0.92
}
```

#### 사용 예시
```bash
curl -X POST "http://localhost:8010/qa/question" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "회사의 매출 현황은 어떻게 되나요?",
    "top_k": 5,
    "include_summary": true,
    "include_sources": true
  }'
```

---

### 3. 테스트 질문-답변
**POST** `/qa/test`

#### 헤더
```
Authorization: Bearer <access_token>
```

#### 응답
```json
{
  "success": true,
  "question": "테스트 질문",
  "answer": "이것은 테스트 답변입니다.",
  "summary": "테스트 요약",
  "sources": [],
  "search_results": [],
  "total_sources": 0,
  "confidence_score": 1.0
}
```

#### 사용 예시
```bash
curl -X POST "http://localhost:8010/qa/test" \
  -H "Authorization: Bearer <access_token>"
```

---

## QA 시스템 구성 요소

### 1. OpenSearch 연결
- 문서 인덱싱 및 검색
- 벡터 유사도 검색
- 실시간 검색 결과 제공

### 2. 임베딩 모델
- 텍스트를 벡터로 변환
- 의미적 유사도 계산
- 다국어 지원

### 3. 문서 처리
- 텍스트 청킹
- 메타데이터 추출
- 관계 분석

---

## 에러 응답

### 400 Bad Request
```json
{
  "detail": "질문이 너무 짧습니다."
}
```

```json
{
  "detail": "질문이 너무 깁니다."
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
  "detail": "QA 시스템에 문제가 있습니다."
}
```

---

## 성능 최적화

### 검색 파라미터 조정
- **top_k**: 검색할 문서 수 (높을수록 정확도 향상, 속도 저하)
- **include_summary**: 요약 포함 여부 (처리 시간 단축)
- **include_sources**: 소스 정보 포함 여부 (메모리 사용량)

### 권장 설정
```json
{
  "top_k": 5,
  "include_summary": true,
  "include_sources": true
}
```

---

## 질문 작성 가이드

### 좋은 질문 예시
- "회사의 매출 현황은 어떻게 되나요?"
- "신제품 출시 계획은 언제인가요?"
- "직원 수는 몇 명인가요?"

### 피해야 할 질문
- 너무 짧은 질문: "매출?"
- 너무 긴 질문: 매우 긴 문장
- 모호한 질문: "그것은 어떻게 되나요?"

---

## 시스템 모니터링

### 상태 확인
```bash
# 시스템 상태 확인
curl -X GET "http://localhost:8010/qa/health"
```

### 로그 확인
```bash
# QA 시스템 로그 확인
docker logs fastapi-app | grep qa
```

---

## 주의사항

1. **질문 품질**: 명확하고 구체적인 질문 작성
2. **문서 업로드**: 질문과 관련된 문서가 먼저 업로드되어야 함
3. **시스템 상태**: 사용 전 `/qa/health`로 상태 확인
4. **응답 시간**: 복잡한 질문은 처리 시간이 오래 걸릴 수 있음
5. **정확도**: AI 기반 답변이므로 중요한 결정에는 추가 검증 필요 