# AWS 배포 및 마이그레이션 가이드

## 📁 폴더 구조
```
docker/
├── aws/                    # AWS 관련 파일들
│   ├── README.md          # 이 파일 (AWS 가이드)
│   ├── deploy-ecr.sh     # ECR 배포 스크립트
│   ├── env.template       # AWS 환경변수 템플릿
│   ├── terraform/         # Terraform 인프라 코드 (선택사항)
│   └── scripts/           # 추가 AWS 스크립트들
├── docker-compose.yml     # 로컬 개발용
├── Dockerfile            # 애플리케이션 이미지
└── start.sh              # 로컬 실행 스크립트
```

## 🚀 빠른 시작

### 1. AWS 환경변수 설정
```bash
# 템플릿 복사
cp docker/aws/env.template docker/aws/.env.aws

# 실제 값으로 수정
nano docker/aws/.env.aws
```

### 2. ECR 배포
```bash
# ECR에 이미지 배포
./docker/aws/deploy-ecr.sh [AWS_ACCOUNT_ID] [REGION] [REPOSITORY_NAME]
```

## 📋 상세 가이드

### AWS 서비스 구성
- **S3**: 파일 저장소 (MinIO 대체)
- **RDS**: PostgreSQL 데이터베이스
- **OpenSearch Service**: 검색 엔진
- **ECR**: Docker 이미지 저장소
- **ECS/Fargate**: 컨테이너 오케스트레이션

### 마이그레이션 단계
1. **S3 설정** - 파일 저장소 마이그레이션
2. **RDS 설정** - 데이터베이스 마이그레이션  
3. **OpenSearch 설정** - 검색 서비스 마이그레이션
4. **ECR 배포** - 애플리케이션 이미지 배포
5. **ECS 배포** - 프로덕션 환경 구성

자세한 내용은 각 섹션을 참조하세요. 