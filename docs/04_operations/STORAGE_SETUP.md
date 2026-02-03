# Storage & Database 구축 가이드

Shorts Producer의 데이터 영속화와 대용량 에셋 관리를 위한 인프라 설정 가이드입니다.

## 1. PostgreSQL (Database)

시스템의 모든 메타데이터(프로젝트, 스토리보드, 캐릭터, 태그 규칙 등)를 저장합니다.

### 설치 및 실행
- **Docker 사용 시**:
  ```bash
  docker run --name shorts-db -e POSTGRES_PASSWORD=password123 -p 5432:5432 -d postgres
  ```
- **환경 변수 설정 (`.env`)**:
  ```bash
  DATABASE_URL=postgresql://postgres:password123@localhost:5432/shorts_producer
  ```

### 데이터베이스 초기화 (Alembic)
백엔드 디렉토리에서 마이그레이션을 실행하여 테이블을 생성합니다.
```bash
cd backend
uv run alembic upgrade head
```

## 2. MinIO (Object Storage)

생성된 이미지, 영상, 캐릭터 아바타 등 대용량 파일을 저장합니다.

### 설치 및 실행 (Docker)
```bash
docker run -p 9000:9000 -p 9001:9001 \
  --name shorts-minio \
  -e "MINIO_ROOT_USER=admin" \
  -e "MINIO_ROOT_PASSWORD=password123" \
  -d minio/minio server /data --console-address ":9001"
```

### 버킷 생성
- 접속: `http://localhost:9001`
- 버킷 생성: `shorts-producer` (기본값)
- **Access Policy**: `public`으로 설정해야 웹 UI에서 이미지를 직접 로드할 수 있습니다.

### 설정 (`.env`)
```bash
STORAGE_MODE=s3
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=password123
MINIO_BUCKET=shorts-producer
STORAGE_PUBLIC_URL=http://localhost:9000
```

## 3. 로컬 스토리지 모드 (개발용)

의존성 없이 빠르게 시작하려면 로컬 파일 시스템을 저장소로 사용할 수 있습니다.

### 설정 (`.env`)
```bash
STORAGE_MODE=local
```
- 모든 파일은 `backend/outputs/` 디렉토리에 저장됩니다.
- 프로덕션 환경에서는 권장되지 않습니다.

## 4. 데이터 계층 구조

시스템은 다음과 같은 계층으로 데이터를 관리합니다.
1. **Projects**: 최상위 채널 단위
2. **Groups**: 시리즈 또는 주제별 그룹
3. **Storyboards**: 개별 제작 영상 단위
4. **Scenes**: 영상 내 장면 정보
5. **Assets**: 이미지/비디오 파일 (MinIO 또는 Local)
