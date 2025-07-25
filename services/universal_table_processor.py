import logging
import re
from typing import List, Dict, Any, Optional, Callable, TypedDict
from contextlib import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

# 모델 import 추가 (데이터 삽입 로직 구현)
from models.employees import Employee
from models.employee_info import EmployeeInfo
from models.customers import Customer
from models.sales_records import SalesRecord
from models.products import Product
from models.interaction_logs import InteractionLog

logger = logging.getLogger(__name__)

# 테이블 매핑 규칙 (컬럼 분석용)
TABLE_MAPPING_RULES = {
    'employee_info': {
        'required_columns': ['성명', '이름'],  # EmployeeInfo 모델의 name 필드 (필수)
        'optional_columns': ['사번', '직원명', '부서', '팀', '직급', '사업부', '지점', '연락처', '월평균사용예산', '최근 평가', '기본급(₩)', '성과급(₩)', '책임업무'],
        'score_weight': 1.0,
        'related_tables': {
            'employees': '직원 계정 정보',
            'sales_records': '직원이 매출을 담당',
            'interaction_logs': '직원이 고객과 상호작용',
            'customers': '직원이 담당하는 고객들'
        },
        'description': '직원 인사 정보 관리 (이름, 팀, 직급, 급여 등) - 문서 업로드 대상'
    },
    'customers': {
        'required_columns': ['고객명', '기관명'],  # Customer 모델의 customer_name 필드 (필수)
        'optional_columns': ['거래처ID', '주소', '총환자수', '담당자', '고객유형', '담당의사명', '고객등급', '메모'],
        'score_weight': 1.0,
        'related_tables': {
            'sales_records': '고객의 매출 기록',
            'interaction_logs': '고객과의 상호작용 기록',
            'employees': '고객을 담당하는 직원들'
        },
        'description': '고객(의료기관) 정보 관리 (기관명, 주소, 환자수 등)'
    },
    'sales_records': {
        'required_columns': ['매출', '날짜'],
        'optional_columns': ['제품명', '수량', '단가', '고객명', '직원명'],
        'score_weight': 1.0,
        'related_tables': {
            'customers': '매출이 발생한 고객',
            'employees': '매출을 담당한 직원',
            'products': '판매된 제품'
        },
        'description': '매출 기록 관리 (매출액, 날짜, 제품, 고객, 담당자)'
    },
    'products': {
        'required_columns': ['제품명', '상품명'],
        'optional_columns': ['가격', '단가', '카테고리', '설명'],
        'score_weight': 1.0,
        'related_tables': {
            'sales_records': '제품의 매출 기록',
            'customers': '제품을 구매하는 고객들'
        },
        'description': '제품 정보 관리 (제품명, 가격, 카테고리 등)'
    },
    'interaction_logs': {
        'required_columns': ['방문일', '상호작용일', '날짜'],  # InteractionLog 모델의 interacted_at 필드 (선택이지만 중요)
        'optional_columns': ['고객명', '직원명', '내용', '결과', '상호작용유형', '요약', '감정분석', '준법위험도'],
        'score_weight': 1.0,
        'related_tables': {
            'customers': '상호작용 대상 고객',
            'employees': '상호작용 담당 직원'
        },
        'description': '고객 상호작용 기록 관리 (방문일, 내용, 결과 등)'
    }
}

# 컬럼 분류 규칙 (복합 데이터 분리용)
COLUMN_CLASSIFICATION_RULES = {
    'employee_info_columns': ['사번', '직원명', '성명', '부서', '직급', '사업부', '지점', '연락처', '기본급', '성과급', '책임업무'],
    'customer_columns': ['거래처ID', '고객명', '기관명', '주소', '총환자수', '담당자'],
    'sales_columns': ['매출', '날짜', '제품명', '수량', '단가'],
    'product_columns': ['제품명', '상품명', '가격', '단가', '카테고리'],
    'interaction_columns': ['방문일', '상호작용일', '내용', '결과']
}

