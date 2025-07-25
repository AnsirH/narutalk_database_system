from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import List, Optional, Union, Dict
from datetime import datetime
from schemas.document import DocumentBase, DocumentInfo
from services.s3_service import upload_file, delete_file_from_s3
from services.postgres_service import save_document, get_documents, get_document_by_id, delete_document_from_postgres
from services.opensearch_service import index_document_chunks, delete_document_chunks_from_opensearch, DOCUMENT_INDEX_NAME

from services.document_analyzer import document_analyzer
from services.universal_table_processor import universal_table_processor
from routers.user_router import get_current_user, get_current_admin_user
from pydantic import BaseModel
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class TableUploadResult(BaseModel):
    doc_title: str
    doc_type: str
    uploader_id: int
    version: Optional[str]
    created_at: datetime
    message: str
    analysis: Optional[Dict] = None

def extract_text_and_table(file_bytes: bytes, filename: str, content_type: str):
    """
    파일 확장자에 따라 텍스트/테이블 데이터를 추출한다.
    Returns: (text, table_data, is_table_file)
    """
    file_extension = document_analyzer._get_file_extension(filename)
    is_table_file = file_extension in document_analyzer.supported_extensions["table"]
    text = ""
    table_data = []
    if is_table_file:
        try:
            import pandas as pd
            import io
            if filename.lower().endswith('.csv'):
                df = pd.read_csv(io.BytesIO(file_bytes))
            else:
                df = pd.read_excel(io.BytesIO(file_bytes))
            text = df.to_string()
            table_data = df.to_dict('records')
        except ImportError:
            logger.warning("pandas 라이브러리가 설치되지 않았습니다. 테이블 파일 내용을 추출할 수 없습니다.")
            raise HTTPException(status_code=500, detail="테이블 파일 처리를 위한 pandas 라이브러리가 필요합니다.")
        except Exception as e:
            logger.error(f"테이블 파일 텍스트 추출 실패: {e}")
            raise HTTPException(status_code=500, detail=f"테이블 파일 처리 중 오류가 발생했습니다: {str(e)}")
    else:
        if filename.lower().endswith('.txt'):
            text = file_bytes.decode("utf-8", errors="ignore")
        elif filename.lower().endswith('.docx'):
            try:
                from docx import Document
                import io
                doc = Document(io.BytesIO(file_bytes))
                text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            except ImportError:
                logger.warning("python-docx 라이브러리가 설치되지 않았습니다. DOCX 파일 내용을 추출할 수 없습니다.")
                text = ""
            except Exception as e:
                logger.error(f"DOCX 파일 텍스트 추출 실패: {e}")
                text = ""
        elif filename.lower().endswith('.pdf'):
            try:
                import PyPDF2
                import io
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            except ImportError:
                logger.warning("PyPDF2 라이브러리가 설치되지 않았습니다. PDF 파일 내용을 추출할 수 없습니다.")
                text = ""
            except Exception as e:
                logger.error(f"PDF 파일 텍스트 추출 실패: {e}")
                text = ""
    return text, table_data, is_table_file

@router.post("/documents/upload", response_model=Union[DocumentInfo, TableUploadResult])
def upload_document(file: UploadFile = File(...), doc_title: str = Form(...), uploader_id: int = Form(...), doc_type: str = Form(None), version: str = Form(None), user=Depends(get_current_user)):
    """
    문서를 업로드하고 자동으로 타입을 분석하여 저장합니다.
    """
    try:
        file_bytes = file.file.read()
        content_type = file.content_type
        text, table_data, is_table_file = extract_text_and_table(file_bytes, file.filename, content_type)
        
        # 테이블 문서 처리 - 범용 처리기 사용
        if is_table_file and table_data:
            logger.info(f"테이블 문서 처리 시작: {file.filename}")
            
            # 범용 테이블 처리기로 처리
            try:
                result = universal_table_processor.process_table_data(table_data)
                
                if result['success']:
                    logger.info(f"테이블 문서 처리 완료: {result['message']}")
                    return TableUploadResult(
                        doc_title=doc_title,
                        doc_type=result.get('analysis', {}).get('table_type', 'table_data'),
                        uploader_id=uploader_id,
                        version=version,
                        created_at=datetime.utcnow(),
                        message=result['message'],
                        analysis=result.get('analysis')
                    )
                else:
                    logger.error(f"테이블 문서 처리 실패: {result['message']}")
                    raise HTTPException(status_code=500, detail=f"테이블 문서 처리 중 오류가 발생했습니다: {result['message']}")
                    
            except Exception as e:
                logger.error(f"범용 테이블 처리기 실행 실패: {e}")
                raise HTTPException(status_code=500, detail=f"테이블 문서 처리 중 오류가 발생했습니다: {str(e)}")
        
        # 텍스트 문서 처리
        else:
            logger.info(f"텍스트 문서 처리 시작: {file.filename}")
            
            # 문서 타입 분석 (텍스트 문서용)
            analyzed_doc_type = document_analyzer.analyze_document(text, file.filename)
            logger.info(f"문서 분석 결과: {file.filename} -> {analyzed_doc_type}")
            
            # S3 업로드
            file_path = upload_file(file_bytes, file.filename, content_type)
            
            # 문서 메타데이터 저장
            meta = DocumentBase(
                doc_title=doc_title,
                doc_type=analyzed_doc_type,
                file_path=file_path,
                uploader_id=uploader_id,
                version=version,
                created_at=datetime.utcnow()
            )
            doc = save_document(meta)
            
            # OpenSearch 인덱싱 (텍스트 문서만)
            if file.filename.lower().endswith(('.txt', '.docx', '.pdf')):
                chunking_type = document_analyzer.get_chunking_type(analyzed_doc_type)
                index_document_chunks(
                    doc_id=doc.doc_id,
                    doc_title=doc_title,
                    file_name=file.filename,
                    text=text,
                    document_type=chunking_type
                )
                logger.info(f"텍스트 문서 업로드 완료: {doc.doc_id} (타입: {analyzed_doc_type}, 청킹: {chunking_type})")
            else:
                logger.info(f"문서 업로드 완료: {doc.doc_id} (타입: {analyzed_doc_type})")
            
            return DocumentInfo.model_validate(doc)
            
    except Exception as e:
        logger.error(f"문서 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail=f"문서 업로드 중 오류가 발생했습니다: {str(e)}")

@router.get("/documents/", response_model=List[DocumentInfo])
def list_documents(user=Depends(get_current_user)):
    docs = get_documents()
    return [DocumentInfo.model_validate(doc) for doc in docs]

@router.get("/documents/{doc_id}", response_model=DocumentInfo)
def get_document(doc_id: int, user=Depends(get_current_user)):
    doc = get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentInfo.model_validate(doc)

@router.delete("/documents/{doc_id}", response_model=DocumentInfo)
def delete_document(doc_id: int, admin=Depends(get_current_admin_user)):
    doc = get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    file_name = doc.file_path.split("/")[-1]
    delete_file_from_s3(file_name)
    delete_document_chunks_from_opensearch(DOCUMENT_INDEX_NAME, doc_id)
    deleted_doc = delete_document_from_postgres(doc_id)
    if not deleted_doc:
        raise HTTPException(status_code=500, detail="Failed to delete document from DB")
    return DocumentInfo.model_validate(deleted_doc) 