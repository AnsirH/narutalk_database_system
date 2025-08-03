"""
Text2SQL 기반 테이블 분류 서비스
LLM을 사용하여 테이블 데이터를 분석하고 적절한 데이터베이스 테이블에 분류합니다.
"""

import logging
import re
import json
from typing import List, Dict, Any, Optional, Callable
from contextlib import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
from decimal import Decimal

# 공통 OpenAI 서비스 import
from app.services.external.openai_service import openai_service
from app.services.utils.customer_utils import extract_address_from_name, extract_address_and_clean_name

# 모델 import
from app.models.employees import Employee
from app.models.employee_info import EmployeeInfo
from app.models.customers import Customer
from app.models.sales_records import SalesRecord
from app.models.products import Product
from app.models.interaction_logs import InteractionLog
from app.models.assignment_map import AssignmentMap
from app.models.documents import Document
from app.models.document_relations import DocumentRelation

logger = logging.getLogger(__name__)

class Text2SQLTableClassifier:
    """Text2SQL 기반 테이블 분류기"""
    
    def __init__(self, db_session_factory: Optional[Callable] = None):
        """초기화"""
        self.db_session_factory = db_session_factory
        
        # 데이터베이스 테이블 설명 (LLM 프롬프트용)
        self.table_descriptions = {
            'employee_info': {
                'description': '직원 인사 정보 (이름, 사번, 팀, 직급, 급여, 연락처 등)',
                'required_fields': ['name'],
                'optional_fields': ['employee_number', 'team', 'position', 'business_unit', 'branch', 'contact_number', 'base_salary', 'incentive_pay', 'avg_monthly_budget', 'latest_evaluation']
            },
            'customers': {
                'description': '고객(의료기관) 정보 (기관명, 주소, 환자수, 담당의사 등)',
                'required_fields': ['customer_name'],
                'optional_fields': ['address', 'doctor_name', 'total_patients']
            },
            'sales_records': {
                'description': '매출 기록 (매출액, 날짜, 고객, 제품, 담당자)',
                'required_fields': ['sale_amount', 'sale_date'],
                'optional_fields': ['employee_id', 'customer_id', 'product_id']
            },
            'products': {
                'description': '제품 정보 (제품명, 설명, 카테고리)',
                'required_fields': ['product_name'],
                'optional_fields': ['description', 'category']
            },
            'interaction_logs': {
                'description': '직원-고객 상호작용 기록 (상호작용 유형, 요약, 감정분석)',
                'required_fields': ['employee_id', 'customer_id'],
                'optional_fields': ['interaction_type', 'summary', 'sentiment', 'compliance_risk', 'interacted_at']
            },
            'assignment_map': {
                'description': '직원-고객 배정 관계 (담당자 정보)',
                'required_fields': ['employee_id', 'customer_id'],
                'optional_fields': []
            },
            'documents': {
                'description': '문서 메타데이터 (제목, 타입, 파일경로 등)',
                'required_fields': ['doc_title', 'uploader_id', 'file_path'],
                'optional_fields': ['doc_type', 'version']
            },
            'document_relations': {
                'description': '문서와 엔티티 간의 관계 (자동 분석 결과)',
                'required_fields': ['doc_id', 'related_entity_type', 'related_entity_id'],
                'optional_fields': ['confidence_score']
            }
        }
    
    @contextmanager
    def _get_db_session(self):
        """데이터베이스 세션 컨텍스트 매니저"""
        if not self.db_session_factory:
            logger.warning("DB 세션 팩토리가 설정되지 않음")
            yield None
            return
            
        session = self.db_session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def classify_table_with_text2sql(self, table_data: List[Dict[str, Any]], table_description: str = "") -> Dict[str, Any]:
        """
        Text2SQL을 사용하여 테이블 분류 및 SQL 생성
        """
        if not table_data:
            return {
                'success': False,
                'message': '테이블 데이터가 없습니다.',
                'target_table': None,
                'confidence': 0.0
            }
        
        try:
            # 1. 테이블 구조 분석
            columns = list(table_data[0].keys()) if table_data else []
            sample_data = table_data[:3] if len(table_data) >= 3 else table_data
            
            # 2. Text2SQL 분류 수행
            classification_result = self._perform_text2sql_classification(
                columns=columns,
                sample_data=sample_data,
                table_description=table_description
            )
            
            # 3. 결과 검증 및 데이터 삽입
            if classification_result['success'] and classification_result['confidence'] > 0.5:
                target_table = classification_result['target_table']
                column_mapping = classification_result['column_mapping']
                
                # 데이터 삽입
                insertion_result = self._insert_data_to_target_table(
                    table_data=table_data,
                    target_table=target_table,
                    column_mapping=column_mapping
                )
                
                if insertion_result['success']:
                    return {
                        'success': True,
                        'target_table': target_table,
                        'confidence': classification_result['confidence'],
                        'reasoning': classification_result['reasoning'],
                        'column_mapping': column_mapping,
                        'processed_count': insertion_result['processed_count'],
                        'message': f"Text2SQL 분류 완료: {target_table} 테이블에 {insertion_result['processed_count']}건 저장"
                    }
                else:
                    return {
                        'success': False,
                        'message': f"데이터 삽입 실패: {insertion_result['message']}",
                        'target_table': target_table,
                        'confidence': classification_result['confidence']
                    }
            else:
                return {
                    'success': False,
                    'message': f"Text2SQL 분류 실패: 신뢰도 {classification_result['confidence']:.2f}",
                    'target_table': classification_result.get('target_table'),
                    'confidence': classification_result['confidence']
                }
                
        except Exception as e:
            logger.error(f"Text2SQL 분류 중 오류: {e}")
            return {
                'success': False,
                'message': f'Text2SQL 분류 중 오류 발생: {str(e)}',
                'target_table': None,
                'confidence': 0.0
            }
    
    def _perform_text2sql_classification(self, columns: List[str], sample_data: List[Dict], table_description: str) -> Dict[str, Any]:
        """
        LLM을 사용한 Text2SQL 분류 수행
        """
        if not openai_service.is_available():
            logger.error("OpenAI 클라이언트가 사용 불가능합니다.")
            return {
                'success': False,
                'message': 'OpenAI 클라이언트가 초기화되지 않았습니다.',
                'target_table': None,
                'confidence': 0.0
            }
        
        try:
            # LLM 기반 분류 수행
            llm_result = self._perform_llm_classification(columns, sample_data, table_description)
            
            if llm_result['success']:
                return llm_result
            else:
                logger.error(f"LLM 분류 실패: {llm_result['message']}")
                return llm_result
                
        except Exception as e:
            logger.error(f"LLM 분류 중 오류: {e}")
            return {
                'success': False,
                'message': f'LLM 분류 중 오류: {str(e)}',
                'target_table': None,
                'confidence': 0.0
            }
    
    def _perform_llm_classification(self, columns: List[str], sample_data: List[Dict], table_description: str) -> Dict[str, Any]:
        """LLM을 사용한 테이블 분류"""
        try:
            # LLM 프롬프트 생성
            prompt = self._create_llm_classification_prompt(columns, sample_data, table_description)
            
            # OpenAI API 호출
            messages = [
                {"role": "system", "content": "당신은 Excel 테이블 데이터를 분석하여 적절한 데이터베이스 테이블을 선택하고 컬럼 매핑을 제공하는 전문가입니다."},
                {"role": "user", "content": prompt}
            ]
            
            result = openai_service.create_json_completion(
                messages=messages,
                model="gpt-3.5-turbo",
                max_tokens=1000,
                temperature=0.1
            )
            
            if not result:
                return {
                    'success': False,
                    'message': 'LLM 응답을 받지 못했습니다.',
                    'target_table': None,
                    'confidence': 0.0
                }
            
            # 기본 검증
            if 'target_table' not in result or 'column_mapping' not in result:
                return {
                    'success': False,
                    'message': 'LLM 응답 형식이 올바르지 않습니다.',
                    'target_table': None,
                    'confidence': 0.0
                }
            
            # 컬럼 매핑 정규화 (안전한 방식)
            normalized_mapping = {}
            for key, value in result['column_mapping'].items():
                try:
                    str_key = str(key)
                    str_value = str(value)
                    if str_value in columns:  # 실제 컬럼이 존재하는지 확인
                        normalized_mapping[str_key] = str_value
                except (TypeError, AttributeError, ValueError):
                    continue
            
            logger.info(f"LLM 분류 완료: {result.get('target_table')} (신뢰도: {result.get('confidence', 0)})")
            logger.info(f"LLM 컬럼 매핑 결과: {normalized_mapping}")
            
            return {
                'success': True,
                'target_table': result.get('target_table'),
                'confidence': result.get('confidence', 0.0),
                'reasoning': result.get('reasoning', ''),
                'column_mapping': normalized_mapping
            }
            
        except Exception as e:
            logger.error(f"LLM 분류 중 오류: {e}")
            return {
                'success': False,
                'message': f'LLM 분류 중 오류: {str(e)}',
                'target_table': None,
                'confidence': 0.0
            }
    
    def _create_llm_classification_prompt(self, columns: List[str], sample_data: List[Dict], table_description: str) -> str:
        """LLM 분류를 위한 프롬프트 생성"""
        return f"""
다음 Excel 테이블 데이터를 분석하여 가장 적합한 데이터베이스 테이블을 선택하고 컬럼 매핑을 제공하세요:

컬럼명: {columns}
샘플 데이터: {sample_data[:3]}
테이블 설명: {table_description}

사용 가능한 테이블:
- employee_info: 직원 인사 정보 (name, employee_number, team, position, business_unit, branch, contact_number, base_salary, incentive_pay, avg_monthly_budget, latest_evaluation)
- customers: 고객 정보 (customer_name, address, doctor_name, total_patients)
- sales_records: 매출 기록 (employee_name, employee_number, customer_name, product_name, sale_amount, sale_date) - 이름과 사번으로 ID를 자동 매핑
- products: 제품 정보 (product_name, description, category, is_active)
- interaction_logs: 상호작용 기록 (employee_id, customer_id, interaction_type, summary, sentiment, compliance_risk, interacted_at)
- assignment_map: 배정 관계 (employee_id, customer_id)
- documents: 문서 메타데이터 (doc_title, uploader_id, file_path, doc_type, version)
- document_relations: 문서 관계 (doc_id, related_entity_type, related_entity_id, confidence_score)

분석 기준:
1. 컬럼명의 의미와 데이터베이스 필드의 의미가 일치하는지 확인
2. 샘플 데이터의 패턴이 해당 테이블의 데이터 패턴과 일치하는지 확인
3. 필수 필드가 모두 매핑되는지 확인
4. 가장 높은 신뢰도로 매핑할 수 있는 테이블을 선택

특별 주의사항:
- employee_info 테이블: 
  * employee_number(사번)은 동명이인 구분을 위해 사용, 고유값으로 관리
  * 사번 컬럼이 있으면 반드시 employee_number로 매핑
  * 사번이 없으면 이름만으로 처리
- customers 테이블: customer_grade와 notes는 시스템에서 관리하므로 매핑하지 않음
- address 필드: customer_name에서 주소 정보를 추출하거나 별도 컬럼에서 매핑 가능
- customer_type은 사용하지 않음
- customer_name과 address의 조합으로 중복 체크 (같은 지역의 같은 이름은 중복 불가)
- 각 테이블의 필드만 해당 테이블에 매핑 (employee_info 필드를 customers에 매핑하지 않음)
- sales_records 테이블: 
  * 월별 매출 데이터 감지: 컬럼명이 202312, 202401 등 YYYYMM 형태인 경우 월별 매출 데이터로 분류
  * LLM은 기본 컬럼만 매핑 (담당자, 사번, ID, 품목 등)
  * 월별 컬럼(202312, 202401 등)은 매핑하지 말 것 - 시스템에서 자동 처리
  * 사번 컬럼이 있으면 employee_number로 매핑 (동명이인 구분용)
  * sale_amount와 sale_date는 LLM이 매핑하지 않음 (시스템에서 자동 변환)
  * 월별 데이터 변환: 각 행을 12개의 개별 매출 기록으로 분할하여 처리
  * 합계 행 처리: 품목이나 거래처에 "합계"가 포함된 행은 월별 총합이므로 개별 매출 기록으로 변환하지 않음
  * 고객명 컬럼: "ID" 컬럼이 실제로는 고객명인 경우가 많음, 주의해서 매핑

중요한 매핑 규칙:
1. 직원 관련 테이블(employee_info, sales_records, assignment_map, interaction_logs)에서는 반드시 employee_number(사번)을 매핑해야 함
2. sales_records 테이블에서 employee_name 컬럼이 있으면 반드시 employee_number로도 매핑해야 함
3. 사번이 없는 경우 시스템에서 직원을 찾을 수 없어 데이터 처리가 실패함
4. 직원명 컬럼이 있으면 employee_name으로 매핑하고, 추가로 employee_number 컬럼이 있으면 그것도 매핑해야 함

JSON 형식으로 응답:
{{
    "target_table": "테이블명",
    "confidence": 0.95,
    "reasoning": "분류 이유",
    "column_mapping": {{
        "데이터베이스필드": "Excel컬럼명"
    }}
}}
"""
    

    
    def _insert_data_to_target_table(self, table_data: List[Dict[str, Any]], target_table: str, column_mapping: Dict[str, str]) -> Dict[str, Any]:
        """대상 테이블에 데이터 삽입"""
        try:
            if target_table == 'employee_info':
                return self._execute_with_session(lambda session: self._insert_employee_info(table_data, session, column_mapping))
            elif target_table == 'customers':
                return self._execute_with_session(lambda session: self._insert_customers(table_data, session, column_mapping))
            elif target_table == 'sales_records':
                return self._execute_with_session(lambda session: self._insert_sales_records(table_data, session, column_mapping))
            elif target_table == 'products':
                return self._execute_with_session(lambda session: self._insert_products(table_data, session, column_mapping))
            elif target_table == 'interaction_logs':
                return self._execute_with_session(lambda session: self._insert_interaction_logs(table_data, session, column_mapping))
            elif target_table == 'assignment_map':
                return self._execute_with_session(lambda session: self._insert_assignment_map(table_data, session, column_mapping))
            elif target_table == 'documents':
                return self._execute_with_session(lambda session: self._insert_documents(table_data, session, column_mapping))
            elif target_table == 'document_relations':
                return self._execute_with_session(lambda session: self._insert_document_relations(table_data, session, column_mapping))
            else:
                return {
                    'success': False,
                    'message': f'지원하지 않는 테이블 타입: {target_table}',
                    'processed_count': 0
                }
        except Exception as e:
            logger.error(f"{target_table} 테이블 데이터 삽입 중 오류: {e}")
            return {
                'success': False,
                'message': f'데이터 삽입 중 오류 발생: {str(e)}',
                'processed_count': 0
            }
    
    def _execute_with_session(self, func: Callable[[Session], Dict[str, Any]]) -> Dict[str, Any]:
        """세션을 사용하여 함수 실행"""
        try:
            with self._get_db_session() as session:
                return func(session)
        except SQLAlchemyError as e:
            logger.error(f"DB 오류: {e}")
            return {
                'success': False,
                'message': f'데이터베이스 오류: {str(e)}',
                'processed_count': 0
            }
        except Exception as e:
            logger.error(f"처리 중 예상치 못한 오류: {e}")
            return {
                'success': False,
                'message': f'처리 중 오류 발생: {str(e)}',
                'processed_count': 0
            }
    
    # === 데이터 삽입 메서드들 ===
    
    def _insert_employee_info(self, table_data: List[Dict[str, Any]], session: Session, column_mapping: Dict[str, str]) -> Dict[str, Any]:
        """직원 인사 정보 삽입 (사번으로만 조회)"""
        processed_count = 0
        skipped_count = 0
        
        try:
            for row in table_data:
                # 사번 추출 (필수)
                employee_number = None
                if 'employee_number' in column_mapping and row.get(column_mapping['employee_number']):
                    employee_number = str(row[column_mapping['employee_number']]).strip()
                
                if not employee_number or employee_number == 'nan':
                    logger.warning(f"사번이 없거나 유효하지 않은 행 건너뜀: {row}")
                    skipped_count += 1
                    continue
                
                # 이름 추출
                name = str(row[column_mapping['name']]).strip() if 'name' in column_mapping and row.get(column_mapping['name']) else None
                
                if not name:
                    logger.warning(f"이름을 찾을 수 없는 행 건너뜀: {row}")
                    skipped_count += 1
                    continue
                
                # 사번으로만 기존 직원 확인
                existing_employee = session.query(EmployeeInfo).filter(
                    EmployeeInfo.employee_number == employee_number
                ).first()
                
                if existing_employee:
                    # 업데이트
                    self._update_employee_info(existing_employee, row, column_mapping)
                    logger.info(f"직원 정보 업데이트: {name} (사번: {employee_number})")
                else:
                    # 새 직원 등록
                    new_employee = self._create_employee_info(row, column_mapping)
                    session.add(new_employee)
                    logger.info(f"새 직원 등록: {name} (사번: {employee_number})")
                
                processed_count += 1
            
            return {
                'success': True,
                'message': f'직원 인사 정보 삽입 완료: {processed_count}명 처리됨, {skipped_count}명 건너뜀',
                'processed_count': processed_count,
                'skipped_count': skipped_count
            }
            
        except SQLAlchemyError as e:
            logger.error(f"직원 인사 정보 삽입 중 DB 오류: {e}")
            raise
    
    def _create_employee_info(self, row: Dict[str, Any], column_mapping: Dict[str, str]) -> EmployeeInfo:
        """직원 정보 객체 생성"""
        employee_data = {}
        
        # 매핑된 컬럼에서 데이터 추출
        for db_field, source_column in column_mapping.items():
            if source_column in row and row[source_column] is not None:
                value = str(row[source_column]).strip()
                
                # 숫자 필드 처리
                if db_field in ['base_salary', 'incentive_pay', 'avg_monthly_budget']:
                    try:
                        value = int(str(value).replace(',', '').replace('₩', '').strip())
                    except:
                        value = None
                
                employee_data[db_field] = value
        
        return EmployeeInfo(**employee_data)
    
    def _update_employee_info(self, employee: EmployeeInfo, row: Dict[str, Any], column_mapping: Dict[str, str]):
        """직원 정보 업데이트"""
        for db_field, source_column in column_mapping.items():
            if source_column in row and row[source_column] is not None:
                value = str(row[source_column]).strip()
                
                # 숫자 필드 처리
                if db_field in ['base_salary', 'incentive_pay', 'avg_monthly_budget']:
                    try:
                        value = int(str(value).replace(',', '').replace('₩', '').strip())
                    except:
                        value = None
                
                setattr(employee, db_field, value)
    
    def _insert_customers(self, table_data: List[Dict[str, Any]], session: Session, column_mapping: Dict[str, str]) -> Dict[str, Any]:
        """고객 데이터 삽입"""
        processed_count = 0
        skipped_count = 0
        
        # 중복 제거를 위한 메모리 추적
        processed_customers = set()  # (customer_name, address) 조합 추적
        customer_updates = {}  # 업데이트할 고객 정보 저장
        
        try:
            # 1단계: 중복 제거 및 데이터 정리
            unique_customers = []
            for row in table_data:
                # 고객명 추출
                customer_name = str(row[column_mapping['customer_name']]).strip() if 'customer_name' in column_mapping and row.get(column_mapping['customer_name']) else None
                
                if not customer_name:
                    logger.warning(f"고객명을 찾을 수 없는 행 건너뜀: {row}")
                    continue
                
                # 임시 고객 객체 생성하여 address 추출
                temp_customer = self._create_customer(row, column_mapping)
                address = temp_customer.address
                
                # 중복 키 생성
                customer_key = (customer_name, address)
                
                if customer_key in processed_customers:
                    # 중복된 고객 - 업데이트 정보만 저장
                    if customer_key not in customer_updates:
                        customer_updates[customer_key] = []
                    customer_updates[customer_key].append(row)
                    skipped_count += 1
                    logger.info(f"중복 고객 건너뜀: {customer_name} ({address})")
                else:
                    # 새로운 고객
                    processed_customers.add(customer_key)
                    unique_customers.append((customer_key, row))
            
            # 2단계: DB에서 기존 고객 확인 및 처리
            for customer_key, row in unique_customers:
                customer_name, address = customer_key
                
                # DB에서 기존 고객 확인
                existing_customer = session.query(Customer).filter(
                    Customer.customer_name == customer_name,
                    Customer.address == address
                ).first()
                
                if existing_customer:
                    # 기존 고객 업데이트
                    self._update_customer(existing_customer, row, column_mapping)
                    logger.info(f"고객 정보 업데이트: {customer_name} ({address})")
                else:
                    # 새 고객 등록
                    new_customer = self._create_customer(row, column_mapping)
                    session.add(new_customer)
                    logger.info(f"새 고객 등록: {customer_name} ({address})")
                
                processed_count += 1
            
            return {
                'success': True,
                'message': f'고객 정보 삽입 완료: {processed_count}명 처리됨, {skipped_count}명 중복 건너뜀',
                'processed_count': processed_count,
                'skipped_count': skipped_count
            }
            
        except SQLAlchemyError as e:
            logger.error(f"고객 정보 삽입 중 DB 오류: {e}")
            raise
    
    def _create_customer(self, row: Dict[str, Any], column_mapping: Dict[str, str]) -> Customer:
        """고객 객체 생성"""
        customer_data = {}
        
        # Customer 모델의 유효한 필드만 추출
        valid_customer_fields = ['customer_name', 'address', 'doctor_name', 'total_patients']
        
        for db_field, source_column in column_mapping.items():
            if db_field in valid_customer_fields and source_column in row and row[source_column] is not None:
                value = str(row[source_column]).strip()
                
                # 숫자 필드 처리
                if db_field == 'total_patients':
                    try:
                        value = int(str(value).replace(',', '').strip())
                    except:
                        value = None
                
                customer_data[db_field] = value
        
        # address 필드 특별 처리: 매핑된 address가 없으면 customer_name에서 주소 추출
        if 'address' not in customer_data or not customer_data['address']:
            customer_name = customer_data.get('customer_name', '')
            if customer_name:
                # customer_name에서 주소 추출하고 깔끔한 이름으로 정리
                clean_name, address = self._extract_address_and_clean_name(customer_name)  # (이름, 주소) 순서로 받기
                if address:
                    customer_data['address'] = address
                    customer_data['customer_name'] = clean_name  # 주소 부분 제거된 깔끔한 이름
                    # 자동 추출된 address를 column_mapping에 추가 (LLM 응답에 포함되도록)
                    if 'address' not in column_mapping:
                        column_mapping['address'] = 'customer_name(추출)'
        
        return Customer(**customer_data)
    

    
    def _update_customer(self, customer: Customer, row: Dict[str, Any], column_mapping: Dict[str, str]):
        """고객 정보 업데이트"""
        for db_field, source_column in column_mapping.items():
            if source_column in row and row[source_column] is not None:
                value = str(row[source_column]).strip()
                
                # 숫자 필드 처리
                if db_field == 'total_patients':
                    try:
                        value = int(str(value).replace(',', '').strip())
                    except:
                        value = None
                
                setattr(customer, db_field, value)
        
        # address 필드 특별 처리: 매핑된 address가 없으면 customer_name에서 주소 추출
        if not customer.address:
            customer_name = customer.customer_name or ''
            if customer_name:
                clean_name, address = extract_address_and_clean_name(customer_name)
                if address:
                    customer.address = address
                    customer.customer_name = clean_name  # 주소 부분 제거된 깔끔한 이름
                    # 자동 추출된 address를 column_mapping에 추가 (LLM 응답에 포함되도록)
                    if 'address' not in column_mapping:
                        column_mapping['address'] = 'customer_name(추출)'
    
    def _insert_sales_records(self, table_data: List[Dict[str, Any]], session: Session, column_mapping: Dict[str, str]) -> Dict[str, Any]:
        """매출 데이터 삽입"""
        processed_count = 0
        skipped_count = 0
        
        try:
            # 월별 매출 데이터인지 확인
            is_monthly_data = self._is_monthly_sales_data(column_mapping)
            
            # 원본 테이블 데이터에서도 월별 컬럼 확인 (백업)
            if not is_monthly_data and table_data:
                import re
                sample_row = table_data[0]
                monthly_columns = [col for col in sample_row.keys() if re.match(r'^\d{6}$', str(col))]
                is_monthly_data = len(monthly_columns) >= 10
            
            if is_monthly_data:
                # 월별 데이터를 개별 매출 기록으로 변환
                transformed_data = self._transform_monthly_sales_data(table_data, column_mapping)
                logger.info(f"월별 매출 데이터 변환: {len(table_data)}행 → {len(transformed_data)}개 매출 기록")
                
                table_data = transformed_data
                column_mapping = self._get_standard_sales_mapping()  # 표준 매핑 사용
            
            for row in table_data:
                # 매출 금액 추출
                sale_amount = None
                if 'sale_amount' in column_mapping and row.get(column_mapping['sale_amount']):
                    try:
                        sale_amount = float(str(row[column_mapping['sale_amount']]).replace(',', '').strip())
                    except:
                        pass
                
                if sale_amount is None or sale_amount == 0:
                    logger.warning(f"매출 금액을 찾을 수 없는 행 건너뜀: {row}")
                    skipped_count += 1
                    continue
                
                # 날짜 추출
                sale_date = None
                if 'sale_date' in column_mapping and row.get(column_mapping['sale_date']):
                    sale_date = self._parse_date(str(row[column_mapping['sale_date']]))
                
                if not sale_date:
                    logger.warning(f"날짜를 찾을 수 없는 행 건너뜀: {row}")
                    skipped_count += 1
                    continue
                
                # 직원 ID 찾기 (사번으로만 조회)
                employee_id = None
                employee_name = ""
                
                # 사번으로만 찾기
                if 'employee_number' in column_mapping and row.get(column_mapping['employee_number']):
                    employee_number = str(row[column_mapping['employee_number']]).strip()
                    if employee_number and employee_number != 'nan':
                        # 사번으로 employee_info에서 찾기
                        employee_info = session.query(EmployeeInfo).filter(
                            EmployeeInfo.employee_number == employee_number
                        ).first()
                        if employee_info and employee_info.employee_info_id:
                            employee_id = employee_info.employee_info_id
                            employee_name = employee_info.name
                            logger.info(f"✅ 사번으로 직원 조회 성공: {employee_name} (사번: {employee_number}, ID: {employee_id})")
                        else:
                            logger.warning(f"사번으로 직원을 찾을 수 없음: {employee_number}")
                    else:
                        logger.warning(f"유효하지 않은 사번: {employee_number}")
                else:
                    # 사번 컬럼이 매핑에 없거나 실제 데이터에 없는 경우
                    if 'employee_number' in column_mapping:
                        mapped_column = column_mapping['employee_number']
                        logger.warning(f"사번 컬럼 '{mapped_column}'이 실제 데이터에 없음: {column_mapping}")
                    else:
                        logger.warning(f"사번 컬럼 매핑 없음: {column_mapping}")
                
                # 사번이 없거나 직원을 찾을 수 없는 경우 해당 행 건너뛰기
                if not employee_id:
                    logger.warning(f"직원 ID를 찾을 수 없는 행 건너뜀: {row}")
                    skipped_count += 1
                    continue
                
                # 고객 ID 찾기 (개선된 로직)
                customer_id = self._get_or_create_customer_id(session, row, column_mapping)
                if not customer_id:
                    logger.warning(f"고객 ID를 찾을 수 없는 행 건너뜀: {row}")
                    skipped_count += 1
                    continue
                
                # 제품 ID 찾기 (개선된 로직)
                product_id = self._get_or_create_product_id(session, row, column_mapping)
                if not product_id:
                    logger.warning(f"제품 ID를 찾을 수 없는 행 건너뜀: {row}")
                    skipped_count += 1
                    continue
                
                # ID를 찾지 못한 경우 해당 레코드 건너뛰기
                if not employee_id:
                    logger.warning(f"직원 ID를 찾을 수 없는 행 건너뜀: {row}")
                    skipped_count += 1
                    continue
                
                if not product_id:
                    logger.warning(f"제품 ID를 찾을 수 없는 행 건너뜀: {row}")
                    skipped_count += 1
                    continue
                
                # 매출 기록 생성
                new_sales_record = SalesRecord(
                    employee_id=employee_id,
                    customer_id=customer_id,
                    product_id=product_id,
                    sale_amount=Decimal(str(sale_amount)),
                    sale_date=sale_date
                )
                session.add(new_sales_record)
                processed_count += 1
            
            session.commit()
            
            return {
                'success': True,
                'message': f'매출 기록 삽입 완료: {processed_count}건 처리됨, {skipped_count}건 건너뜀',
                'processed_count': processed_count,
                'skipped_count': skipped_count
            }
            
        except SQLAlchemyError as e:
            logger.error(f"매출 기록 삽입 중 DB 오류: {e}")
            raise

    def _get_or_create_customer_id(self, session: Session, row: Dict[str, Any], column_mapping: Dict[str, str]) -> Optional[int]:
        """고객 ID를 안전하게 가져오거나 생성 (고객명+주소로 정확히 특정)"""
        if 'customer_name' not in column_mapping or not row.get(column_mapping['customer_name']):
            return None
            
        customer_name = str(row[column_mapping['customer_name']]).strip()
        logger.info(f"🔍 고객 조회 시작: 원본 고객명 = '{customer_name}'")
        
        # 고객명에서 주소 추출
        parsed_customer_name, parsed_address = self._extract_address_and_clean_name(customer_name)
        logger.info(f"🔍 파싱 결과: 고객명 = '{parsed_customer_name}', 주소 = '{parsed_address}'")
        
        # 고객명과 주소로 정확히 조회
        logger.info(f"🔍 고객명+주소로 정확히 조회 - 고객명='{parsed_customer_name}', 주소='{parsed_address}'")
        
        if parsed_address:
            # 주소가 있는 경우: 고객명+주소로 정확히 조회
            customer = session.query(Customer).filter(
                Customer.customer_name == parsed_customer_name,
                Customer.address == parsed_address
            ).first()
        else:
            # 주소가 없는 경우: 고객명으로만 조회
            customer = session.query(Customer).filter(
                Customer.customer_name == parsed_customer_name
            ).first()
        
        if customer:
            logger.info(f"✅ 고객 조회 성공: 고객 ID = {customer.customer_id}, 이름 = '{customer.customer_name}', 주소 = '{customer.address}'")
            return customer.customer_id
        else:
            logger.warning(f"❌ 고객 조회 실패: '{parsed_customer_name}' (주소: '{parsed_address}') 고객을 찾을 수 없음")
        
        # 고객이 없으면 자동 생성 (안전한 방식)
        logger.info(f"🔍 새 고객 생성 시도 - 고객명='{parsed_customer_name}', 주소='{parsed_address}'")
        
        # 고객 생성 전에 한 번 더 확인 (동시성 문제 방지)
        if parsed_address:
            customer = session.query(Customer).filter(
                Customer.customer_name == parsed_customer_name,
                Customer.address == parsed_address
            ).first()
        else:
            customer = session.query(Customer).filter(
                Customer.customer_name == parsed_customer_name
            ).first()
        
        if customer:
            logger.info(f"✅ 동시성 체크: 기존 고객 발견 - 고객 ID = {customer.customer_id}")
            return customer.customer_id
        
        # 새 고객 생성 시도
        try:
            new_customer = self._create_customer(row, column_mapping)
            logger.info(f"🔍 생성할 고객 정보: 이름='{new_customer.customer_name}', 주소='{new_customer.address}'")
            session.add(new_customer)
            session.flush()  # ID 생성
            customer_id = new_customer.customer_id
            logger.info(f"✅ 새 고객 자동 생성: '{new_customer.customer_name}' (ID: {customer_id})")
            return customer_id
            
        except Exception as e:
            # 중복 제약 조건 위반 시 기존 고객 찾기
            if "duplicate key value violates unique constraint" in str(e) or "unique constraint" in str(e).lower():
                logger.warning(f"⚠️ 고객 중복 발견, 기존 고객 찾기: '{customer_name}'")
                
                # 세션 롤백 후 재조회
                session.rollback()
                
                # 다시 조회 시도
                if parsed_address:
                    customer = session.query(Customer).filter(
                        Customer.customer_name == parsed_customer_name,
                        Customer.address == parsed_address
                    ).first()
                else:
                    customer = session.query(Customer).filter(
                        Customer.customer_name == parsed_customer_name
                    ).first()
                
                if customer:
                    logger.info(f"✅ 중복 고객 사용: '{customer.customer_name}' (ID: {customer.customer_id})")
                    return customer.customer_id
                else:
                    logger.error(f"❌ 중복 고객을 찾을 수 없음: '{customer_name}'")
                    return None
            else:
                logger.error(f"❌ 고객 생성 중 예상치 못한 오류: {e}")
                session.rollback()
                return None

    def _get_or_create_product_id(self, session: Session, row: Dict[str, Any], column_mapping: Dict[str, str]) -> Optional[int]:
        """제품 ID를 안전하게 가져오거나 생성 (정확한 제품명으로만 조회)"""
        if 'product_name' not in column_mapping or not row.get(column_mapping['product_name']):
            return None
            
        product_name = str(row[column_mapping['product_name']]).strip()
        logger.info(f"🔍 제품 조회 시작: 원본 제품명 = '{product_name}'")
        
        # 제품명으로 조회
        logger.info(f"🔍 1단계: 제품명으로 조회 시도 - '{product_name}'")
        product = session.query(Product).filter(
            Product.product_name == product_name
        ).first()
        
        if product:
            logger.info(f"✅ 제품 조회 성공: 제품 ID = {product.product_id}, 이름 = '{product.product_name}'")
            return product.product_id
        else:
            logger.warning(f"❌ 제품 조회 실패: '{product_name}' 제품을 찾을 수 없음")
        
        # 제품이 없으면 자동 생성 (안전한 방식)
        logger.info(f"🔍 새 제품 생성 시도 - 제품명='{product_name}'")
        
        # 제품 생성 전에 한 번 더 확인 (동시성 문제 방지)
        product = session.query(Product).filter(
            Product.product_name == product_name
        ).first()
        
        if product:
            logger.info(f"✅ 동시성 체크: 기존 제품 발견 - 제품 ID = {product.product_id}")
            return product.product_id
        
        # 새 제품 생성 시도
        try:
            new_product = self._create_product(row, column_mapping)
            logger.info(f"🔍 생성할 제품 정보: 이름='{new_product.product_name}'")
            session.add(new_product)
            session.flush()  # ID 생성
            product_id = new_product.product_id
            logger.info(f"✅ 새 제품 자동 생성: '{new_product.product_name}' (ID: {product_id})")
            return product_id
            
        except Exception as e:
            # 중복 제약 조건 위반 시 기존 제품 찾기
            if "duplicate key value violates unique constraint" in str(e) or "unique constraint" in str(e).lower():
                logger.warning(f"⚠️ 제품 중복 발견, 기존 제품 찾기: '{product_name}'")
                
                # 세션 롤백 후 재조회
                session.rollback()
                
                # 다시 조회 시도
                product = session.query(Product).filter(
                    Product.product_name == product_name
                ).first()
                
                if product:
                    logger.info(f"✅ 중복 제품 사용: '{product.product_name}' (ID: {product.product_id})")
                    return product.product_id
                else:
                    logger.error(f"❌ 중복 제품을 찾을 수 없음: '{product_name}'")
                    return None
            else:
                logger.error(f"❌ 제품 생성 중 예상치 못한 오류: {e}")
                session.rollback()
                return None
    
    def _insert_products(self, table_data: List[Dict[str, Any]], session: Session, column_mapping: Dict[str, str]) -> Dict[str, Any]:
        """제품 데이터 삽입"""
        processed_count = 0
        skipped_count = 0
        
        try:
            for row in table_data:
                # 제품명 추출
                product_name = str(row[column_mapping['product_name']]).strip() if 'product_name' in column_mapping and row.get(column_mapping['product_name']) else None
                
                if not product_name:
                    logger.warning(f"제품명을 찾을 수 없는 행 건너뜀: {row}")
                    continue
                
                # 기존 제품 확인
                existing_product = session.query(Product).filter(
                    Product.product_name == product_name
                ).first()
                
                if existing_product:
                    # 업데이트
                    self._update_product(existing_product, row, column_mapping)
                    logger.info(f"제품 정보 업데이트: {product_name}")
                else:
                    # 새 제품 등록
                    new_product = self._create_product(row, column_mapping)
                    session.add(new_product)
                    logger.info(f"새 제품 등록: {product_name}")
                
                processed_count += 1
            
            return {
                'success': True,
                'message': f'제품 정보 삽입 완료: {processed_count}건 처리됨, {skipped_count}건 중복 건너뜀',
                'processed_count': processed_count,
                'skipped_count': skipped_count
            }
            
        except SQLAlchemyError as e:
            logger.error(f"제품 정보 삽입 중 DB 오류: {e}")
            raise
    
    def _create_product(self, row: Dict[str, Any], column_mapping: Dict[str, str]) -> Product:
        """제품 객체 생성"""
        product_data = {}
        
        # Product 모델의 유효한 필드만 추출
        valid_product_fields = ['product_name', 'description', 'category', 'is_active']
        
        for db_field, source_column in column_mapping.items():
            if db_field in valid_product_fields and source_column in row and row[source_column] is not None:
                value = str(row[source_column]).strip()
                
                # Boolean 필드 처리
                if db_field == 'is_active':
                    try:
                        value = bool(value.lower() in ['true', '1', 'yes', '활성', '활성화'])
                    except:
                        value = True
                
                product_data[db_field] = value
        
        return Product(**product_data)
    
    def _update_product(self, product: Product, row: Dict[str, Any], column_mapping: Dict[str, str]):
        """제품 정보 업데이트"""
        for db_field, source_column in column_mapping.items():
            if source_column in row and row[source_column] is not None:
                value = str(row[source_column]).strip()
                setattr(product, db_field, value)
    
    def _insert_interaction_logs(self, table_data: List[Dict[str, Any]], session: Session, column_mapping: Dict[str, str]) -> Dict[str, Any]:
        """상호작용 로그 삽입"""
        processed_count = 0
        
        try:
            for row in table_data:
                # 날짜 추출
                interaction_date = None
                if 'interacted_at' in column_mapping and row.get(column_mapping['interacted_at']):
                    interaction_date = self._parse_date(str(row[column_mapping['interacted_at']]))
                
                if not interaction_date:
                    interaction_date = datetime.now(timezone.utc)
                
                # 고객 ID 찾기 (customer_name으로만 조회 - address 정보가 없으므로)
                customer_id = None
                if 'customer_name' in column_mapping and row.get(column_mapping['customer_name']):
                    customer_name = str(row[column_mapping['customer_name']]).strip()
                    customer = session.query(Customer).filter(
                        Customer.customer_name == customer_name
                    ).first()
                    if customer:
                        customer_id = customer.customer_id
                
                if not customer_id:
                    logger.warning(f"고객을 찾을 수 없는 행 건너뜀: {row}")
                    continue
                
                # 기본 직원 찾기 (employee_info에서)
                default_employee_info = session.query(EmployeeInfo).first()
                if not default_employee_info:
                    logger.warning("기본 직원이 없어 상호작용 로그를 생성할 수 없습니다.")
                    continue
                
                # 상호작용 로그 생성
                new_interaction = InteractionLog(
                    employee_id=default_employee_info.employee_info_id,
                    customer_id=customer_id,
                    interaction_type=row.get(column_mapping.get('interaction_type', ''), '방문'),
                    summary=row.get(column_mapping.get('summary', ''), ''),
                    sentiment=row.get(column_mapping.get('sentiment', ''), 'neutral'),
                    compliance_risk=row.get(column_mapping.get('compliance_risk', ''), 'low'),
                    interacted_at=interaction_date
                )
                session.add(new_interaction)
                processed_count += 1
            
            return {
                'success': True,
                'message': f'상호작용 로그 삽입 완료: {processed_count}건 처리됨',
                'processed_count': processed_count
            }
            
        except SQLAlchemyError as e:
            logger.error(f"상호작용 로그 삽입 중 DB 오류: {e}")
            raise
    
    def _insert_assignment_map(self, table_data: List[Dict[str, Any]], session: Session, column_mapping: Dict[str, str]) -> Dict[str, Any]:
        """직원-고객 배정 관계 삽입 (사번으로만 직원 조회)"""
        processed_count = 0
        skipped_count = 0
        
        try:
            for row in table_data:
                # 사번과 고객명 추출
                employee_number = str(row[column_mapping['employee_id']]).strip() if 'employee_id' in column_mapping and row.get(column_mapping['employee_id']) else None
                customer_name = str(row[column_mapping['customer_id']]).strip() if 'customer_id' in column_mapping and row.get(column_mapping['customer_id']) else None
                
                if not employee_number or not customer_name:
                    logger.warning(f"사번 또는 고객명을 찾을 수 없는 행 건너뜀: {row}")
                    skipped_count += 1
                    continue
                
                # 직원 ID 찾기 (사번으로만 조회)
                employee_info = session.query(EmployeeInfo).filter(
                    EmployeeInfo.employee_number == employee_number
                ).first()
                
                # 고객 ID 찾기 (customer_name으로만 조회 - address 정보가 없으므로)
                customer = session.query(Customer).filter(
                    Customer.customer_name == customer_name
                ).first()
                
                if not employee_info or not customer:
                    logger.warning(f"직원 또는 고객을 찾을 수 없음: 사번={employee_number}, 고객명={customer_name}")
                    skipped_count += 1
                    continue
                
                # 기존 배정 관계 확인
                existing_assignment = session.query(AssignmentMap).filter(
                    AssignmentMap.employee_id == employee_info.employee_info_id,
                    AssignmentMap.customer_id == customer.customer_id
                ).first()
                
                if existing_assignment:
                    logger.info(f"배정 관계가 이미 존재함: {employee_info.name} (사번: {employee_number}) - {customer_name}")
                    skipped_count += 1
                else:
                    # 새 배정 관계 생성
                    new_assignment = AssignmentMap(
                        employee_id=employee_info.employee_info_id,
                        customer_id=customer.customer_id
                    )
                    session.add(new_assignment)
                    logger.info(f"새 배정 관계 생성: {employee_info.name} (사번: {employee_number}) - {customer_name}")
                
                processed_count += 1
            
            return {
                'success': True,
                'message': f'배정 관계 삽입 완료: {processed_count}건 처리됨, {skipped_count}건 건너뜀',
                'processed_count': processed_count,
                'skipped_count': skipped_count
            }
            
        except SQLAlchemyError as e:
            logger.error(f"배정 관계 삽입 중 DB 오류: {e}")
            raise
    
    def _insert_documents(self, table_data: List[Dict[str, Any]], session: Session, column_mapping: Dict[str, str]) -> Dict[str, Any]:
        """문서 메타데이터 삽입"""
        processed_count = 0
        
        try:
            for row in table_data:
                # 필수 필드 추출
                doc_title = str(row[column_mapping['doc_title']]).strip() if 'doc_title' in column_mapping and row.get(column_mapping['doc_title']) else None
                uploader_id = int(row[column_mapping['uploader_id']]) if 'uploader_id' in column_mapping and row.get(column_mapping['uploader_id']) else None
                file_path = str(row[column_mapping['file_path']]).strip() if 'file_path' in column_mapping and row.get(column_mapping['file_path']) else None
                
                if not doc_title or not uploader_id or not file_path:
                    logger.warning(f"필수 필드가 없는 행 건너뜀: {row}")
                    continue
                
                # 선택 필드 추출
                doc_type = str(row[column_mapping['doc_type']]).strip() if 'doc_type' in column_mapping and row.get(column_mapping['doc_type']) else None
                version = str(row[column_mapping['version']]).strip() if 'version' in column_mapping and row.get(column_mapping['version']) else None
                
                # 새 문서 생성
                new_document = Document(
                    doc_title=doc_title,
                    uploader_id=uploader_id,
                    file_path=file_path,
                    doc_type=doc_type,
                    version=version
                )
                session.add(new_document)
                logger.info(f"새 문서 메타데이터 생성: {doc_title}")
                
                processed_count += 1
            
            return {
                'success': True,
                'message': f'문서 메타데이터 삽입 완료: {processed_count}건 처리됨',
                'processed_count': processed_count
            }
            
        except SQLAlchemyError as e:
            logger.error(f"문서 메타데이터 삽입 중 DB 오류: {e}")
            raise
    
    def _insert_document_relations(self, table_data: List[Dict[str, Any]], session: Session, column_mapping: Dict[str, str]) -> Dict[str, Any]:
        """문서 관계 삽입"""
        processed_count = 0
        
        try:
            for row in table_data:
                # 필수 필드 추출
                doc_id = int(row[column_mapping['doc_id']]) if 'doc_id' in column_mapping and row.get(column_mapping['doc_id']) else None
                related_entity_type = str(row[column_mapping['related_entity_type']]).strip() if 'related_entity_type' in column_mapping and row.get(column_mapping['related_entity_type']) else None
                related_entity_id = int(row[column_mapping['related_entity_id']]) if 'related_entity_id' in column_mapping and row.get(column_mapping['related_entity_id']) else None
                
                if not doc_id or not related_entity_type or not related_entity_id:
                    logger.warning(f"필수 필드가 없는 행 건너뜀: {row}")
                    continue
                
                # 선택 필드 추출
                confidence_score = int(row[column_mapping['confidence_score']]) if 'confidence_score' in column_mapping and row.get(column_mapping['confidence_score']) else 100
                
                # 기존 관계 확인
                existing_relation = session.query(DocumentRelation).filter(
                    DocumentRelation.doc_id == doc_id,
                    DocumentRelation.related_entity_type == related_entity_type,
                    DocumentRelation.related_entity_id == related_entity_id
                ).first()
                
                if existing_relation:
                    logger.info(f"문서 관계가 이미 존재함: doc_id={doc_id}, entity_type={related_entity_type}, entity_id={related_entity_id}")
                    continue
                
                # 새 문서 관계 생성
                new_relation = DocumentRelation(
                    doc_id=doc_id,
                    related_entity_type=related_entity_type,
                    related_entity_id=related_entity_id,
                    confidence_score=confidence_score
                )
                session.add(new_relation)
                logger.info(f"새 문서 관계 생성: doc_id={doc_id}, entity_type={related_entity_type}, entity_id={related_entity_id}")
                
                processed_count += 1
            
            return {
                'success': True,
                'message': f'문서 관계 삽입 완료: {processed_count}건 처리됨',
                'processed_count': processed_count
            }
            
        except SQLAlchemyError as e:
            logger.error(f"문서 관계 삽입 중 DB 오류: {e}")
            raise
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """날짜 문자열 파싱"""
        try:
            # YYYY-MM 형식 (월별 데이터용)
            if re.match(r'^\d{4}-\d{2}$', date_str):
                return datetime.strptime(date_str, '%Y-%m')
            
            # YYYYMM 형식 (월별 데이터용)
            if re.match(r'^\d{6}$', date_str):
                year = date_str[:4]
                month = date_str[4:6]
                return datetime.strptime(f"{year}-{month}", '%Y-%m')
            
            # 다양한 날짜 형식 지원
            date_formats = [
                '%Y-%m-%d',
                '%Y/%m/%d',
                '%Y.%m.%d',
                '%Y년 %m월 %d일',
                '%m/%d/%Y',
                '%d/%m/%Y'
            ]
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_str.strip(), fmt)
                except ValueError:
                    continue
            
            return None
        except Exception:
            return None
    
    def _is_monthly_sales_data(self, column_mapping: Dict[str, str]) -> bool:
        """월별 매출 데이터인지 확인"""
        import re
        
        # 1. 매핑된 컬럼명에서 YYYYMM 형태 확인
        monthly_columns = []
        for source_column in column_mapping.values():
            if re.match(r'^\d{6}$', str(source_column)):
                monthly_columns.append(source_column)
        
        # 2. 매핑되지 않은 원본 컬럼명들도 확인
        original_columns = list(column_mapping.keys())
        monthly_columns_original = [col for col in original_columns if re.match(r'^\d{6}$', str(col))]
        
        # 3. 모든 월별 컬럼 수집
        all_monthly_columns = list(set(monthly_columns + monthly_columns_original))
        
        # 4. 10개 이상의 월별 컬럼이 있으면 월별 데이터로 판단
        if len(all_monthly_columns) >= 10:
            logger.info(f"월별 매출 데이터 감지: {len(all_monthly_columns)}개 월별 컬럼 발견")
            return True
        
        return False
    
    def _transform_monthly_sales_data(self, table_data: List[Dict[str, Any]], column_mapping: Dict[str, str]) -> List[Dict[str, Any]]:
        """월별 매출 데이터를 개별 매출 기록으로 변환"""
        import re
        from datetime import datetime
        
        transformed_data = []
        
        # 상위 행의 거래처 값을 추적하기 위한 변수
        last_customer_name = ""
        
        # 변환 통계
        processed_rows = 0
        total_records = 0
        
        for row in table_data:
            processed_rows += 1
            
            # 기본 정보 추출 (LLM 매핑된 컬럼명만 사용)
            employee_name = ""
            employee_number = ""  # 사번 추가
            customer_name = ""
            product_name = ""
            
            # 매핑된 컬럼명에서 추출
            employee_name = str(row.get(column_mapping.get('employee_name', ''), '')).strip()
            employee_number = str(row.get(column_mapping.get('employee_number', ''), '')).strip()  # 사번 추출
            customer_name = str(row.get(column_mapping.get('customer_name', ''), '')).strip()
            product_name = str(row.get(column_mapping.get('product_name', ''), '')).strip()
            
            # 담당자와 품목이 비어있으면 해당 행 제외
            if not employee_name or employee_name == 'nan':
                logger.warning(f"담당자가 비어있는 행 제외: {row}")
                continue
            
            if not product_name or product_name == 'nan':
                logger.warning(f"품목이 비어있는 행 제외: {row}")
                continue
            
            # 합계 행 제외 (품목이나 거래처에 "합계", "총합계" 등이 포함된 경우)
            summary_keywords = ['합계', '총합계', 'total', 'sum']
            if any(keyword in str(product_name).lower() for keyword in summary_keywords) or \
               any(keyword in str(customer_name).lower() for keyword in summary_keywords):
                # 로그를 한 번만 출력하도록 수정
                if not hasattr(self, '_summary_row_logged'):
                    logger.info(f"합계 행 제외: 품목={product_name}, 거래처={customer_name}")
                    self._summary_row_logged = True
                continue
            
            # 거래처(ID)가 비어있으면 상위 행의 값 사용
            if customer_name and customer_name != 'nan':
                last_customer_name = customer_name
            else:
                customer_name = last_customer_name
            
            # 월별 매출 데이터 추출 (원본 컬럼명에서)
            row_records = 0
            for source_column, value in row.items():
                if re.match(r'^\d{6}$', str(source_column)) and value is not None:
                    try:
                        sale_amount = float(str(value).replace(',', '').strip())
                        if sale_amount > 0:  # 매출이 있는 경우만 처리
                            # YYYYMM → YYYY-MM 형식으로 변환
                            year = str(source_column)[:4]
                            month = str(source_column)[4:6]
                            sale_date = f"{year}-{month}-01"  # 날짜 형식 개선
                            
                            # 개별 매출 기록 생성
                            sale_record = {
                                'employee_name': employee_name,
                                'employee_number': employee_number, # 사번 추가
                                'customer_name': customer_name,
                                'product_name': product_name,
                                'sale_amount': sale_amount,
                                'sale_date': sale_date
                            }
                            transformed_data.append(sale_record)
                            row_records += 1
                    except (ValueError, TypeError):
                        # 숫자가 아닌 값은 건너뛰기
                        continue
            
            total_records += row_records
        
        logger.info(f"월별 데이터 변환 완료: {processed_rows}행 처리, {len(transformed_data)}개 매출 기록 생성")
        return transformed_data
    
    def _get_standard_sales_mapping(self) -> Dict[str, str]:
        """표준 매출 데이터 매핑 반환"""
        return {
            'employee_name': 'employee_name',
            'employee_number': 'employee_number',  # 사번 추가
            'customer_name': 'customer_name',
            'product_name': 'product_name',
            'sale_amount': 'sale_amount',
            'sale_date': 'sale_date'
        }
    



# 싱글턴 인스턴스
from app.services.utils.db import SessionLocal
text2sql_classifier = Text2SQLTableClassifier(db_session_factory=SessionLocal) 