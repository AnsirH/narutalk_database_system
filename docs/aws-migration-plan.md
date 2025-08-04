# AWS 마이그레이션 계획

## 📋 현재 상태

### ✅ 완료된 작업
- **정리 기능 구현**: `CleanupService` 클래스로 PostgreSQL 중심의 데이터 무결성 보장
- **S3 서비스 개선**: AWS S3와 MinIO 모두 지원하는 통합 서비스
- **AWS 설정 추가**: `AWSS3Settings` 클래스 및 `get_aws_s3_config()` 메서드
- **배포 도구**: ECR 배포 스크립트 (`deploy-ecr.sh`)
- **환경변수 템플릿**: AWS 환경변수 템플릿 (`env.aws.template`)
- **마이그레이션 가이드**: 상세한 단계별 가이드 (`docker/README.md`)

### 🔄 현재 구조
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MinIO/S3      │    │   PostgreSQL    │    │   OpenSearch    │
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

### 🎯 목표 구조
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AWS S3        │    │   AWS RDS       │    │   OpenSearch    │
│   (파일 저장)    │    │   (PostgreSQL)  │    │   Service       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   AWS ECS       │
                    │   (FastAPI App) │
                    └─────────────────┘
```

## 🚀 실행 단계

### **1단계: AWS 계정 및 IAM 설정**

#### 1-1. AWS CLI 설정
```bash
# AWS CLI 설치 및 설정
aws configure
# AWS Access Key ID: your_access_key
# AWS Secret Access Key: your_secret_key
# Default region name: ap-northeast-2
# Default output format: json
```

#### 1-2. IAM 권한 설정
```bash
# IAM 사용자 생성 (필요한 경우)
aws iam create-user --user-name database-api-user

# S3 권한 정책 생성
aws iam create-policy \
  --policy-name DatabaseApiS3Policy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ],
        "Resource": [
          "arn:aws:s3:::database-api-files",
          "arn:aws:s3:::database-api-files/*"
        ]
      }
    ]
  }'

# RDS 권한 정책 생성
aws iam create-policy \
  --policy-name DatabaseApiRDSPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "rds:DescribeDBInstances",
          "rds:CreateDBInstance",
          "rds:ModifyDBInstance",
          "rds:DeleteDBInstance"
        ],
        "Resource": "*"
      }
    ]
  }'

# OpenSearch 권한 정책 생성
aws iam create-policy \
  --policy-name DatabaseApiOpenSearchPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "es:DescribeElasticsearchDomain",
          "es:CreateElasticsearchDomain",
          "es:UpdateElasticsearchDomainConfig",
          "es:DeleteElasticsearchDomain"
        ],
        "Resource": "*"
      }
    ]
  }'

# ECR 권한 정책 생성
aws iam create-policy \
  --policy-name DatabaseApiECRPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ],
        "Resource": "*"
      }
    ]
  }'

# ECS 권한 정책 생성
aws iam create-policy \
  --policy-name DatabaseApiECSPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "ecs:CreateCluster",
          "ecs:CreateService",
          "ecs:CreateTaskDefinition",
          "ecs:RegisterTaskDefinition",
          "ecs:UpdateService",
          "ecs:DescribeServices",
          "ecs:DescribeTasks"
        ],
        "Resource": "*"
      }
    ]
  }'
```

### **2단계: AWS S3 설정**

#### 2-1. S3 버킷 생성
```bash
# S3 버킷 생성
aws s3 mb s3://database-api-files --region ap-northeast-2

# 버전 관리 활성화
aws s3api put-bucket-versioning \
  --bucket database-api-files \
  --versioning-configuration Status=Enabled

# 암호화 설정
aws s3api put-bucket-encryption \
  --bucket database-api-files \
  --server-side-encryption-configuration '{
    "Rules": [
      {
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "AES256"
        }
      }
    ]
  }'

# 버킷 정책 설정 (선택사항)
aws s3api put-bucket-policy \
  --bucket database-api-files \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "PublicReadGetObject",
        "Effect": "Allow",
        "Principal": "*",
        "Action": "s3:GetObject",
        "Resource": "arn:aws:s3:::database-api-files/*"
      }
    ]
  }'
```

#### 2-2. 환경변수 설정
```bash
# 환경변수 파일 생성
cp docker/env.aws.template docker/.env.aws

# .env.aws 파일 편집하여 AWS S3 설정 추가
AWS_S3_ACCESS_KEY_ID=your_aws_access_key_id
AWS_S3_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_S3_REGION=ap-northeast-2
AWS_S3_BUCKET_NAME=database-api-files
```

### **3단계: AWS RDS 설정**

#### 3-1. VPC 및 보안 그룹 생성
```bash
# VPC 생성 (기본 VPC 사용하는 경우 생략)
aws ec2 create-vpc --cidr-block 10.0.0.0/16

