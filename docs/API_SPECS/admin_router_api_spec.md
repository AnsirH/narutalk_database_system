# Admin Router API 명세서

## 개요
관리자 전용 기능을 제공하는 API입니다. 직원 등록, 시스템 관리 등의 기능을 포함합니다.

## 기본 정보
- **Base URL**: `/admin`
- **Content-Type**: `application/json`
- **인증**: 관리자 권한 필요 (admin role)

## API 엔드포인트

### 1. 직원 등록 (관리자만)
**POST** `/admin/register-employee`

#### 헤더
```
Authorization: Bearer <admin_token>
```

#### 요청 본문
```json
{
  "email": "newuser@example.com",
  "username": "newuser",
  "password": "password123",
  "name": "새 사용자",
  "role": "user"
}
```

#### 응답
```json
{
  "employee_id": 3,
  "email": "newuser@example.com",
  "username": "newuser",
  "name": "새 사용자",
  "role": "user",
  "is_active": true,
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### 사용 예시
```bash
curl -X POST "http://localhost:8010/admin/register-employee" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "username": "newuser",
    "password": "password123",
    "name": "새 사용자",
    "role": "user"
  }'
```

---

### 2. 초기 관리자 계정 생성
**POST** `/admin/init-admin`

#### 요청 본문
```json
{
  "email": "admin@example.com",
  "username": "admin",
  "password": "admin123",
  "name": "시스템 관리자",
  "role": "admin"
}
```

#### 응답
```json
{
  "employee_id": 1,
  "email": "admin@example.com",
  "username": "admin",
  "name": "시스템 관리자",
  "role": "admin",
  "is_active": true,
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### 사용 예시
```bash
curl -X POST "http://localhost:8010/admin/init-admin" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "username": "admin",
    "password": "admin123",
    "name": "시스템 관리자",
    "role": "admin"
  }'
```

#### 주의사항
- 최초 1회만 사용 가능
- 이미 관리자가 존재하면 400 에러 반환
- 인증이 필요하지 않음 (시스템 초기화용)

---

### 3. 깨진 문서 정리
**DELETE** `/admin/cleanup-corrupted-documents`

#### 헤더
```
Authorization: Bearer <admin_token>
```

#### 응답
```json
{
  "success": true,
  "message": "깨진 문서 정리 완료",
  "deleted_count": 5
}
```

#### 사용 예시
```bash
curl -X DELETE "http://localhost:8010/admin/cleanup-corrupted-documents" \
  -H "Authorization: Bearer <admin_token>"
```

#### 기능 설명
- OpenSearch에서 깨진 텍스트가 포함된 문서 청크들을 삭제
- 시스템 성능 향상 및 데이터 무결성 보장
- 관리자만 접근 가능

---

## 에러 응답

### 400 Bad Request
```json
{
  "detail": "Email already registered"
}
```

```json
{
  "detail": "관리자 계정이 이미 존재합니다."
}
```

```json
{
  "detail": "role은 반드시 'admin'이어야 합니다."
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

### 500 Internal Server Error
```json
{
  "detail": "관리자 계정 생성 중 오류 발생: <error_message>"
}
```

---

## 권한 요구사항

### 관리자 권한이 필요한 기능
- 직원 등록 (`/admin/register-employee`)
- 깨진 문서 정리 (`/admin/cleanup-corrupted-documents`)

### 인증 불필요한 기능
- 초기 관리자 생성 (`/admin/init-admin`) - 시스템 초기화용

---

## 초기 관리자 생성 프로세스

### 1단계: 시스템 초기화
```bash
# 최초 관리자 계정 생성
curl -X POST "http://localhost:8010/admin/init-admin" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "username": "admin",
    "password": "admin123",
    "name": "시스템 관리자",
    "role": "admin"
  }'
```

### 2단계: 관리자 로그인
```bash
# 생성된 관리자로 로그인
curl -X POST "http://localhost:8010/user/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=admin123"
```

### 3단계: 추가 직원 등록
```bash
# 관리자 토큰으로 추가 직원 등록
curl -X POST "http://localhost:8010/admin/register-employee" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "user",
    "password": "password123",
    "name": "일반 사용자",
    "role": "user"
  }'
```

---

## 주의사항

1. **초기 관리자 생성**: 시스템 최초 실행 시에만 사용
2. **관리자 권한**: 대부분의 기능은 admin 역할이 필요
3. **데이터 백업**: 깨진 문서 정리 전에 데이터 백업 권장
4. **보안**: 관리자 계정 정보를 안전하게 보관
5. **토큰 관리**: 관리자 토큰의 안전한 보관 및 사용 