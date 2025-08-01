#!/bin/bash
set -e

echo "🚀 애플리케이션 시작 중..."

# ML 라이브러리 설치 (첫 실행 시에만)
if [ ! -f /app/.ml_installed ]; then
    echo "📦 ML 라이브러리 설치 중..."
    pip install --no-cache-dir -r /app/requirements-ml.txt
    touch /app/.ml_installed
    echo "✅ ML 라이브러리 설치 완료"
else
    echo "✅ ML 라이브러리 이미 설치됨"
fi

# PostgreSQL 연결 대기
echo "⏳ PostgreSQL 연결 대기 중..."
echo "🔍 Docker 환경 확인:"
echo "  - 현재 디렉토리: $(pwd)"
echo "  - PYTHONPATH: $PYTHONPATH"
echo "  - /app/.env 존재 여부:"
ls -la /app/.env || echo "  ❌ /app/.env 없음"

until python -c "
import sys
import os
sys.path.append('/app')

try:
    from app.config.settings import settings
    import psycopg2
    
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.db,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )
    conn.close()
    print('✅ PostgreSQL 연결 성공')
except Exception as e:
    print(f'❌ PostgreSQL 연결 실패: {e}')
    exit(1)
"; do
    echo "⏳ PostgreSQL 연결 재시도 중..."
    sleep 2
done

# 자동 마이그레이션 실행
echo "🔄 자동 마이그레이션 실행 중..."
cd /app && python migrations/scripts/auto_migrate.py

# 애플리케이션 실행
echo "🚀 FastAPI 애플리케이션 시작..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app/app/routers --reload-dir /app/app/services --reload-dir /app/app/models --reload-dir /app/app/schemas --reload-dir /app/app/config --reload-dir /app/app/main.py