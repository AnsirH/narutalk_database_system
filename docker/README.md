# Docker 개발 환경 가이드

## 📋 개요
로컬 개발을 위한 Docker Compose 환경 설정 가이드입니다.

## 🏗️ 아키텍처

### **로컬 개발 환경**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MinIO         │    │   PostgreSQL    │    │   OpenSearch    │
│   (파일 저장)    │    │   (Docker)      │    │   (Docker)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   FastAPI App   │
                    │   (Docker)      │
                    └─────────────────┘
```

## 🚀 빠른 시작

### 1. 환경변수 설정
```bash
# 환경변수 파일 복사
cp docs/환경변수_README.md .env

# 실제 값으로 수정
nano .env
```

### 2. 서비스 시작
```bash
# 모든 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f
```

### 3. 서비스 중지
```bash
# 모든 서비스 중지
docker-compose down
```

## 📊 서비스 정보

### **포트 매핑**
- **FastAPI App**: http://localhost:8010
- **PostgreSQL**: localhost:5432
- **PgAdmin**: http://localhost:5050
- **MinIO Console**: http://localhost:9001
- **OpenSearch**: http://localhost:9200

### **기본 접속 정보**
- **PgAdmin**: admin@admin.com / admin1234
- **MinIO**: minioadmin / minioadmin
- **OpenSearch**: admin / G7!kz@2pQw

## 🔧 개발 도구

### **데이터베이스 관리**
```bash
# PostgreSQL 접속
docker exec -it postgres psql -U myuser -d mydatabase

# PgAdmin 접속
# 브라우저에서 http://localhost:5050 접속
```

### **파일 저장소 관리**
```bash
# MinIO Console 접속
# 브라우저에서 http://localhost:9001 접속
```

### **검색 엔진 관리**
```bash
# OpenSearch 접속
curl -u admin:G7!kz@2pQw http://localhost:9200
```

## 📁 폴더 구조

```
docker/
├── README.md              # 이 파일 (로컬 개발 가이드)
├── docker-compose.yml     # 서비스 구성
├── Dockerfile            # 애플리케이션 이미지
├── start.sh              # 실행 스크립트
├── aws/                  # AWS 배포 관련 (별도 폴더)
│   ├── README.md         # AWS 가이드
│   ├── deploy-ecr.sh    # ECR 배포 스크립트
│   ├── env.template      # AWS 환경변수 템플릿
│   └── MIGRATION_GUIDE.md # AWS 마이그레이션 가이드
├── pgdata/               # PostgreSQL 데이터
├── pgadmin_data/         # PgAdmin 데이터
├── minio_data/           # MinIO 데이터
└── osdata*/              # OpenSearch 데이터
```

## 🛠️ 개발 워크플로우

### **1. 코드 수정**
```bash
# 애플리케이션 코드 수정
# app/ 폴더의 파일들을 수정하면 자동으로 반영됩니다
```

### **2. 데이터베이스 마이그레이션**
```bash
# 마이그레이션 실행
docker exec -it fastapi-app alembic upgrade head

# 새 마이그레이션 생성
docker exec -it fastapi-app alembic revision --autogenerate -m "설명"
```

### **3. 로그 확인**
```bash
# 특정 서비스 로그
docker-compose logs fastapi-app
docker-compose logs postgres
docker-compose logs minio
```

### **4. 서비스 재시작**
```bash
# 특정 서비스만 재시작
docker-compose restart fastapi-app

# 모든 서비스 재시작
docker-compose restart
```

## 🔍 문제 해결

### **포트 충돌**
```bash
# 사용 중인 포트 확인
netstat -tulpn | grep :8010

# 다른 포트로 변경 (docker-compose.yml 수정)
ports:
  - "8011:8000"  # 8010 → 8011로 변경
```

### **데이터베이스 연결 실패**
```bash
# PostgreSQL 상태 확인
docker-compose ps postgres

# PostgreSQL 로그 확인
docker-compose logs postgres
```

### **메모리 부족**
```bash
# Docker 리소스 확인
docker system df

# 사용하지 않는 리소스 정리
docker system prune -a
```

## 📚 추가 문서

- **환경변수 설정**: `docs/환경변수_README.md`
- **API 명세서**: `docs/CHAT_HISTORY_API_SPEC.md`
- **AWS 배포**: `docker/aws/README.md`
- **JWT 보안**: `docs/JWT_SECURITY_GUIDE.md`

## 🚨 주의사항

1. **데이터 백업**: 중요한 데이터는 정기적으로 백업
2. **환경변수**: 민감한 정보는 .env 파일에 저장
3. **포트 관리**: 다른 서비스와 포트 충돌 주의
4. **리소스 모니터링**: Docker 리소스 사용량 확인
5. **보안**: 개발 환경이므로 프로덕션 보안 설정 적용하지 않음 