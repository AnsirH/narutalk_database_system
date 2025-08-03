# AWS 마이그레이션 가이드

## 📋 개요
현재 Docker 기반 인프라를 AWS 클라우드로 마이그레이션하는 가이드입니다.

## 🏗️ 아키텍처 변경사항

### **현재 구조 (Docker)**
- **MinIO** → **AWS S3**
- **PostgreSQL (Docker)** → **AWS RDS**
- **OpenSearch (Docker)** → **AWS OpenSearch Service**
- **Docker Compose** → **AWS ECS/Fargate**

### **새로운 AWS 구조**
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

## 🚀 단계별 마이그레이션

### **1단계: AWS S3 설정**

#### 1-1. S3 버킷 생성
```bash
# S3 버킷 생성
aws s3 mb s3://database-api-files

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
```

#### 1-2. 환경변수 설정
```bash
# env.aws.template을 복사하여 .env.aws 생성
cp docker/env.aws.template docker/.env.aws

# AWS S3 설정 수정
AWS_S3_ACCESS_KEY_ID=your_aws_access_key_id
AWS_S3_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_S3_REGION=ap-northeast-2
AWS_S3_BUCKET_NAME=database-api-files
```

### **2단계: AWS RDS 설정**

#### 2-1. RDS PostgreSQL 생성
```bash
# 보안 그룹 생성
aws ec2 create-security-group \
  --group-name database-api-rds-sg \
  --description "Security group for RDS PostgreSQL"

# 보안 그룹 규칙 추가
aws ec2 authorize-security-group-ingress \
  --group-name database-api-rds-sg \
  --protocol tcp \
  --port 5432 \
  --cidr 0.0.0.0/0

# RDS 인스턴스 생성
aws rds create-db-instance \
  --db-instance-identifier database-api-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username postgres \
  --master-user-password your_password \
  --allocated-storage 20 \
  --vpc-security-group-ids sg-12345 \
  --backup-retention-period 7 \
  --storage-encrypted
```

#### 2-2. 환경변수 설정
```bash
# RDS 엔드포인트 확인
aws rds describe-db-instances \
  --db-instance-identifier database-api-db \
  --query 'DBInstances[0].Endpoint.Address'

# .env.aws 파일에 RDS 설정 추가
POSTGRES_HOST=your-rds-endpoint.ap-northeast-2.rds.amazonaws.com
POSTGRES_PASSWORD=your_rds_password
```

### **3단계: AWS OpenSearch Service 설정**

#### 3-1. OpenSearch 도메인 생성
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
  }'
```

#### 3-2. 환경변수 설정
```bash
# OpenSearch 엔드포인트 확인
aws opensearch describe-domain \
  --domain-name database-api-search \
  --query 'DomainStatus.Endpoints.vpc'

# .env.aws 파일에 OpenSearch 설정 추가
OPENSEARCH_HOST=your-opensearch-domain.ap-northeast-2.es.amazonaws.com
OPENSEARCH_PORT=443
```

### **4단계: AWS ECR 설정**

#### 4-1. ECR 저장소 생성
```bash
# ECR 저장소 생성
aws ecr create-repository \
  --repository-name database-fastapi-app \
  --image-scanning-configuration scanOnPush=true
```

#### 4-2. 이미지 빌드 및 푸시
```bash
# 배포 스크립트 실행
cd docker
chmod +x deploy-ecr.sh
./deploy-ecr.sh your-aws-account-id ap-northeast-2 database-fastapi-app latest
```

### **5단계: AWS ECS 설정**

#### 5-1. ECS 클러스터 생성
```bash
# ECS 클러스터 생성
aws ecs create-cluster \
  --cluster-name database-api-cluster
```

#### 5-2. Task Definition 생성
```json
{
  "family": "database-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
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
```

#### 5-3. ECS 서비스 생성
```bash
# 서비스 생성
aws ecs create-service \
  --cluster database-api-cluster \
  --service-name database-api-service \
  --task-definition database-api:1 \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345],securityGroups=[sg-12345],assignPublicIp=ENABLED}"
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
POSTGRES_PASSWORD=your_rds_password

# OpenSearch 설정
OPENSEARCH_HOST=your-opensearch-domain.ap-northeast-2.es.amazonaws.com
OPENSEARCH_PORT=443
```

### **배포 스크립트 (deploy-ecr.sh)**
```bash
# 사용법
./deploy-ecr.sh [AWS_ACCOUNT_ID] [REGION] [REPOSITORY_NAME] [IMAGE_TAG]
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