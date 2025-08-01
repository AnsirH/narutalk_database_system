# 빌드 스테이지
FROM python:3.11-slim AS builder

WORKDIR /app

# 빌드 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 기본 Python 의존성만 설치 (ML 라이브러리는 런타임에)
COPY requirements/requirements-base.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-base.txt && \
    rm -rf ~/.cache/pip/*

# 실행 스테이지
FROM python:3.11-slim

WORKDIR /app

# 런타임 의존성만 설치
RUN apt-get update && apt-get install -y \
    libpq5 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/*

# 빌드 스테이지에서 Python 패키지 복사
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# ML 라이브러리 requirements 복사
COPY requirements/requirements-ml.txt .

# 애플리케이션 코드 복사 (자주 변경되지 않는 것부터)
COPY migrations/scripts/ ./migrations/scripts/
COPY migrations/alembic/ ./migrations/alembic/
COPY migrations/alembic.ini .

# 포트 노출
EXPOSE 8000

# 환경변수 설정
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 시작 스크립트 복사 및 라인 엔딩 변환
COPY docker/start.sh /app/start.sh
RUN apt-get update && apt-get install -y dos2unix && \
    dos2unix /app/start.sh && \
    chmod +x /app/start.sh && \
    apt-get remove -y dos2unix && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 애플리케이션 실행
CMD ["/app/start.sh"] 