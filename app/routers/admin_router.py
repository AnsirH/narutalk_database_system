from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.employee import EmployeeCreate, EmployeeInfo
from app.services.user_service import get_employee_by_email, create_employee
from app.services.db import get_db
from app.models.employees import Employee
from sqlalchemy.exc import IntegrityError
from app.routers.user_router import get_current_admin_user
from app.services.opensearch_service import DOCUMENT_INDEX_NAME
from app.config import settings
from app.services.opensearch_client import opensearch_client


router = APIRouter()

@router.post("/register-employee", response_model=EmployeeInfo)
def register_employee(user: EmployeeCreate, db: Session = Depends(get_db), admin: EmployeeInfo = Depends(get_current_admin_user)):
    db_user = get_employee_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = create_employee(db, user)
    return EmployeeInfo.from_orm(new_user)

@router.post("/init-admin", response_model=EmployeeInfo)
def init_admin(user: EmployeeCreate, db: Session = Depends(get_db)):
    """
    최초 1회만 사용 가능한 관리자 계정 생성 API (인증 불필요)
    이미 관리자가 존재하면 400 에러 반환
    """
    # 1. 기존 관리자 확인 (soft delete 고려)
    existing_admin = db.query(Employee).filter(
        Employee.role == "admin",
        Employee.is_deleted == False
    ).first()
    if existing_admin:
        raise HTTPException(status_code=400, detail="관리자 계정이 이미 존재합니다.")
    
    # 2. 역할 검증
    if user.role != "admin":
        raise HTTPException(status_code=400, detail="role은 반드시 'admin'이어야 합니다.")
    
    # 3. 이메일 중복 체크
    existing_user = get_employee_by_email(db, email=user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="이메일이 이미 존재합니다.")
    
    # 4. 사용자명 중복 체크
    existing_username = db.query(Employee).filter(
        Employee.username == user.username,
        Employee.is_deleted == False
    ).first()
    if existing_username:
        raise HTTPException(status_code=400, detail="사용자명이 이미 존재합니다.")
    
    try:
        # 5. 관리자 계정 생성
        new_user = create_employee(db, user)
        return EmployeeInfo.from_orm(new_user)
    except IntegrityError as e:
        db.rollback()
        # 더 구체적인 오류 메시지 제공
        if "email" in str(e).lower():
            raise HTTPException(status_code=400, detail="이메일이 이미 존재합니다.")
        elif "username" in str(e).lower():
            raise HTTPException(status_code=400, detail="사용자명이 이미 존재합니다.")
        else:
            raise HTTPException(status_code=400, detail="데이터베이스 제약 조건 위반: " + str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"관리자 계정 생성 중 오류 발생: {str(e)}")



@router.delete("/cleanup-corrupted-documents")
def cleanup_corrupted_documents(admin: EmployeeInfo = Depends(get_current_admin_user)):
    """
    깨진 문서 데이터를 정리하는 관리자용 API입니다.
    OpenSearch에서 깨진 텍스트가 포함된 문서 청크들을 삭제합니다.
    """
    try:
        if not opensearch_client or not opensearch_client.client:
            raise HTTPException(status_code=500, detail="OpenSearch 클라이언트가 초기화되지 않았습니다.")
        
        # 깨진 텍스트 패턴을 찾아서 삭제
        corrupted_patterns = [
            "ߩ+)]N",  # 실제 결과에서 발견된 패턴
            "\\u6M~g~l",
            "zi'$&3",
            "xml]O0"
        ]
        
        deleted_count = 0
        
        for pattern in corrupted_patterns:
            try:
                # 깨진 패턴이 포함된 문서 검색
                query = {
                    "query": {
                        "wildcard": {
                            "content": f"*{pattern}*"
                        }
                    }
                }
                
                response = opensearch_client.client.search(
                    index=DOCUMENT_INDEX_NAME,
                    body=query,
                    size=100
                )
                
                # 검색된 문서들 삭제
                for hit in response["hits"]["hits"]:
                    doc_id = hit["_id"]
                    opensearch_client.client.delete(
                        index=DOCUMENT_INDEX_NAME,
                        id=doc_id
                    )
                    deleted_count += 1
                    
            except Exception as e:
                print(f"패턴 '{pattern}' 삭제 중 오류: {e}")
                continue
        
        return {
            "success": True,
            "message": f"깨진 문서 데이터 정리 완료: {deleted_count}개 청크 삭제됨",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"깨진 문서 정리 중 오류 발생: {str(e)}") 