#!/bin/bash
set -e

echo "🚀 애플리케이션 시작 중..."

# pip 업그레이드 및 ML 라이브러리 설치 (pip 캐시 활용)
echo "📦 pip 업그레이드 중..."
pip install --upgrade pip
echo "📦 ML 라이브러리 설치 확인 중..."
pip install -r /app/requirements-ml.txt
echo "✅ ML 라이브러리 설치 완료"

# PostgreSQL 연결 대기
echo "⏳ PostgreSQL 연결 대기 중..."
echo "🔍 Docker 환경 확인:"
echo "  - 현재 디렉토리: $(pwd)"
echo "  - PYTHONPATH: $PYTHONPATH"
echo "  - /app/.env 존재 여부:"
ls -la /app/.env || echo "  ❌ /app/.env 없음"
echo "  - /app/app 디렉토리 확인:"
ls -la /app/app || echo "  ❌ /app/app 디렉토리 없음"

until python -c "
import sys
import os
sys.path.insert(0, '/app')

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

# 애플리케이션 실행
echo "🚀 FastAPI 애플리케이션 시작..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app/app/routers --reload-dir /app/app/services --reload-dir /app/app/models --reload-dir /app/app/schemas --reload-dir /app/app/config --reload-dir /app/app/main.py