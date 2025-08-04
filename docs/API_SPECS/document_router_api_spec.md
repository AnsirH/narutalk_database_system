# Document Router API 명세서

## 개요
문서 업로드, 관리, 검색 기능을 제공하는 API입니다. 다양한 파일 형식을 지원하며 텍스트 추출 및 분석 기능을 포함합니다.

## 기본 정보
- **Base URL**: `/documents`
- **Content-Type**: `multipart/form-data` (업로드), `application/json`
- **인증**: JWT 토큰 기반

## 지원 파일 형식

### 텍스트 문서
- **PDF** (.pdf)
- **DOCX** (.docx)
- **TXT** (.txt)

### 데이터 파일
- **CSV** (.csv)
- **Excel** (.xlsx, .xls)

## API 엔드포인트

### 1. 문서 업로드
**POST** `/documents/upload`

#### 헤더
```
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

#### 요청 본문 (Form Data)
```
file: File (업로드할 파일)
doc_title: string (문서 제목)
uploader_id: integer (업로더 ID)
version: string (선택사항, 문서 버전)
```

#### 응답 (텍스트 문서)
```json
{
  "doc_id": 1,
  "doc_title": "샘플 문서",
  "doc_type": "pdf",
  "uploader_id": 1,
  "file_path": "documents/sample.pdf",
  "version": "1.0",
  "created_at": "2024-01-01T12:00:00Z",
  "analysis": {
    "text_length": 1500,
    "chunks_count": 5,
    "entities_found": ["회사명", "날짜"],
    "summary": "문서 요약..."
  }
}
```

#### 응답 (데이터 파일)
```json
{
  "doc_title": "데이터 파일",
  "doc_type": "csv",
  "uploader_id": 1,
  "version": "1.0",
  "created_at": "2024-01-01T12:00:00Z",
  "message": "데이터 파일이 성공적으로 업로드되었습니다.",
  "analysis": {
    "row_count": 100,
    "column_count": 5,
    "data_preview": [...]
  }
}
```

#### 사용 예시
```bash
curl -X POST "http://localhost:8010/documents/upload" \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@sample.pdf" \
  -F "doc_title=샘플 문서" \
  -F "uploader_id=1" \
  -F "version=1.0"
```

---

### 2. 문서 목록 조회
**GET** `/documents/`

#### 헤더
```
Authorization: Bearer <access_token>
```

#### 응답
```json
[
  {
    "doc_id": 1,
    "doc_title": "샘플 문서",
    "doc_type": "pdf",
    "uploader_id": 1,
    "file_path": "documents/sample.pdf",
    "version": "1.0",
    "created_at": "2024-01-01T12:00:00Z"
  },
  {
    "doc_id": 2,
    "doc_title": "데이터 파일",
    "doc_type": "csv",
    "uploader_id": 1,
    "file_path": "documents/data.csv",
    "version": "1.0",
    "created_at": "2024-01-01T12:00:00Z"
  }
]
```

#### 사용 예시
```bash
curl -X GET "http://localhost:8010/documents/" \
  -H "Authorization: Bearer <access_token>"
```

---

### 3. 특정 문서 조회
**GET** `/documents/{doc_id}`

#### 헤더
```
Authorization: Bearer <access_token>
```

#### 응답
```json
{
  "doc_id": 1,
  "doc_title": "샘플 문서",
  "doc_type": "pdf",
  "uploader_id": 1,
  "file_path": "documents/sample.pdf",
  "version": "1.0",
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### 사용 예시
```bash
curl -X GET "http://localhost:8010/documents/1" \
  -H "Authorization: Bearer <access_token>"
```

---

### 4. 문서 삭제 (관리자만)
**DELETE** `/documents/{doc_id}`

#### 헤더
```
Authorization: Bearer <admin_token>
```

#### 응답
```json
{
  "doc_id": 1,
  "doc_title": "샘플 문서",
  "doc_type": "pdf",
  "uploader_id": 1,
  "file_path": "documents/sample.pdf",
  "version": "1.0",
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### 사용 예시
```bash
curl -X DELETE "http://localhost:8010/documents/1" \
  -H "Authorization: Bearer <admin_token>"
```

---

## 파일 처리 기능

### 텍스트 추출
- **PDF**: PyPDF2를 사용한 텍스트 추출
- **DOCX**: python-docx를 사용한 텍스트 추출
- **TXT**: UTF-8 인코딩으로 텍스트 읽기

### 데이터 처리
- **CSV**: pandas를 사용한 데이터 읽기
- **Excel**: pandas를 사용한 데이터 읽기

### 문서 분석
- 텍스트 청킹 (OpenSearch 인덱싱용)
- 엔티티 추출
- 문서 요약 생성
- 관계 분석

---

## 에러 응답

### 400 Bad Request
```json
{
  "detail": "지원하지 않는 파일 형식입니다."
}
```

```json
{
  "detail": "파일 크기가 너무 큽니다."
}
```

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 403 Forbidden
```json
{
  "detail": "Admin privileges required"
}
```

### 404 Not Found
```json
{
  "detail": "문서를 찾을 수 없습니다."
}
```

### 500 Internal Server Error
```json
{
  "detail": "파일 업로드 중 오류가 발생했습니다."
}
```

---

## 파일 크기 제한

### 권장 사항
- **PDF**: 50MB 이하
- **DOCX**: 20MB 이하
- **TXT**: 10MB 이하
- **CSV**: 100MB 이하
- **Excel**: 50MB 이하

---

## 문서 분석 기능

### 텍스트 문서 분석
- 텍스트 길이 계산
- 청크 분할 (검색용)
- 엔티티 추출
- 요약 생성

### 데이터 파일 분석
- 행/열 수 계산
- 데이터 미리보기
- 스키마 분석

---

## 주의사항

1. **파일 형식**: 지원되는 형식만 업로드 가능
2. **파일 크기**: 권장 크기 제한 준수
3. **권한**: 문서 삭제는 관리자만 가능
4. **백업**: 중요한 문서는 별도 백업 권장
5. **보안**: 민감한 정보가 포함된 문서 주의 