# 환경변수 설정 가이드

이 문서는 Document QA API 시스템에서 사용되는 환경변수들의 역할과 설정 방법을 설명합니다.

## 📋 환경변수 목록

### 🔐 Database Configuration (PostgreSQL)

| 변수명 | 현재값 | 설명 | 필수 여부 |
|--------|--------|------|-----------|
| `POSTGRES_USER` | `myuser` | PostgreSQL 데이터베이스 사용자명 | ✅ |
| `POSTGRES_PASSWORD` | `mypassword` | PostgreSQL 데이터베이스 비밀번호 | ✅ |
| `POSTGRES_DB` | `mydatabase` | PostgreSQL 데이터베이스 이름 | ✅ |
| `POSTGRES_HOST` | `localhost` | PostgreSQL 호스트 주소 (Docker에서는 `postgres`) | ✅ |
| `POSTGRES_PORT` | `5432` | PostgreSQL 포트 번호 | ✅ |

**설정 가이드:**
- 개발 환경: `localhost` 사용
- Docker 환경: `postgres` (컨테이너명) 사용
- 비밀번호는 보안을 위해 강력한 값으로 변경 권장

### 🔍 OpenSearch Configuration

| 변수명 | 현재값 | 설명 | 필수 여부 |
|--------|--------|------|-----------|
| `OPENSEARCH_HOST` | `localhost` | OpenSearch 호스트 주소 (Docker에서는 `opensearch-node1`) | ✅ |
| `OPENSEARCH_PORT` | `9200` | OpenSearch 포트 번호 | ✅ |
| `OPENSEARCH_USER` | `admin` | OpenSearch 관리자 사용자명 | ✅ |
| `OPENSEARCH_INITIAL_ADMIN_PASSWORD` | `G7!kz@2pQw` | OpenSearch 관리자 비밀번호 | ✅ |

**설정 가이드:**
- 개발 환경: `localhost` 사용
- Docker 환경: `opensearch-node1` (컨테이너명) 사용
- 비밀번호는 보안을 위해 강력한 값으로 변경 권장

### 📦 MinIO Configuration (Object Storage)

| 변수명 | 현재값 | 설명 | 필수 여부 |
|--------|--------|------|-----------|
| `MINIO_ENDPOINT` | `http://localhost:9000` | MinIO 서버 엔드포인트 (Docker에서는 `http://minio:9000`) | ✅ |
| `MINIO_ROOT_USER` | `minioadmin` | MinIO 루트 사용자명 | ✅ |
| `MINIO_ROOT_PASSWORD` | `minioadmin` | MinIO 루트 비밀번호 | ✅ |
| `MINIO_BUCKET_NAME` | `documents` | 문서 저장용 버킷 이름 | ✅ |

**설정 가이드:**
- 개발 환경: `http://localhost:9000` 사용
- Docker 환경: `http://minio:9000` 사용
- 기본값 사용 가능하지만, 프로덕션에서는 보안을 위해 변경 권장

### 🗄️ PgAdmin Configuration

| 변수명 | 현재값 | 설명 | 필수 여부 |
|--------|--------|------|-----------|
| `PGADMIN_DEFAULT_EMAIL` | `admin@admin.com` | PgAdmin 로그인 이메일 | ✅ |
| `PGADMIN_DEFAULT_PASSWORD` | `admin1234` | PgAdmin 로그인 비밀번호 | ✅ |

**설정 가이드:**
- 실제 이메일 주소 사용 권장
- 비밀번호는 보안을 위해 강력한 값으로 변경 권장

### 🔗 Application Configuration

| 변수명 | 현재값 | 설명 | 필수 여부 |
|--------|--------|------|-----------|
| `DATABASE_URL` | `postgresql://myuser:mypassword@localhost:5432/mydatabase` | PostgreSQL 연결 문자열 | ✅ |
| `OPENSEARCH_URL` | `http://localhost:9200` | OpenSearch 연결 URL | ✅ |

**설정 가이드:**
- 위의 개별 설정값들을 기반으로 자동 생성됨
- 직접 수정하지 말고 개별 설정값들을 변경하세요

### 🔐 JWT Configuration