# 컬럼 동의어 매핑 (의미는 같지만 글자가 다른 컬럼들) - 실제 모델 구조 반영
COLUMN_SYNONYMS = {
    # 직원 관련 동의어 (Employee 모델 기반)
    '성명': ['직원명', '사원명', '이름', '직원이름', '사원이름', 'name'],
    '이름': ['성명', '직원명', '사원명', '직원이름', '사원이름', 'name'],
    '부서': ['팀', '소속', '부서명', '팀명', '소속부서', 'team'],
    '직급': ['직책', '포지션', 'position'],
    '사업부': ['비즈니스유닛', 'business_unit'],
    '연락처': ['전화번호', 'contact_number'],
    '책임업무': ['담당업무', 'responsibilities'],
    '이메일': ['email', '메일'],
    '사용자명': ['username', '아이디', 'ID'],
    '비밀번호': ['password', '패스워드', 'PW'],
    '역할': ['role', '권한'],
    
    # 고객 관련 동의어 (Customer 모델 기반)
    '고객명': ['거래처명', '기관명', '병원명', '고객이름', '거래처이름', 'customer_name'],
    '기관명': ['고객명', '거래처명', '병원명', '기관이름', 'customer_name'],
    '고객유형': ['customer_type', '고객타입'],
    '담당의사명': ['doctor_name', '담당자'],
    '고객등급': ['customer_grade', '등급'],
    '메모': ['notes', '비고', '특이사항'],
    
    # 매출 관련 동의어 (SalesRecord 모델 기반)
    '매출': ['판매금액', '금액', '매출액', '판매액', '매출금', 'sale_amount'],
    '날짜': ['판매일', '매출일', '거래일', '일자', 'sale_date'],
    '직원ID': ['employee_id', '담당자ID'],
    '고객ID': ['customer_id', '거래처ID'],
    '제품ID': ['product_id', '상품ID'],
    
    # 제품 관련 동의어 (Product 모델 기반)
    '제품명': ['상품명', '품목명', '제품이름', '상품이름', 'product_name'],
    '설명': ['description', '제품설명', '상세정보'],
    '카테고리': ['category', '분류'],
    
    # 상호작용 관련 동의어 (InteractionLog 모델 기반)
    '방문일': ['상호작용일', '방문날짜', '상호작용날짜', '일자', 'interacted_at'],
    '상호작용유형': ['interaction_type', '유형', '방문유형'],
    '요약': ['summary', '내용'],
    '감정분석': ['sentiment', '감정'],
    '준법위험도': ['compliance_risk', '위험도']
}

# 타입 정의
class ProcessingResult(TypedDict, total=False):
    success: bool
    message: str
    processed_count: int
    skipped_count: int
    analysis: Optional[Dict[str, Any]]
    results: Optional[Dict[str, Any]]
    processed_tables: Optional[List[str]]
    total_processed_count: Optional[int]
    partial_data: Optional[Dict[str, Any]]

class TableRow(TypedDict, total=False):
    # 고객 관련
    거래처ID: Optional[str]
    고객명: Optional[str]
    기관명: Optional[str]
    주소: Optional[str]
    총환자수: Optional[str]
    # 직원 관련
    사번: Optional[str]
    직원명: Optional[str]
    성명: Optional[str]
    부서: Optional[str]
    직급: Optional[str]
    # 매출 관련
    매출: Optional[str]
    날짜: Optional[str]
    제품명: Optional[str]
    # 기타 - 동적 키는 Dict[str, Any]로 처리

