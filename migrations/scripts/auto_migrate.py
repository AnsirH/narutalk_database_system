#!/usr/bin/env python3
"""
자동 마이그레이션 스크립트
스키마 변경을 감지하고 자동으로 마이그레이션을 실행합니다.
"""

import os
import sys
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# settings.py를 사용하여 환경변수 로드

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AutoMigrator:
    def __init__(self):
        # Docker 환경 설정
        self.project_root = Path('/app')
        self.alembic_dir = self.project_root / "migrations" / "alembic"
        self.scripts_dir = self.project_root / "migrations" / "scripts"
        
        # 작업 디렉토리를 프로젝트 루트로 변경
        os.chdir(self.project_root)
        logger.info(f"작업 디렉토리: {self.project_root}")
    
    def run_command(self, command, description=""):
        """명령어 실행 및 결과 반환"""
        try:
            logger.info(f"🔄 {description}")
            logger.info(f"실행 명령어: {command}")
            
            # 환경변수에 인코딩 설정 추가
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONUTF8'] = '1'
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                cwd=self.project_root,
                env=env
            )
            
            if result.returncode == 0:
                logger.info(f"✅ {description} 성공")
                if result.stdout:
                    logger.info(f"출력: {result.stdout.strip()}")
                return True, result.stdout
            else:
                logger.error(f"❌ {description} 실패")
                logger.error(f"오류: {result.stderr}")
                return False, result.stderr
                
        except Exception as e:
            logger.error(f"❌ 명령어 실행 중 오류: {e}")
            return False, str(e)
    
    def check_schema_changes(self):
        """스키마 변경사항 감지"""
        logger.info("🔍 스키마 변경사항 감지 중...")
        
        try:
            # schema_detector.py 실행
            detector_script = self.scripts_dir / "schema_detector.py"
            result = subprocess.run(
                [sys.executable, str(detector_script)],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            # 종료 코드로 변경사항 여부 판단
            has_changes = result.returncode == 1
            
            if has_changes:
                logger.info("📝 스키마 변경사항이 감지되었습니다!")
                logger.info(f"감지 결과: {result.stdout}")
            else:
                logger.info("✅ 스키마 변경사항이 없습니다.")
            
            return has_changes, result.stdout
            
        except Exception as e:
            logger.error(f"❌ 스키마 감지 중 오류: {e}")
            return False, str(e)
    
    def create_migration(self):
        """새 마이그레이션 파일 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        message = "auto_migration"  # 메시지에서 시간 제거
        
        # --rev-id 옵션으로 직접 파일명 지정
        command = f'alembic revision --autogenerate --rev-id {timestamp} -m "{message}"'
        return self.run_command(command, "새 마이그레이션 파일 생성")
    

    
    def apply_migrations(self):
        """마이그레이션 적용"""
        command = "alembic upgrade head"
        return self.run_command(command, "마이그레이션 적용")
    
    def check_migration_status(self):
        """마이그레이션 상태 확인"""
        command = "alembic current"
        return self.run_command(command, "마이그레이션 상태 확인")
    
    def backup_database(self):
        """데이터베이스 백업 (선택사항)"""
        logger.info("💾 데이터베이스 백업 중...")
        # PostgreSQL 백업 명령어 (필요시 구현)
        # pg_dump 명령어 등
        logger.info("✅ 백업 완료 (현재는 스킵)")
        return True, "백업 스킵됨"
    
    def reset_database(self):
        """데이터베이스 초기화 (개발 환경용)"""
        logger.info("🔄 데이터베이스 초기화 중...")
        command = "alembic downgrade base"
        success, output = self.run_command(command, "데이터베이스 초기화")
        if success:
            logger.info("✅ 데이터베이스 초기화 완료")
        return success, output
    
    def check_and_fix_migration_status(self):
        """마이그레이션 상태 확인 및 수정"""
        logger.info("🔍 마이그레이션 상태 확인 중...")
        
        # 1. 현재 데이터베이스 상태 확인
        current_success, current_output = self.run_command("alembic current", "현재 마이그레이션 상태 확인")
        
        # 2. 현재 존재하는 마이그레이션 파일 확인
        versions_dir = self.alembic_dir / "versions"
        migration_files = []
        
        for file in versions_dir.glob("*.py"):
            if file.name.startswith("__"):
                continue
            revision_id = file.name.split("_")[0]
            migration_files.append(revision_id)
        
        if not migration_files:
            logger.error("❌ 마이그레이션 파일을 찾을 수 없습니다.")
            return False
        
        latest_revision = migration_files[-1]
        logger.info(f"📝 최신 마이그레이션 파일: {latest_revision}")
        
        # 3. 데이터베이스 상태와 파일 상태 비교
        if current_success and latest_revision in current_output:
            logger.info("✅ 마이그레이션 상태가 정상입니다.")
            return True
        else:
            logger.warning("⚠️ 마이그레이션 상태가 불일치합니다. 수정을 시도합니다.")
            
            # 4. 데이터베이스 초기화 후 최신 마이그레이션 적용
            logger.info("🔄 데이터베이스 마이그레이션 상태 수정 중...")
            
            # 먼저 데이터베이스 초기화
            reset_success, reset_output = self.run_command("alembic downgrade base", "데이터베이스 초기화")
            if not reset_success:
                logger.warning("⚠️ 데이터베이스 초기화 실패, stamp 명령으로 시도합니다.")
            
            # 최신 마이그레이션으로 stamp
            stamp_success, stamp_output = self.run_command(f"alembic stamp {latest_revision}", f"최신 마이그레이션 {latest_revision} 적용")
            
            if stamp_success:
                logger.info("✅ 마이그레이션 상태 수정 완료")
                return True
            else:
                logger.error("❌ 마이그레이션 상태 수정 실패")
                return False
    
    def run_auto_migration(self):
        """자동 마이그레이션 실행"""
        print("\n" + "="*60)
        print("🚀 자동 마이그레이션 시작")
        print("="*60)
        
        try:
            # 1. 마이그레이션 상태 확인 및 수정
            logger.info("🔄 마이그레이션 상태 확인 및 수정 중...")
            migration_status_success = self.check_and_fix_migration_status()
            if not migration_status_success:
                logger.warning("⚠️ 마이그레이션 상태 수정 실패, 계속 진행...")
            
            # 2. 기존 마이그레이션 적용 (데이터베이스를 최신 상태로)
            logger.info("🔄 기존 마이그레이션 적용 중...")
            apply_success, apply_output = self.apply_migrations()
            if not apply_success:
                logger.warning("⚠️ 기존 마이그레이션 적용 실패, 계속 진행...")
            
            # 3. 스키마 변경사항 감지
            has_changes, changes_output = self.check_schema_changes()
            
            if not has_changes:
                print("\n✅ 스키마 변경사항이 없습니다. 마이그레이션이 필요하지 않습니다.")
                return True
            
            # 4. 백업 (선택사항)
            self.backup_database()
            
            # 5. 새 마이그레이션 파일 생성
            migration_success, migration_output = self.create_migration()
            if not migration_success:
                logger.error("❌ 마이그레이션 파일 생성 실패")
                return False
            
            # 6. 새 마이그레이션 적용
            apply_success, apply_output = self.apply_migrations()
            if not apply_success:
                logger.error("❌ 마이그레이션 적용 실패")
                return False
            
            # 7. 최종 상태 확인
            final_status_success, final_status_output = self.check_migration_status()
            
            print("\n" + "="*60)
            print("🎉 자동 마이그레이션 완료!")
            print("="*60)
            print(f"📊 변경사항: {changes_output}")
            print(f"📝 마이그레이션: {migration_output}")
            print(f"✅ 적용 결과: {apply_output}")
            if final_status_success:
                print(f"🔍 최종 상태: {final_status_output}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 자동 마이그레이션 중 오류 발생: {e}")
            return False

def main():
    """메인 실행 함수"""
    try:
        migrator = AutoMigrator()
        success = migrator.run_auto_migration()
        
        if success:
            print("\n✅ 자동 마이그레이션이 성공적으로 완료되었습니다!")
            sys.exit(0)
        else:
            print("\n❌ 자동 마이그레이션에 실패했습니다.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ 예상치 못한 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 