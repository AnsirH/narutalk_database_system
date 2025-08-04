import boto3
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# AWS S3 또는 MinIO 설정 선택
def get_s3_config():
    """AWS S3 또는 MinIO 설정을 반환합니다."""
    # AWS S3 설정 주석 처리 - MinIO만 사용
    # try:
    #     # AWS S3 설정 시도
    #     aws_config = settings.get_aws_s3_config()
    #     logger.info("AWS S3 설정을 사용합니다.")
    #     return aws_config, "aws"
    # except Exception as e:
    #     logger.warning(f"AWS S3 설정 실패, MinIO 사용: {e}")
    # MinIO 설정 사용
    minio_config = settings.get_minio_config()
    logger.info("MinIO 설정을 사용합니다.")
    return minio_config, "minio"

# S3 클라이언트 생성
s3_config, storage_type = get_s3_config()
BUCKET_NAME = s3_config["bucket_name"]

# boto3 클라이언트 생성
# AWS S3 클라이언트 주석 처리 - MinIO만 사용
# if storage_type == "aws":
#     # AWS S3 클라이언트
#     s3_client = boto3.client(
#         "s3",
#         aws_access_key_id=s3_config["aws_access_key_id"],
#         aws_secret_access_key=s3_config["aws_secret_access_key"],
#         region_name=s3_config["region_name"]
#     )
# else:
# MinIO 클라이언트
s3_client = boto3.client(
    "s3",
    aws_access_key_id=s3_config["aws_access_key_id"],
    aws_secret_access_key=s3_config["aws_secret_access_key"],
    endpoint_url=s3_config["endpoint_url"],
    region_name=s3_config["region_name"]
)

def upload_file(file_bytes, filename, content_type):
    """파일을 S3에 업로드합니다."""
    try:
        # 버킷이 없으면 생성 (MinIO의 경우)
        if storage_type == "minio":
            try:
                s3_client.head_bucket(Bucket=BUCKET_NAME)
            except Exception:
                s3_client.create_bucket(Bucket=BUCKET_NAME)
        
        # 파일 업로드
        import io
        s3_client.upload_fileobj(
            io.BytesIO(file_bytes), 
            BUCKET_NAME, 
            filename, 
            ExtraArgs={"ContentType": content_type}
        )
        
        # URL 생성
        # AWS S3 URL 생성 주석 처리 - MinIO만 사용
        # if storage_type == "aws":
        #     url = f"https://{BUCKET_NAME}.s3.{s3_config['region_name']}.amazonaws.com/{filename}"
        # else:
        url = f"{s3_config['endpoint_url']}/{BUCKET_NAME}/{filename}"
        
        logger.info(f"파일 업로드 성공: {filename} -> {url}")
        return url
        
    except Exception as e:
        logger.error(f"파일 업로드 실패: {filename}, 오류: {str(e)}")
        raise

def delete_file_from_s3(file_name: str):
    """S3에서 파일을 삭제합니다."""
    try:
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=file_name)
        logger.info(f"파일 삭제 성공: {file_name}")
        return True
    except Exception as e:
        logger.error(f"파일 삭제 실패: {file_name}, 오류: {str(e)}")
        return False

def get_file_url(file_name: str):
    """파일의 URL을 반환합니다."""
    # AWS S3 URL 생성 주석 처리 - MinIO만 사용
    # if storage_type == "aws":
    #     return f"https://{BUCKET_NAME}.s3.{s3_config['region_name']}.amazonaws.com/{file_name}"
    # else:
    return f"{s3_config['endpoint_url']}/{BUCKET_NAME}/{file_name}"

def list_files(prefix: str = ""):
    """S3에서 파일 목록을 조회합니다."""
    try:
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
        files = []
        if 'Contents' in response:
            for obj in response['Contents']:
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified']
                })
        return files
    except Exception as e:
        logger.error(f"파일 목록 조회 실패: {str(e)}")
        return [] 