class UniversalTableProcessor:
    """범용 테이블 처리기 - 컬럼 분석 및 테이블 선택 전용"""
    
    def __init__(self, db_session_factory: Optional[Callable] = None):
        """초기화"""
        self.db_session_factory = db_session_factory
        # 데이터 삽입 관련 변수들 제거
        # self.processed_employees = set()
        # self.processed_customers = set()
        # self.processed_products = set()
    
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
    
    def _execute_with_session(self, func: Callable[[Session], ProcessingResult]) -> ProcessingResult:
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
    
    def analyze_table_structure(self, table_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        테이블 구조를 분석하여 적절한 테이블 타입을 결정
        """
        if not table_data:
            return {'table_type': None, 'confidence': 0.0, 'columns': []}
        
        columns = list(table_data[0].keys())
        logger.info(f"분석된 컬럼들: {columns}")
        
        # 각 테이블 타입별로 점수 계산
        table_scores = {}
        for table_type, rules in TABLE_MAPPING_RULES.items():
            score_result = self._calculate_table_score(columns, table_data, rules)
            table_scores[table_type] = score_result
        
        # 가장 높은 점수의 테이블 타입 선택
        best_table = max(table_scores.items(), key=lambda x: x[1]['score'])
        table_type, score_info = best_table
        
        confidence = score_info['score'] / 100.0  # 0-1 범위로 정규화
        
        logger.info(f"테이블 타입 분석 결과: {table_type} (점수: {score_info['score']:.2f}, 신뢰도: {confidence:.2f})")
        
        # 관련 테이블 정보 추가
        related_tables_info = {}
        if table_type and confidence > 0.3:
            table_rules = TABLE_MAPPING_RULES.get(table_type, {})
            related_tables_info = {
                'related_tables': table_rules.get('related_tables', {}),
                'description': table_rules.get('description', ''),
                'suggested_actions': self._get_suggested_actions(table_type, columns, table_data)
            }
        
        return {
            'table_type': table_type if confidence > 0.3 else None,
            'confidence': confidence,
            'columns': columns,
            'scores': table_scores,
            'related_tables': related_tables_info
        }
    
    def _calculate_table_score(self, columns: List[str], table_data: List[Dict], rules: Dict) -> Dict[str, Any]:
        """테이블 타입별 점수 계산"""
        score = 0
        matched_required = []
        matched_optional = []
        
        # 필수 컬럼 매칭
        for required_col in rules['required_columns']:
            for col in columns:
                if required_col in col:
                    score += 30  # 필수 컬럼은 높은 가중치
                    matched_required.append(col)
                    break
        
        # 선택 컬럼 매칭
        for optional_col in rules['optional_columns']:
            for col in columns:
                if optional_col in col:
                    score += 10  # 선택 컬럼은 낮은 가중치
                    matched_optional.append(col)
                    break
        
        # 데이터 패턴 분석 (간단한 예시)
        if table_data:
            sample_row = table_data[0]
            # 숫자 데이터가 많은 경우 매출/제품 관련일 가능성
            numeric_count = sum(1 for v in sample_row.values() if str(v).replace(',', '').replace('.', '').isdigit())
            if numeric_count > len(sample_row) * 0.3:
                score += 5
        
        return {
            'score': score,
            'matched_required': matched_required,
            'matched_optional': matched_optional
        }
    
    def _get_suggested_actions(self, table_type: str, columns: List[str], table_data: List[Dict[str, Any]]) -> List[str]:
        """테이블 타입에 따른 제안 액션 생성"""
        suggestions = []
        
        if table_type == 'employees':
            suggestions.append("직원 정보를 employees 테이블에 저장")
            if any('매출' in col for col in columns):
                suggestions.append("매출 정보가 포함되어 있으므로 sales_records 테이블도 함께 처리 고려")
            if any('고객' in col for col in columns):
                suggestions.append("고객 정보가 포함되어 있으므로 customers 테이블도 함께 처리 고려")
        
        elif table_type == 'customers':
            suggestions.append("고객 정보를 customers 테이블에 저장")
            if any('매출' in col for col in columns):
                suggestions.append("매출 정보가 포함되어 있으므로 sales_records 테이블도 함께 처리 고려")
            if any('방문' in col or '상호작용' in col for col in columns):
                suggestions.append("상호작용 정보가 포함되어 있으므로 interaction_logs 테이블도 함께 처리 고려")
        
        elif table_type == 'sales_records':
            suggestions.append("매출 정보를 sales_records 테이블에 저장")
            suggestions.append("고객 정보가 있으면 customers 테이블과 연결")
            suggestions.append("직원 정보가 있으면 employees 테이블과 연결")
            suggestions.append("제품 정보가 있으면 products 테이블과 연결")
        
        elif table_type == 'products':
            suggestions.append("제품 정보를 products 테이블에 저장")
            if any('매출' in col for col in columns):
                suggestions.append("매출 정보가 포함되어 있으므로 sales_records 테이블도 함께 처리 고려")
        
        elif table_type == 'interaction_logs':
            suggestions.append("상호작용 정보를 interaction_logs 테이블에 저장")
            suggestions.append("고객 정보가 있으면 customers 테이블과 연결")
            suggestions.append("직원 정보가 있으면 employees 테이블과 연결")
        
        # 공통 제안사항
        if len(table_data) > 100:
            suggestions.append("대용량 데이터이므로 배치 처리 고려")
        
        if any('날짜' in col for col in columns):
            suggestions.append("날짜 데이터가 있으므로 날짜 형식 검증 필요")
        
        if any('금액' in col or '매출' in col or '가격' in col for col in columns):
            suggestions.append("금액 데이터가 있으므로 숫자 형식 검증 필요")
        
        return suggestions
    
    def check_required_columns(self, table_data: List[Dict[str, Any]], table_type: str) -> Dict[str, Any]:
        """특정 테이블 타입에 대한 필수 컬럼 검사 (동의어 매핑 포함)"""
        if not table_data:
            return {
                'has_required_columns': False,
                'missing_columns': [],
                'available_columns': [],
                'message': '데이터가 없습니다.'
            }
        
        columns = list(table_data[0].keys())
        table_rules = TABLE_MAPPING_RULES.get(table_type, {})
        required_columns = table_rules.get('required_columns', [])
        
        # 필수 컬럼 매칭 확인 (동의어 매핑 포함)
        matched_required = []
        missing_required = []
        column_mapping = {}  # 원본 컬럼명 -> 실제 컬럼명 매핑
        
        for required_col in required_columns:
            found = False
            matched_column = None
            
            # 1. 정확한 매칭 시도
            for col in columns:
                if required_col == col:
                    matched_column = col
                    found = True
                    break
            
            # 2. 부분 문자열 매칭 시도
            if not found:
                for col in columns:
                    if required_col in col or col in required_col:
                        matched_column = col
                        found = True
                        break
            
            # 3. 동의어 매핑 시도
            if not found:
                synonyms = COLUMN_SYNONYMS.get(required_col, [])
                for synonym in synonyms:
                    for col in columns:
                        if synonym == col or synonym in col or col in synonym:
                            matched_column = col
                            found = True
                            break
                    if found:
                        break
            
            if found and matched_column:
                matched_required.append(matched_column)
                column_mapping[required_col] = matched_column
            else:
                missing_required.append(required_col)
        
        has_required = len(missing_required) == 0
        
        return {
            'has_required_columns': has_required,
            'missing_columns': missing_required,
            'available_columns': columns,
            'matched_required_columns': matched_required,
            'column_mapping': column_mapping,  # 원본 -> 실제 컬럼명 매핑
            'message': f"필수 컬럼 {'충족' if has_required else '부족'}: {len(matched_required)}/{len(required_columns)}"
        }
    
    def insert_data_to_table(self, table_data: List[Dict[str, Any]], table_type: str) -> ProcessingResult:
        """필수 컬럼 검사 후 해당 테이블에 데이터 삽입"""
        # 1. 필수 컬럼 검사
        column_check = self.check_required_columns(table_data, table_type)
        
        if not column_check['has_required_columns']:
            return {
                'success': False,
                'message': f"{table_type} 테이블: {column_check['message']} - 부족한 컬럼: {column_check['missing_columns']}",
                'processed_count': 0,
                'column_check': column_check
            }
        
        # 2. 필수 컬럼이 모두 존재하면 데이터 삽입
        logger.info(f"{table_type} 테이블에 데이터 삽입 시작: {len(table_data)}개 행")
        
        try:
            if table_type == 'employee_info':
                return self._execute_with_session(lambda session: self._insert_employee_info(table_data, session, column_check))
            elif table_type == 'customers':
                return self._execute_with_session(lambda session: self._insert_customers(table_data, session, column_check))
            elif table_type == 'sales_records':
                return self._execute_with_session(lambda session: self._insert_sales_records(table_data, session, column_check))
            elif table_type == 'products':
                return self._execute_with_session(lambda session: self._insert_products(table_data, session, column_check))
            elif table_type == 'interaction_logs':
                return self._execute_with_session(lambda session: self._insert_interaction_logs(table_data, session, column_check))
            else:
                return {
                    'success': False,
                    'message': f'지원하지 않는 테이블 타입: {table_type}',
                    'processed_count': 0
                }
        except Exception as e:
            logger.error(f"{table_type} 테이블 데이터 삽입 중 오류: {e}")
            return {
                'success': False,
                'message': f'데이터 삽입 중 오류 발생: {str(e)}',
                'processed_count': 0
            }
    
    def process_table_data(self, table_data: List[Dict[str, Any]]) -> ProcessingResult:
        """
        테이블 데이터를 분석하고 적절한 테이블 타입을 결정
        (데이터 삽입 로직 제거)
        """
        # 테이블 구조 분석
        analysis = self.analyze_table_structure(table_data)
        
        if not analysis['table_type']:
            logger.warning(f"적절한 테이블 타입을 찾을 수 없습니다. 신뢰도: {analysis['confidence']:.2f}")
            return {
                'success': False,
                'message': f"테이블 타입을 결정할 수 없습니다. 신뢰도: {analysis['confidence']:.2f}",
                'analysis': analysis,
                'processed_count': 0
            }
        
        # 복합 데이터인지 확인
        if self._is_composite_data(table_data):
            logger.info("복합 데이터 감지됨. 자동 분리 및 데이터 삽입 시작")
            return self._process_composite_data_with_insertion(table_data)
        
        # 단일 테이블 처리: 필수 컬럼 검사 후 데이터 삽입
        table_type = analysis['table_type']
        if table_type:
            logger.info(f"단일 테이블 처리: {table_type}")
            return self.insert_data_to_table(table_data, table_type)
        
        # 테이블 타입을 결정할 수 없는 경우
        return {
            'success': False,
            'message': f'테이블 타입을 결정할 수 없습니다. 신뢰도: {analysis["confidence"]:.2f}',
            'analysis': analysis,
            'processed_count': 0
        }
    
    def _is_composite_data(self, table_data: List[Dict[str, Any]]) -> bool:
        """복합 데이터인지 확인 (여러 테이블의 컬럼이 섞여있는지)"""
        if not table_data:
            return False
        
        columns = list(table_data[0].keys())
        
        # 각 테이블 타입별로 매칭되는 컬럼 수 계산
        table_matches = {}
        for table_type, rules in TABLE_MAPPING_RULES.items():
            matched_columns = []
            for col in columns:
                for required_col in rules['required_columns'] + rules['optional_columns']:
                    if required_col in col:
                        matched_columns.append(col)
                        break
            table_matches[table_type] = len(matched_columns)
        
        # 2개 이상의 테이블에 의미있는 컬럼이 매칭되면 복합 데이터로 판단
        meaningful_matches = [count for count in table_matches.values() if count >= 2]
        return len(meaningful_matches) >= 2
    
    def _process_composite_data_with_insertion(self, table_data: List[Dict[str, Any]]) -> ProcessingResult:
        """복합 데이터를 자동 분리하여 필수 컬럼 검사 후 데이터 삽입"""
        logger.info("복합 데이터 자동 분리 및 데이터 삽입 시작")
        
        # 1. 컬럼별로 데이터 분리
        separated_data = self._separate_data_by_columns(table_data)
        
        # 2. 각 분리된 데이터에 대해 필수 컬럼 검사 및 데이터 삽입
        insertion_results = {}
        total_processed = 0
        successful_tables = []
        
        for table_type, data in separated_data.items():
            if data and len(data) > 0:
                logger.info(f"{table_type} 테이블 처리: {len(data)}개 행")
                
                # 필수 컬럼 검사 및 데이터 삽입
                result = self.insert_data_to_table(data, table_type)
                insertion_results[table_type] = result
                
                if result.get('success'):
                    total_processed += result.get('processed_count', 0)
                    successful_tables.append(table_type)
                    logger.info(f"{table_type} 테이블 처리 성공: {result.get('processed_count', 0)}건")
                else:
                    logger.warning(f"{table_type} 테이블 처리 실패: {result.get('message', '')}")
        
        # 3. 결과 요약
        return {
            'success': len(successful_tables) > 0,
            'message': f'복합 데이터 처리 완료: {len(successful_tables)}개 테이블에 {total_processed}건 저장',
            'results': insertion_results,
            'processed_tables': successful_tables,
            'total_processed_count': total_processed
        }
    
    def _separate_data_by_columns(self, table_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """컬럼별로 데이터를 분리"""
        separated = {
            'employee_info': [],
            'customers': [],
            'sales_records': [],
            'products': [],
            'interaction_logs': []
        }
        
        for row in table_data:
            # 각 테이블 타입별로 관련 컬럼만 추출
            employee_row = self._extract_employee_data(row)
            customer_row = self._extract_customer_data(row)
            sales_row = self._extract_sales_data(row)
            product_row = self._extract_product_data(row)
            interaction_row = self._extract_interaction_data(row)
            
            # 데이터가 있는 경우만 추가
            if employee_row:
                separated['employee_info'].append(employee_row)
            if customer_row:
                separated['customers'].append(customer_row)
            if sales_row:
                separated['sales_records'].append(sales_row)
            if product_row:
                separated['products'].append(product_row)
            if interaction_row:
                separated['interaction_logs'].append(interaction_row)
        
        return separated
    
    def _extract_employee_data(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """직원 관련 데이터 추출"""
        employee_data = {}
        for col, value in row.items():
            if any(pattern in col for pattern in COLUMN_CLASSIFICATION_RULES['employee_info_columns']):
                if value is not None and str(value).strip():
                    employee_data[col] = value
        return employee_data if employee_data else None
    
    def _extract_customer_data(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """고객 관련 데이터 추출"""
        customer_data = {}
        for col, value in row.items():
            if any(pattern in col for pattern in COLUMN_CLASSIFICATION_RULES['customer_columns']):
                if value is not None and str(value).strip():
                    customer_data[col] = value
        return customer_data if customer_data else None
    
    def _extract_sales_data(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """매출 관련 데이터 추출"""
        sales_data = {}
        for col, value in row.items():
            if any(pattern in col for pattern in COLUMN_CLASSIFICATION_RULES['sales_columns']):
                if value is not None and str(value).strip():
                    sales_data[col] = value
        return sales_data if sales_data else None
    
    def _extract_product_data(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """제품 관련 데이터 추출"""
        product_data = {}
        for col, value in row.items():
            if any(pattern in col for pattern in COLUMN_CLASSIFICATION_RULES['product_columns']):
                if value is not None and str(value).strip():
                    product_data[col] = value
        return product_data if product_data else None
    
    def _extract_interaction_data(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """상호작용 관련 데이터 추출"""
        interaction_data = {}
        for col, value in row.items():
            if any(pattern in col for pattern in COLUMN_CLASSIFICATION_RULES['interaction_columns']):
                if value is not None and str(value).strip():
                    interaction_data[col] = value
        return interaction_data if interaction_data else None
    
    # === 데이터 삽입 메서드들 ===
    
    def _insert_employee_info(self, table_data: List[Dict[str, Any]], session: Session, column_check: Dict[str, Any]) -> ProcessingResult:
        """직원 인사 정보 삽입 (컬럼 검사 결과 활용)"""
        processed_count = 0
        skipped_count = 0
        
        # 컬럼 매핑 정보 (필수 컬럼 검사 결과 활용)
        matched_columns = column_check['matched_required_columns']
        available_columns = column_check['available_columns']
        column_mapping = column_check.get('column_mapping', {})
        
        # 컬럼 매핑 생성 (동의어 매핑 결과 활용)
        name_column = None
        if '성명' in column_mapping:
            name_column = column_mapping['성명']
        elif '직원명' in column_mapping:
            name_column = column_mapping['직원명']
        else:
            # 매핑에 없으면 기존 방식으로 찾기
            name_column = next((col for col in matched_columns if any(pattern in col for pattern in ['성명', '직원명', '사원명', '이름'])), None)
            if not name_column:
                name_column = next((col for col in available_columns if any(pattern in col for pattern in ['성명', '직원명', '사원명', '이름'])), None)
        
        # 추가 컬럼 매핑
        team_column = next((col for col in available_columns if any(pattern in col for pattern in ['부서', '팀', '소속'])), None)
        position_column = next((col for col in available_columns if any(pattern in col for pattern in ['직급', '직책', '포지션'])), None)
        salary_column = next((col for col in available_columns if any(pattern in col for pattern in ['기본급', '급여', '월급'])), None)
        incentive_column = next((col for col in available_columns if any(pattern in col for pattern in ['성과급', '인센티브', '보너스'])), None)
        
        try:
            for row in table_data:
                # 직원명 추출 (매핑된 컬럼 사용)
                employee_name = str(row[name_column]).strip() if name_column and row.get(name_column) else None
                
                if not employee_name:
                    logger.warning(f"직원명을 찾을 수 없는 행 건너뜀: {row}")
                    continue
                
                # 기존 직원 계정 확인
                existing_employee = session.query(Employee).filter(
                    Employee.name == employee_name
                ).first()
                
                if not existing_employee:
                    # 계정이 없으면 기본 계정 생성
                    existing_employee = Employee(
                        name=employee_name,
                        email=f"{employee_name}@company.com",
                        username=f"{employee_name.lower()}",
                        password="default_password",
                        role="user"
                    )
                    session.add(existing_employee)
                    session.flush()  # ID 생성
                    logger.info(f"새 직원 계정 생성: {employee_name}")
                
                # 기존 인사 정보 확인
                existing_info = session.query(EmployeeInfo).filter(
                    EmployeeInfo.employee_id == existing_employee.employee_id
                ).first()
                
                # 인사 정보 데이터 준비
                team = str(row[team_column]).strip() if team_column and row.get(team_column) else None
                position = str(row[position_column]).strip() if position_column and row.get(position_column) else None
                
                # 급여 정보 추출
                base_salary = None
                if salary_column and row.get(salary_column):
                    try:
                        base_salary = int(str(row[salary_column]).replace(",", "").strip())
                    except:
                        pass
                
                incentive_pay = None
                if incentive_column and row.get(incentive_column):
                    try:
                        incentive_pay = int(str(row[incentive_column]).replace(",", "").strip())
                    except:
                        pass
                
                if existing_info:
                    # 인사 정보 업데이트
                    if team and existing_info.team != team:
                        existing_info.team = team
                    if position and existing_info.position != position:
                        existing_info.position = position
                    if base_salary is not None:
                        existing_info.base_salary = base_salary
                    if incentive_pay is not None:
                        existing_info.incentive_pay = incentive_pay
                    session.add(existing_info)
                    logger.info(f"직원 인사 정보 업데이트: {employee_name}")
                else:
                    # 새 인사 정보 생성
                    new_info = EmployeeInfo(
                        employee_id=existing_employee.employee_id,
                        name=employee_name,
                        team=team,
                        position=position,
                        base_salary=base_salary,
                        incentive_pay=incentive_pay
                    )
                    session.add(new_info)
                    logger.info(f"새 직원 인사 정보 생성: {employee_name}")
                
                processed_count += 1
            
            return {
                'success': True,
                'message': f'직원 인사 정보 삽입 완료: {processed_count}명 처리됨, {skipped_count}명 중복 건너뜀',
                'processed_count': processed_count,
                'skipped_count': skipped_count
            }
            
        except SQLAlchemyError as e:
            logger.error(f"직원 인사 정보 삽입 중 DB 오류: {e}")
            raise
    
    def _insert_customers(self, table_data: List[Dict[str, Any]], session: Session, column_check: Dict[str, Any]) -> ProcessingResult:
        """고객 데이터 삽입 (컬럼 검사 결과 활용)"""
        processed_count = 0
        skipped_count = 0
        
        # 컬럼 매핑 정보 (필수 컬럼 검사 결과 활용)
        matched_columns = column_check['matched_required_columns']
        available_columns = column_check['available_columns']
        column_mapping = column_check.get('column_mapping', {})
        
        # 컬럼 매핑 생성 (동의어 매핑 결과 활용)
        name_column = None
        if '고객명' in column_mapping:
            name_column = column_mapping['고객명']
        elif '기관명' in column_mapping:
            name_column = column_mapping['기관명']
        elif '거래처ID' in column_mapping:
            name_column = column_mapping['거래처ID']
        else:
            # 매핑에 없으면 기존 방식으로 찾기
            name_column = next((col for col in matched_columns if any(pattern in col for pattern in ['거래처ID', '고객명', '기관명', '병원명'])), None)
        
        address_column = next((col for col in available_columns if any(pattern in col for pattern in ['주소', '지역', '위치'])), None)
        patients_column = next((col for col in available_columns if any(pattern in col for pattern in ['총환자수', '환자수', '규모'])), None)
        
        try:
            for row in table_data:
                # 고객명 추출 (매핑된 컬럼 사용)
                customer_name = str(row[name_column]).strip() if name_column and row.get(name_column) else None
                
                if not customer_name:
                    logger.warning(f"고객명을 찾을 수 없는 행 건너뜀: {row}")
                    continue
                
                # 주소 추출 (매핑된 컬럼 사용)
                address = str(row[address_column]).strip() if address_column and row.get(address_column) else None
                
                # 총환자수 추출 (매핑된 컬럼 사용)
                total_patients = None
                if patients_column and row.get(patients_column):
                    try:
                        total_patients = int(str(row[patients_column]).replace(",", "").strip())
                    except:
                        pass
                
                # 기존 고객 확인
                existing_customer = session.query(Customer).filter(
                    Customer.customer_name == customer_name
                ).first()
                
                if existing_customer:
                    # 업데이트
                    if address and existing_customer.address != address:
                        existing_customer.address = address
                    if total_patients is not None:
                        existing_customer.total_patients = total_patients
                    session.add(existing_customer)
                    logger.info(f"고객 정보 업데이트: {customer_name}")
                else:
                    # 새 고객 등록
                    new_customer = Customer(
                        customer_name=customer_name,
                        address=address,
                        total_patients=total_patients
                    )
                    session.add(new_customer)
                    logger.info(f"새 고객 등록: {customer_name}")
                
                processed_count += 1
            
            return {
                'success': True,
                'message': f'고객 데이터 삽입 완료: {processed_count}명 처리됨, {skipped_count}명 중복 건너뜀',
                'processed_count': processed_count,
                'skipped_count': skipped_count
            }
            
        except SQLAlchemyError as e:
            logger.error(f"고객 데이터 삽입 중 DB 오류: {e}")
            raise
    
    def _insert_sales_records(self, table_data: List[Dict[str, Any]], session: Session, column_check: Dict[str, Any]) -> ProcessingResult:
        """매출 데이터 삽입 (컬럼 검사 결과 활용)"""
        processed_count = 0
        
        # 컬럼 매핑 정보 (필수 컬럼 검사 결과 활용)
        matched_columns = column_check['matched_required_columns']
        available_columns = column_check['available_columns']
        
        # 컬럼 매핑 생성
        amount_column = next((col for col in matched_columns if any(pattern in col for pattern in ['매출', '판매금액', '금액', '매출액'])), None)
        date_column = next((col for col in matched_columns if any(pattern in col for pattern in ['날짜', '판매일', '매출일', '월'])), None)
        customer_column = next((col for col in available_columns if any(pattern in col for pattern in ['고객명', '거래처', '기관명'])), None)
        
        try:
            for row in table_data:
                # 매출 금액 추출 (매핑된 컬럼 사용)
                sale_amount = None
                if amount_column and row.get(amount_column):
                    try:
                        sale_amount = int(str(row[amount_column]).replace(",", "").strip())
                    except:
                        pass
                
                if sale_amount is None:
                    logger.warning(f"매출 금액을 찾을 수 없는 행 건너뜀: {row}")
                    continue
                
                # 날짜 추출 (매핑된 컬럼 사용)
                sale_date = None
                if date_column and row.get(date_column):
                    sale_date = self._parse_date(str(row[date_column]))
                
                if not sale_date:
                    logger.warning(f"날짜를 찾을 수 없는 행 건너뜀: {row}")
                    continue
                
                # 고객명 추출 (매핑된 컬럼 사용)
                customer_name = str(row[customer_column]).strip() if customer_column and row.get(customer_column) else None
                
                # 고객 ID 찾기
                customer_id = None
                if customer_name:
                    customer = session.query(Customer).filter(
                        Customer.customer_name == customer_name
                    ).first()
                    if customer:
                        customer_id = customer.customer_id
                
                # 매출 기록 생성
                from datetime import datetime
                from decimal import Decimal
                
                # 날짜 변환
                if isinstance(sale_date, str):
                    try:
                        sale_date_obj = datetime.strptime(sale_date, '%Y-%m-%d').date()
                    except:
                        sale_date_obj = datetime.now().date()
                else:
                    sale_date_obj = sale_date
                
                # 기본 직원과 제품 찾기 (외래키 제약조건 만족을 위해)
                default_employee = session.query(Employee).first()
                default_product = session.query(Product).first()
                
                if not default_employee:
                    logger.warning("기본 직원이 없어 매출 기록을 생성할 수 없습니다.")
                    continue
                
                if not default_product:
                    logger.warning("기본 제품이 없어 매출 기록을 생성할 수 없습니다.")
                    continue
                
                sale_record = SalesRecord(
                    customer_id=customer_id or 1,  # 기본값
                    employee_id=default_employee.employee_id,  # 실제 존재하는 직원 ID
                    product_id=default_product.product_id,     # 실제 존재하는 제품 ID
                    sale_amount=Decimal(str(sale_amount)),
                    sale_date=sale_date_obj
                )
                session.add(sale_record)
                processed_count += 1
            
            return {
                'success': True,
                'message': f'매출 데이터 삽입 완료: {processed_count}건 처리됨',
                'processed_count': processed_count
            }
            
        except SQLAlchemyError as e:
            logger.error(f"매출 데이터 삽입 중 DB 오류: {e}")
            raise
    
    def _insert_products(self, table_data: List[Dict[str, Any]], session: Session, column_check: Dict[str, Any]) -> ProcessingResult:
        """제품 데이터 삽입 (컬럼 검사 결과 활용)"""
        processed_count = 0
        skipped_count = 0
        
        # 컬럼 매핑 정보 (필수 컬럼 검사 결과 활용)
        matched_columns = column_check['matched_required_columns']
        available_columns = column_check['available_columns']
        
        # 컬럼 매핑 생성
        name_column = next((col for col in matched_columns if any(pattern in col for pattern in ['제품명', '상품명', '품목명'])), None)
        price_column = next((col for col in available_columns if any(pattern in col for pattern in ['가격', '단가', '비용'])), None)
        
        try:
            for row in table_data:
                # 제품명 추출 (매핑된 컬럼 사용)
                product_name = str(row[name_column]).strip() if name_column and row.get(name_column) else None
                
                if not product_name:
                    logger.warning(f"제품명을 찾을 수 없는 행 건너뜀: {row}")
                    continue
                
                # 가격 추출 (매핑된 컬럼 사용)
                price = None
                if price_column and row.get(price_column):
                    try:
                        price = int(str(row[price_column]).replace(",", "").strip())
                    except:
                        pass
                
                # 기존 제품 확인
                existing_product = session.query(Product).filter(
                    Product.product_name == product_name
                ).first()
                
                if existing_product:
                    # 업데이트 (Product 모델에는 price 속성이 없으므로 description만 업데이트)
                    if price:
                        existing_product.description = f"제품: {product_name} (가격: {price:,}원)"
                    session.add(existing_product)
                    logger.info(f"제품 정보 업데이트: {product_name}")
                else:
                    # 새 제품 등록
                    description = f"제품: {product_name}"
                    if price:
                        description += f" (가격: {price:,}원)"
                    
                    new_product = Product(
                        product_name=product_name,
                        description=description
                    )
                    session.add(new_product)
                    logger.info(f"새 제품 등록: {product_name}")
                
                processed_count += 1
            
            return {
                'success': True,
                'message': f'제품 데이터 삽입 완료: {processed_count}개 처리됨, {skipped_count}개 중복 건너뜀',
                'processed_count': processed_count,
                'skipped_count': skipped_count
            }
            
        except SQLAlchemyError as e:
            logger.error(f"제품 데이터 삽입 중 DB 오류: {e}")
            raise
    
    def _insert_interaction_logs(self, table_data: List[Dict[str, Any]], session: Session, column_check: Dict[str, Any]) -> ProcessingResult:
        """상호작용 로그 데이터 삽입 (컬럼 검사 결과 활용)"""
        processed_count = 0
        
        # 컬럼 매핑 정보 (필수 컬럼 검사 결과 활용)
        matched_columns = column_check['matched_required_columns']
        available_columns = column_check['available_columns']
        
        # 컬럼 매핑 생성
        date_column = next((col for col in matched_columns if any(pattern in col for pattern in ['방문일', '상호작용일', '날짜', '일자'])), None)
        customer_column = next((col for col in available_columns if any(pattern in col for pattern in ['고객명', '거래처', '기관명'])), None)
        type_column = next((col for col in available_columns if any(pattern in col for pattern in ['방문유형', '상호작용유형', '유형'])), None)
        
        try:
            for row in table_data:
                # 날짜 추출 (매핑된 컬럼 사용)
                interaction_date = None
                if date_column and row.get(date_column):
                    interaction_date = self._parse_date(str(row[date_column]))
                
                if not interaction_date:
                    logger.warning(f"날짜를 찾을 수 없는 행 건너뜀: {row}")
                    continue
                
                # 고객명 추출 (매핑된 컬럼 사용)
                customer_name = str(row[customer_column]).strip() if customer_column and row.get(customer_column) else None
                
                # 고객 ID 찾기
                customer_id = None
                if customer_name:
                    customer = session.query(Customer).filter(
                        Customer.customer_name == customer_name
                    ).first()
                    if customer:
                        customer_id = customer.customer_id
                
                if not customer_id:
                    logger.warning(f"고객을 찾을 수 없는 행 건너뜀: {row}")
                    continue
                
                # 상호작용 유형 추출 (매핑된 컬럼 사용)
                interaction_type = "방문"
                if type_column and row.get(type_column):
                    interaction_type = str(row[type_column]).strip()
                
                # 기본 직원 찾기 (외래키 제약조건 만족을 위해)
                default_employee = session.query(Employee).first()
                
                if not default_employee:
                    logger.warning("기본 직원이 없어 상호작용 로그를 생성할 수 없습니다.")
                    continue
                
                # 상호작용 로그 생성
                interaction_log = InteractionLog(
                    customer_id=customer_id,
                    employee_id=default_employee.employee_id,  # 실제 존재하는 직원 ID
                    interaction_type=interaction_type,
                    interacted_at=interaction_date
                )
                session.add(interaction_log)
                processed_count += 1
            
            return {
                'success': True,
                'message': f'상호작용 로그 삽입 완료: {processed_count}건 처리됨',
                'processed_count': processed_count
            }
            
        except SQLAlchemyError as e:
            logger.error(f"상호작용 로그 삽입 중 DB 오류: {e}")
            raise
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """날짜 문자열을 파싱하여 YYYY-MM-DD 형식으로 반환"""
        import re
        try:
            date_str = str(date_str).strip()
            
            # YYYYMM 형식
            if len(date_str) == 6 and date_str.isdigit():
                year = date_str[:4]
                month = date_str[4:6]
                return f"{year}-{month}-01"
            
            # YYYY-MM 형식
            if re.match(r'\d{4}-\d{2}', date_str):
                return f"{date_str}-01"
            
            # YYYY-MM-DD 형식
            if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
                return date_str
            
            return None
        except:
            return None

# 범용 테이블 처리기 인스턴스 생성
universal_table_processor = UniversalTableProcessor() 