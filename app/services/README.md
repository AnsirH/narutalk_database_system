# Services 폴더 구조 개선 제안

## 현재 문제점
- 주요 기능과 유틸리티가 한 폴더에 섞여있음
- 코드 찾기가 어려움
- 유지보수성 저하

## 개선된 구조

```
app/services/
├── core/                    # 핵심 비즈니스 로직
│   ├── __init__.py
│   ├── hybrid_search_service.py
│   ├── text2sql_search.py
│   ├── text2sql_classifier.py
│   ├── document_analyzer.py
│   └── document_relation_analyzer.py
│
├── external/                # 외부 서비스 연동
│   ├── __init__.py
│   ├── openai_service.py
│   ├── opensearch_service.py
│   ├── opensearch_client.py
│   ├── postgres_service.py
│   └── s3_service.py
│
├── processors/              # 데이터 처리기
│   ├── __init__.py
│   ├── customer_info_processor.py
│   ├── hr_data_processor.py
│   ├── keyword_extractor.py
│   ├── query_analyzer.py
│   └── user_service.py
│
└── utils/                   # 유틸리티
    ├── __init__.py
    ├── customer_utils.py
    ├── keyword_utils.py
    └── db.py
```

## 장점
1. **명확한 분리**: 기능별로 명확히 구분
2. **쉬운 탐색**: 원하는 기능을 빠르게 찾을 수 있음
3. **유지보수성**: 관련 코드들이 함께 위치
4. **확장성**: 새로운 기능 추가 시 적절한 위치에 배치 가능

## 마이그레이션 계획

### 1단계: 새 폴더 구조 생성
```bash
mkdir app/services/core
mkdir app/services/external
mkdir app/services/processors
mkdir app/services/utils
```

### 2단계: 파일 이동
```bash
# core/ 폴더로 이동
mv app/services/hybrid_search_service.py app/services/core/
mv app/services/text2sql_search.py app/services/core/
mv app/services/text2sql_classifier.py app/services/core/
mv app/services/document_analyzer.py app/services/core/
mv app/services/document_relation_analyzer.py app/services/core/

# external/ 폴더로 이동
mv app/services/openai_service.py app/services/external/
mv app/services/opensearch_service.py app/services/external/
mv app/services/opensearch_client.py app/services/external/
mv app/services/postgres_service.py app/services/external/
mv app/services/s3_service.py app/services/external/

# processors/ 폴더로 이동
mv app/services/customer_info_processor.py app/services/processors/
mv app/services/hr_data_processor.py app/services/processors/
mv app/services/keyword_extractor.py app/services/processors/
mv app/services/query_analyzer.py app/services/processors/
mv app/services/user_service.py app/services/processors/

# utils/ 폴더로 이동
mv app/services/customer_utils.py app/services/utils/
mv app/services/keyword_utils.py app/services/utils/
mv app/services/db.py app/services/utils/
```

### 3단계: __init__.py 파일 생성
각 폴더에 `__init__.py` 파일을 생성하여 패키지로 만들기

### 4단계: Import 경로 수정

#### 4-1. services 내부 import 수정

**core/ 폴더의 파일들:**
- `text2sql_search.py`: 
  - `from app.services.openai_service` → `from app.services.external.openai_service`
  - `from app.services.db` → `from app.services.utils.db`

- `text2sql_classifier.py`:
  - `from app.services.openai_service` → `from app.services.external.openai_service`
  - `from app.services.customer_utils` → `from app.services.utils.customer_utils`
  - `from app.services.db` → `from app.services.utils.db`

- `document_relation_analyzer.py`:
  - `from app.services.openai_service` → `from app.services.external.openai_service`
  - `from app.services.db` → `from app.services.utils.db`

**external/ 폴더의 파일들:**
- `opensearch_service.py`:
  - `from app.services.opensearch_client` → `from app.services.external.opensearch_client`
  - `from app.services.keyword_extractor` → `from app.services.processors.keyword_extractor`
  - `from app.services.keyword_utils` → `from app.services.utils.keyword_utils`

- `postgres_service.py`:
  - `from app.services.db` → `from app.services.utils.db`

**processors/ 폴더의 파일들:**
- `keyword_extractor.py`:
  - `from app.services.keyword_utils` → `from app.services.utils.keyword_utils`

- `customer_info_processor.py`:
  - `from app.services.db` → `from app.services.utils.db`
  - `from app.services.customer_utils` → `from app.services.utils.customer_utils`

- `hr_data_processor.py`:
  - `from app.services.db` → `from app.services.utils.db`

**core/ 폴더의 파일들 (서로 참조):**
- `hybrid_search_service.py`:
  - `from app.services.opensearch_client` → `from app.services.external.opensearch_client`
  - `from app.services.query_analyzer` → `from app.services.processors.query_analyzer`
  - `from app.services.text2sql_search` → `from app.services.core.text2sql_search`
  - `from app.services.opensearch_service` → `from app.services.external.opensearch_service`

#### 4-2. routers 폴더의 import 수정

**user_router.py:**
- `from app.services.user_service` → `from app.services.processors.user_service`
- `from app.services.db` → `from app.services.utils.db`

**qa_router.py:**
- `from app.services.opensearch_service` → `from app.services.external.opensearch_service`

**hybrid_search_router.py:**
- `from app.services.hybrid_search_service` → `from app.services.core.hybrid_search_service`

**document_router.py:**
- `from app.services.s3_service` → `from app.services.external.s3_service`
- `from app.services.postgres_service` → `from app.services.external.postgres_service`
- `from app.services.opensearch_service` → `from app.services.external.opensearch_service`
- `from app.services.document_relation_analyzer` → `from app.services.core.document_relation_analyzer`
- `from app.services.document_analyzer` → `from app.services.core.document_analyzer`
- `from app.services.text2sql_classifier` → `from app.services.core.text2sql_classifier`

**chat_history_router.py:**
- `from app.services.db` → `from app.services.utils.db`

**admin_router.py:**
- `from app.services.user_service` → `from app.services.processors.user_service`
- `from app.services.db` → `from app.services.utils.db`
- `from app.services.opensearch_service` → `from app.services.external.opensearch_service`
- `from app.services.opensearch_client` → `from app.services.external.opensearch_client`

#### 4-3. main.py의 import 수정

**main.py:**
- `from app.services.opensearch_service` → `from app.services.external.opensearch_service`
- `from app.services.opensearch_client` → `from app.services.external.opensearch_client`

### 5단계: 테스트 및 검증
1. 각 import 경로가 올바르게 수정되었는지 확인
2. 애플리케이션 실행 테스트
3. 각 기능별 동작 확인

### 6단계: 기존 services 폴더 정리
- 이동된 파일들 삭제
- 기존 `__init__.py` 파일 정리

## 주의사항
- 모든 import 경로를 한 번에 수정해야 함
- 순환 import 문제가 발생할 수 있으므로 주의
- 테스트를 통해 모든 기능이 정상 동작하는지 확인 필요 