# 보안 그룹 생성
aws ec2 create-security-group \
  --group-name database-api-rds-sg \
  --description "Security group for RDS PostgreSQL" \
  --vpc-id vpc-12345

# 보안 그룹 규칙 추가
aws ec2 authorize-security-group-ingress \
  --group-id sg-12345 \
  --protocol tcp \
  --port 5432 \
  --cidr 0.0.0.0/0
```

#### 3-2. RDS PostgreSQL 생성
```bash
# RDS 인스턴스 생성
aws rds create-db-instance \
  --db-instance-identifier database-api-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username postgres \
  --master-user-password your_secure_password \
  --allocated-storage 20 \
  --vpc-security-group-ids sg-12345 \
  --backup-retention-period 7 \
  --storage-encrypted \
  --region ap-northeast-2

# RDS 엔드포인트 확인
aws rds describe-db-instances \
  --db-instance-identifier database-api-db \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text
```

#### 3-3. 환경변수 설정
```bash
# .env.aws 파일에 RDS 설정 추가
POSTGRES_HOST=your-rds-endpoint.ap-northeast-2.rds.amazonaws.com
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=database_api
POSTGRES_USER=postgres
POSTGRES_PORT=5432
```

### **4단계: AWS OpenSearch Service 설정**

#### 4-1. OpenSearch 도메인 생성
```bash
# OpenSearch 도메인 생성
aws opensearch create-domain \
  --domain-name database-api-search \
  --engine-version OpenSearch_2.13 \
  --cluster-config InstanceType=m6g.large.search,InstanceCount=1 \
  --ebs-options EBSEnabled=true,VolumeType=gp2,VolumeSize=10 \
  --access-policies '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "AWS": "*"
        },
        "Action": "es:*",
        "Resource": "*"
      }
    ]
  }' \
  --region ap-northeast-2

# OpenSearch 엔드포인트 확인
aws opensearch describe-domain \
  --domain-name database-api-search \
  --query 'DomainStatus.Endpoints.vpc' \
  --output text
```

#### 4-2. 환경변수 설정
```bash
# .env.aws 파일에 OpenSearch 설정 추가
OPENSEARCH_HOST=your-opensearch-domain.ap-northeast-2.es.amazonaws.com
OPENSEARCH_PORT=443
OPENSEARCH_USER=admin
OPENSEARCH_INITIAL_ADMIN_PASSWORD=your_opensearch_password
```

### **5단계: AWS ECR 설정**

#### 5-1. ECR 저장소 생성
```bash
# ECR 저장소 생성
aws ecr create-repository \
  --repository-name database-fastapi-app \
  --image-scanning-configuration scanOnPush=true \
  --region ap-northeast-2
```

#### 5-2. 이미지 빌드 및 푸시
```bash
# 배포 스크립트 실행
cd docker
chmod +x deploy-ecr.sh
./deploy-ecr.sh your-aws-account-id ap-northeast-2 database-fastapi-app latest
```

### **6단계: AWS ECS 설정**

#### 6-1. ECS 클러스터 생성
```bash
# ECS 클러스터 생성
aws ecs create-cluster \
  --cluster-name database-api-cluster \
  --region ap-northeast-2
```

#### 6-2. Task Definition 생성
```bash
# Task Definition JSON 파일 생성
cat > task-definition.json << 'EOF'
{
  "family": "database-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::your-account:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "database-api-app",
      "image": "your-account.dkr.ecr.ap-northeast-2.amazonaws.com/database-fastapi-app:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "AWS_S3_ACCESS_KEY_ID",
          "value": "your_access_key"
        },
        {
          "name": "AWS_S3_SECRET_ACCESS_KEY",
          "value": "your_secret_key"
        },
        {
          "name": "AWS_S3_REGION",
          "value": "ap-northeast-2"
        },
        {
          "name": "AWS_S3_BUCKET_NAME",
          "value": "database-api-files"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/database-api",
          "awslogs-region": "ap-northeast-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
EOF

# Task Definition 등록
aws ecs register-task-definition \
  --cli-input-json file://task-definition.json \
  --region ap-northeast-2
```

#### 6-3. ECS 서비스 생성
```bash
# 서비스 생성
aws ecs create-service \
  --cluster database-api-cluster \
  --service-name database-api-service \
  --task-definition database-api:1 \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345],securityGroups=[sg-12345],assignPublicIp=ENABLED}" \
  --region ap-northeast-2
```

### **7단계: 데이터 마이그레이션**

#### 7-1. PostgreSQL 데이터 마이그레이션
```bash
# 현재 PostgreSQL 데이터 백업
docker-compose exec postgres pg_dump -U postgres database_api > backup.sql