| 변수명 | 현재값 | 설명 | 필수 여부 |
|--------|--------|------|-----------|
| `JWT_SECRET_KEY` | `n!CnQ1>(DOcrbITm4]2bUxt[yTF+9,Gu^5s8Duo&27ZK8yCah5Qc-vNd=#.?w(*Ks` | JWT 토큰 암호화 키 | ✅ |

**설정 가이드:**
- **매우 중요**: 프로덕션에서는 반드시 새로운 키로 변경
- 최소 32자 이상의 복잡한 문자열 사용
- 온라인 JWT 시크릿 키 생성기 사용 권장

### 🤖 OpenAI Configuration

| 변수명 | 현재값 | 설명 | 필수 여부 |
|--------|--------|------|-----------|
| `OPENAI_API_KEY` | `your_openai_api_key_here` | OpenAI API 키 | ✅ |

**설정 가이드:**
- OpenAI 계정에서 발급받은 API 키 입력
- **보안 주의**: 이 키는 절대 공개되지 않도록 주의
- API 사용량에 따라 요금이 발생할 수 있음

## 🚀 환경 설정 방법

### 1. 개발 환경 설정
```bash
# .env 파일 복사
cp .env.example .env

# .env 파일 편집
# 각 변수들을 개발 환경에 맞게 수정
```

### 2. Docker 환경 설정
```bash
# Docker 환경에서는 호스트 주소를 컨테이너명으로 변경
POSTGRES_HOST=postgres
OPENSEARCH_HOST=opensearch-node1
MINIO_ENDPOINT=http://minio:9000
```

### 3. 프로덕션 환경 설정
```bash
# 보안을 위해 모든 비밀번호와 키를 강력한 값으로 변경
# 실제 도메인 주소 사용
# HTTPS 사용 권장
```

## 🔒 보안 권장사항

### 필수 변경 항목
1. **JWT_SECRET_KEY**: 새로운 강력한 키로 변경
2. **POSTGRES_PASSWORD**: 강력한 비밀번호로 변경
3. **OPENSEARCH_INITIAL_ADMIN_PASSWORD**: 강력한 비밀번호로 변경
4. **PGADMIN_DEFAULT_PASSWORD**: 강력한 비밀번호로 변경

### 선택 변경 항목
1. **MINIO_ROOT_PASSWORD**: 기본값에서 변경 권장
2. **PGADMIN_DEFAULT_EMAIL**: 실제 이메일 주소 사용 권장

## 📝 환경변수 생성 스크립트

```bash
#!/bin/bash
# .env 파일 생성 스크립트

cat > .env << EOF
# Database Configuration
POSTGRES_USER=myuser
POSTGRES_PASSWORD=\$(openssl rand -base64 32)
POSTGRES_DB=mydatabase
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# OpenSearch Configuration
OPENSEARCH_HOST=opensearch-node1
OPENSEARCH_PORT=9200
OPENSEARCH_USER=admin
OPENSEARCH_INITIAL_ADMIN_PASSWORD=\$(openssl rand -base64 32)

# MinIO Configuration
MINIO_ENDPOINT=http://minio:9000
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=\$(openssl rand -base64 16)
MINIO_BUCKET_NAME=documents

# PgAdmin Configuration
PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=\$(openssl rand -base64 16)

# JWT Configuration
JWT_SECRET_KEY=\$(openssl rand -base64 64)

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
EOF
```

## ⚠️ 주의사항

1. **API 키 보안**: OpenAI API 키는 절대 공개 저장소에 업로드하지 마세요
2. **비밀번호 강도**: 모든 비밀번호는 최소 8자 이상, 특수문자 포함 권장
3. **환경별 설정**: 개발/스테이징/프로덕션 환경별로 다른 설정 사용
4. **백업**: 중요한 설정값들은 안전한 곳에 백업 보관

## 🔧 문제 해결

### 일반적인 문제들
1. **연결 실패**: 호스트 주소가 올바른지 확인
2. **인증 실패**: 사용자명/비밀번호가 올바른지 확인
3. **권한 오류**: 데이터베이스 사용자 권한 확인

### 로그 확인
```bash
# Docker 로그 확인
docker-compose logs fastapi-app
docker-compose logs postgres
docker-compose logs opensearch-node1
``` 