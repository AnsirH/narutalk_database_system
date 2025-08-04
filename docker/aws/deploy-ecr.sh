#!/bin/bash

# AWS ECR 배포 스크립트
# 사용법: ./deploy-ecr.sh [AWS_ACCOUNT_ID] [REGION] [REPOSITORY_NAME]

set -e

# 기본값 설정
AWS_ACCOUNT_ID=${1:-"your-aws-account-id"}
REGION=${2:-"ap-northeast-2"}
REPOSITORY_NAME=${3:-"database-fastapi-app"}
IMAGE_TAG=${4:-"latest"}

echo "🚀 AWS ECR 배포 시작..."
echo "📋 설정 정보:"
echo "  - AWS Account ID: $AWS_ACCOUNT_ID"
echo "  - Region: $REGION"
echo "  - Repository: $REPOSITORY_NAME"
echo "  - Image Tag: $IMAGE_TAG"

# ECR 저장소 URI
ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

# 1. AWS CLI 로그인
echo "🔐 AWS ECR 로그인 중..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI

# 2. ECR 저장소 생성 (없는 경우)
echo "📦 ECR 저장소 확인/생성 중..."
aws ecr describe-repositories --repository-names $REPOSITORY_NAME --region $REGION 2>/dev/null || {
    echo "  - 저장소가 없습니다. 새로 생성합니다..."
    aws ecr create-repository --repository-name $REPOSITORY_NAME --region $REGION
}

# 3. Docker 이미지 빌드
echo "🔨 Docker 이미지 빌드 중..."
docker build -t $REPOSITORY_NAME:$IMAGE_TAG -f docker/Dockerfile ..

# 4. ECR 태그 설정
echo "🏷️ ECR 태그 설정 중..."
docker tag $REPOSITORY_NAME:$IMAGE_TAG $ECR_URI/$REPOSITORY_NAME:$IMAGE_TAG

# 5. ECR에 푸시
echo "📤 ECR에 이미지 푸시 중..."
docker push $ECR_URI/$REPOSITORY_NAME:$IMAGE_TAG

echo "✅ 배포 완료!"
echo "📋 이미지 정보:"
echo "  - ECR URI: $ECR_URI/$REPOSITORY_NAME:$IMAGE_TAG"
echo "  - 로컬 태그: $REPOSITORY_NAME:$IMAGE_TAG"

# 6. 이미지 정보 출력
echo "📊 ECR 이미지 정보:"
aws ecr describe-images --repository-name $REPOSITORY_NAME --region $REGION --query 'imageDetails[?contains(imageTags, `'$IMAGE_TAG'`)].{Tag:imageTags[0],Size:imageSizeInBytes,PushedAt:imagePushedAt}' --output table 