# RDS에 데이터 복원
psql -h your-rds-endpoint.ap-northeast-2.rds.amazonaws.com -U postgres -d database_api < backup.sql
```

#### 7-2. S3 파일 마이그레이션
```bash
# MinIO에서 S3로 파일 동기화
aws s3 sync s3://minio-bucket s3://database-api-files --source-region ap-northeast-2
```

#### 7-3. OpenSearch 인덱스 마이그레이션
```bash
# 현재 OpenSearch 인덱스 백업
curl -X GET "http://localhost:9200/_all" > opensearch_backup.json

# AWS OpenSearch Service에 인덱스 복원
curl -X POST "https://your-opensearch-domain.ap-northeast-2.es.amazonaws.com/_bulk" \
  -H "Content-Type: application/json" \
  --data-binary @opensearch_backup.json
```

### **8단계: 테스트 및 검증**

#### 8-1. API 엔드포인트 테스트
```bash
# ECS 서비스 상태 확인
aws ecs describe-services \
  --cluster database-api-cluster \
  --services database-api-service

# API 테스트
curl -X GET "http://your-ecs-public-ip:8000/api/health"
```

#### 8-2. 파일 업로드/다운로드 테스트
```bash
# 파일 업로드 테스트
curl -X POST "http://your-ecs-public-ip:8000/api/admin/upload-document" \
  -F "file=@test-file.txt"

# 파일 다운로드 테스트
curl -X GET "http://your-ecs-public-ip:8000/api/documents/download/test-file.txt"
```

#### 8-3. 검색 기능 테스트
```bash
# 검색 API 테스트
curl -X POST "http://your-ecs-public-ip:8000/api/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "test search"}'
```

## 🔧 설정 파일

### **환경변수 파일 (.env.aws)**
```bash
# AWS S3 설정
AWS_S3_ACCESS_KEY_ID=your_aws_access_key_id
AWS_S3_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_S3_REGION=ap-northeast-2
AWS_S3_BUCKET_NAME=database-api-files

# RDS 설정
POSTGRES_HOST=your-rds-endpoint.ap-northeast-2.rds.amazonaws.com
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=database_api
POSTGRES_USER=postgres
POSTGRES_PORT=5432

# OpenSearch 설정
OPENSEARCH_HOST=your-opensearch-domain.ap-northeast-2.es.amazonaws.com
OPENSEARCH_PORT=443
OPENSEARCH_USER=admin
OPENSEARCH_INITIAL_ADMIN_PASSWORD=your_opensearch_password

# JWT 설정
JWT_SECRET_KEY=your_jwt_secret_key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# OpenAI 설정
OPENAI_API_KEY=your_openai_api_key

# 애플리케이션 설정
APP_ENV=production
APP_DEBUG=false
```

## 💰 비용 예상

### **월 예상 비용 (ap-northeast-2)**
- **ECS Fargate**: ~$30-50/월
- **RDS PostgreSQL**: ~$20-30/월
- **S3**: ~$5-10/월
- **OpenSearch Service**: ~$50-100/월
- **총 예상 비용**: ~$105-190/월

### **비용 절약 방안**
- RDS Reserved Instance 사용
- S3 Intelligent Tiering 활성화
- Auto Scaling 설정
- CloudWatch 모니터링 설정

## 🔄 마이그레이션 체크리스트

### **준비 단계**
- [ ] AWS 계정 설정
- [ ] IAM 권한 설정
- [ ] VPC 및 보안 그룹 구성
- [ ] 환경변수 파일 준비

### **인프라 생성**
- [ ] S3 버킷 생성
- [ ] RDS PostgreSQL 생성
- [ ] OpenSearch 도메인 생성
- [ ] ECR 저장소 생성
- [ ] ECS 클러스터 생성

### **애플리케이션 배포**
- [ ] Docker 이미지 빌드
- [ ] ECR에 이미지 푸시
- [ ] ECS Task Definition 생성
- [ ] ECS 서비스 배포
- [ ] 도메인 연결 및 SSL 설정

### **데이터 마이그레이션**
- [ ] PostgreSQL 데이터 백업
- [ ] S3 파일 마이그레이션
- [ ] OpenSearch 인덱스 마이그레이션
- [ ] 데이터 무결성 검증

### **테스트 및 검증**
- [ ] API 엔드포인트 테스트
- [ ] 파일 업로드/다운로드 테스트
- [ ] 검색 기능 테스트
- [ ] 성능 모니터링

## 🚨 주의사항

1. **보안**: IAM 권한을 최소 권한 원칙에 따라 설정
2. **비용**: 사용하지 않는 리소스는 삭제
3. **백업**: 중요한 데이터는 정기적으로 백업
4. **모니터링**: CloudWatch를 통한 지속적인 모니터링
5. **SSL**: HTTPS 연결을 위한 SSL 인증서 설정

## 📞 지원

문제가 발생하면 다음을 확인하세요:
1. AWS CLI 설정
2. IAM 권한
3. 보안 그룹 규칙
4. 환경변수 설정
5. 로그 확인 (CloudWatch) 