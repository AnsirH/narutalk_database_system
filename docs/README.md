# Database Project Structure

## 현재 구조 분석

### 문제점
- Docker 관련 파일들이 루트에 흩어져 있음
- 데이터 폴더들이 루트에 노출됨
- 설정 파일들이 혼재됨

### 개선 방안

```
database/
├── docker/                    # Docker 관련 파일들
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── start.sh
│   └── .dockerignore
├── app/                       # 애플리케이션 코드
│   ├── main.py
│   ├── config/
│   ├── models/
│   ├── services/
│   ├── routers/
│   └── schemas/
├── migrations/                # 마이그레이션 관련
│   ├── alembic/
│   ├── alembic.ini
│   └── scripts/
├── requirements/              # 의존성 파일들
│   ├── requirements.txt
│   ├── requirements-base.txt
│   └── requirements-ml.txt
├── data/                      # 데이터 폴더들
│   ├── pgdata/
│   ├── pgadmin_data/
│   ├── osdata1/
│   ├── osdata2/
│   ├── osdata3/
│   └── minio_data/
├── docs/                      # 문서들
│   ├── README.md
│   ├── 환경변수_README.md
│   ├── JWT_SECURITY_GUIDE.md
│   └── readmd.md
└── scripts/                   # 유틸리티 스크립트
    ├── generate_jwt_secret.py
    └── auto_migrate.py
```

## 장점
1. **명확한 분리**: Docker, 앱, 마이그레이션, 데이터 분리
2. **유지보수성**: 관련 파일들이 함께 위치
3. **가독성**: 폴더 구조만 봐도 역할 파악 가능
4. **확장성**: 새로운 기능 추가 시 적절한 위치에 배치

## 마이그레이션 계획
1. 폴더 구조 변경
2. docker-compose.yml 경로 수정
3. Dockerfile 경로 수정
4. 스크립트 경로 수정 